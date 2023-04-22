import logging
import weakref

from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Optional,
    TypeVar,
    cast,
)

from .exporter import maybe_escape
from .lockable import Lockable
from .protocols import ContainableImpl, Serializer
from .registry import CallbackRegistry
from .serializers import lookup


# TODO: Replace with typing.Self when mypy finally supports that.
Self = TypeVar("Self", bound="Key[Any]")
_T = TypeVar("_T")


class Key(Generic[_T], ContainableImpl, Lockable):
    """
    A single setting key containing a typed value.

    Keys support inheritance. If a Key does not have a value explicitly set, and
    it has a parent, then its value will be that of its parent. Else its value
    if unset is the default value it was instantiated with.

    Keys can call a callback when their reported value changes, whether it's
    their own value that changed, or that inherited from a parent. Set this
    callback with the :meth:`onValueChangeCall()` method.

    You can control the values that can be set on this Key by passing a
    `validator` argument when instantiating it.

    Args:
        default: The value that this Key will return when not otherwise set; the
            type of this default determines the type of the values that can be
            set on this Key.

            If the type of the default is not one of bool, int, float, str, or
            an `enum.Enum` subclass, and is also not a class that implements the
            :class:`~sunset.Serializable` protocol, then a serializer argument
            must also be passed.

        serializer: An implementation of the :class:`~sunset.Serializer`
            protocol for the type of this Key's values. This argument must be
            passed if the type in question is not supported by a native
            SunsetSettings serializer. If a serializer is passed, it will be
            used even if SunsetSettings has its own serializer for that type.

        validator: A function that returns True if the given value can be set on
            this Key, else False. This allows you to control what values are
            allowable for this Key. Default: None.

    Example:

    >>> from sunset import Key
    >>> key: Key[int] = Key(default=0)
    >>> key.get()
    0
    >>> key.set(42)
    True
    >>> key.get()
    42
    >>> child_key: Key[int] = Key(default=0)
    >>> child_key.setParent(key)
    >>> child_key.get()
    42
    >>> child_key.set(101)
    True
    >>> child_key.get()
    101
    >>> key.set(36)
    True
    >>> key.get()
    36
    >>> child_key.get()
    101
    >>> child_key.clear()
    >>> child_key.get()
    36
    """

    _default: _T
    _value: Optional[_T]
    _serializer: Serializer[_T]
    _validator: Callable[[_T], bool]
    _bad_value_string: Optional[str]
    _value_change_callbacks: CallbackRegistry[_T]
    _update_notification_callbacks: CallbackRegistry["Key[_T]"]
    _update_notification_enabled: bool
    _parent: Optional[weakref.ref["Key[_T]"]]
    _children: weakref.WeakSet["Key[_T]"]
    _type: type[_T]

    def __init__(
        self,
        default: _T,
        serializer: Optional[Serializer[_T]] = None,
        validator: Optional[Callable[[_T], bool]] = None,
    ) -> None:
        super().__init__()

        # Keep a runtime reference to the practical type contained in this
        # key.

        self._type = cast(type[_T], default.__class__)

        self._default = default
        self._value = None
        self._bad_value_string = None

        if serializer is None:
            serializer = lookup(self._type)
            if serializer is None:
                raise TypeError(
                    f"Default Key value '{default}' has type"
                    f" '{self._type.__name__}', which is not"
                    " supported by a native serializer. Please construct"
                    " the Key with an explicit serializer argument."
                )

        if validator is not None:
            self._validator = validator
        else:
            self._validator = lambda _: True

        self._serializer = serializer

        self._value_change_callbacks = CallbackRegistry()
        self._update_notification_callbacks = CallbackRegistry()
        self._update_notification_enabled = True

        self._parent = None
        self._children = weakref.WeakSet()

    def get(self) -> _T:
        """
        Returns the current value of this Key.

        If this Key does not currently have a value set on it, return that of
        its parent if any. If it does not have a parent, return the default
        value for this Key.

        Returns:
            This Key's current value.
        """

        if (value := self._value) is not None:
            return value

        if (parent := self.parent()) is not None:
            return parent.get()

        return self._default

    def set(self, value: _T) -> bool:
        """
        Sets the given value on this Key.

        Args:
            value: The value that this Key will now hold. Must be of the type
                bound to this Key, i.e. the same type as this Key's default
                value.

        Returns:
            True if the value was successfully set, else False, for instance if
            the validator refused the value.
        """

        # Safety check in case the user is holding it wrong.

        if not isinstance(value, self._type):
            return False

        if not self._validator(value):
            logging.debug(
                "Validator rejected value for Key %s: %r",
                self.fieldPath(),
                value,
            )
            return False

        # Setting a Key's value programmatically always resets bad values.

        self._bad_value_string = None

        previously_set = self.isSet()
        prev_value = self.get()

        self._value = value

        if prev_value != self.get():
            self._value_change_callbacks.callAll(self.get())
            for child in self.children():
                # pylint: disable=protected-access
                child._notifyParentValueChanged()

        if not previously_set or prev_value != self.get():
            self.triggerUpdateNotification()

        return True

    def clear(self) -> None:
        """
        Clears the value currently set on this Key, if any.

        Returns:
            None.
        """

        # Clearing the Key always resets bad values.

        self._bad_value_string = None

        if not self.isSet():
            return

        prev_value = self.get()
        self._value = None

        if prev_value != self.get():
            self._value_change_callbacks.callAll(self.get())
            for child in self.children():
                # pylint: disable=protected-access
                child._notifyParentValueChanged()

        self.triggerUpdateNotification()

    @Lockable.with_lock
    def updateValue(self, updater: Callable[[_T], _T]) -> None:
        """
        Atomically updates this Key's value using the given update function. The
        function will be called with the Key's current value, and the value it
        returns will be set as the Key's new value.

        Args:
            updater: A function that takes an argument of the same type held in
                this key, and returns an argument of the same type.

        Returns:
            None.
        """

        self.set(updater(self.get()))

    def isSet(self) -> bool:
        """
        Returns whether there is a value currently set on this Key.

        Returns:
            True if a value is set on this Key, else False.
        """

        return self._value is not None

    def onValueChangeCall(self, callback: Callable[[_T], Any]) -> None:
        """
        Adds a callback to be called whenever the value returned by calling
        :meth:`get()` on this Key would change, even if this Key itself was not
        updated; for instance, this will happen if there is no value currently
        set on it and its parent's value changed.

        The callback will be called with the new value as its argument.

        If you want a callback to be called whenever this Key is updated, even
        if its apparent value does not change, use :meth:`onUpdateCall()`
        instead. For example, if you call :meth:`set()` with a value of `0` on a
        Key newly created with a default value of `0`, callbacks added with
        :meth:`onUpdateCall()` are called and callbacks added with
        :meth:`onValueChangeCall()` are not.


        Args:
            callback: A callable that takes one argument of the same type as the
                values held by this Key.

        Returns:
            None.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._value_change_callbacks.add(callback)

    def onUpdateCall(self, callback: Callable[["Key[_T]"], Any]) -> None:
        """
        Adds a callback to be called whenever this Key is updated, even if the
        value returned by :meth:`get()` does not end up changing.

        The callback will be called with this Key instance as its argument.

        If you want a callback to be called only when the apparent value of this
        Key changes, use :meth:`onValueChangeCall()` instead. For example, if a
        Key has no value set on it and has a parent whose value is updated, then
        callbacks added on this Key with :meth:`onValueChangeCall()` are called,
        and callbacks added with :meth:`onUpdateCall()` are not, because it's
        not *this* Key that was updated.

        Args:
            callback: A callable that will be called with one argument of type
                :class:`~sunset.Key`.

        Returns:
            None.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._update_notification_callbacks.add(callback)

    def setValidator(self, validator: Callable[[_T], bool]) -> None:
        """
        Replaces this Key's validator.

        Args:
            validator: A function that returns True if the given value can be
                set on this Key, else False. This allows you to control what
                values are allowable for this Key.

        Returns:
            None.
        """

        self._validator = validator

    def setParent(self: Self, parent: Optional[Self]) -> None:
        """
        Makes the given Key the parent of this one. If None, remove this
        Key's parent, if any.

        A Key with a parent will inherit its parent's value when this
        Key's own value is not currently set.

        This method is for internal purposes and you will typically not need to
        call it directly.

        Args:
            parent: Either a Key that will become this Key's parent, or
                None. The parent Key must have the same type as this
                Key.

        Returns:
            None.

        Note:
            A Key and its parent, if any, do not increase each other's
            reference count.
        """

        # Runtime check to affirm the type check of the method.

        if parent is not None:
            if type(self) is not type(parent):
                return

        # pylint: disable=protected-access

        old_parent = self.parent()
        if old_parent is not None:
            old_parent._children.discard(self)

        if parent is None:
            self._parent = None
            return

        if parent._type is not self._type:
            # This should not happen... unless the user is holding it wrong.
            # So, better safe than sorry.

            return

        parent._children.add(self)
        self._parent = weakref.ref(parent)

    def parent(self: Self) -> Optional[Self]:
        """
        Returns the parent of this Key, if any.

        Returns:
            A Key instance of the same type as this one, or None.
        """

        # Make the type of self._parent more specific for the purpose of type
        # checking.

        _parent = cast(Optional[weakref.ref[Self]], self._parent)
        return _parent() if _parent is not None else None

    def children(self: Self) -> Iterator[Self]:
        """
        Returns an iterator over the Keys that have this Key as their parent.

        Returns:
            An iterator over Keys of the same type as this one.
        """

        for child in self._children:
            yield cast(Self, child)

    def dumpFields(self) -> Iterable[tuple[str, Optional[str]]]:
        if not self.isPrivate():
            if self.isSet():
                yield self.fieldPath(), self._serializer.toStr(self.get())

            elif self._bad_value_string is not None:
                # If a bad value was set in the settings file for this Key, and
                # the Key was not modified since, then save the bad value again.
                # This way, typos in the settings file don't outright destroy
                # the entry.

                yield self.fieldPath(), self._bad_value_string

    def restoreField(self, path: str, value: Optional[str]) -> bool:
        if value is None:
            # Note that doing nothing when the given value is None, is
            # considered a success.

            return True

        success: bool = False

        self._update_notification_enabled = False

        if path == self.fieldLabel():
            if (val := self._serializer.fromStr(value)) is not None:
                success = self.set(val)

            else:
                # Keep track of the value that failed to restore, so that we can
                # dump it again when saving. That way, if a user makes a typo
                # while editing the settings file, the faulty entry is not
                # entirely lost when we save.

                logging.error(
                    "Invalid value for Key %s: %s", self.fieldPath(), value
                )
                self._bad_value_string = value

        self._update_notification_enabled = True

        return success

    def _notifyParentValueChanged(self) -> None:
        if self.isSet():
            return

        self._value_change_callbacks.callAll(self.get())
        for child in self.children():
            # pylint: disable=protected-access
            child._notifyParentValueChanged()

    def triggerUpdateNotification(self) -> None:
        """
        Internal.
        """

        if not self._update_notification_enabled:
            return

        self._update_notification_callbacks.callAll(self)

        if (container := self.container()) is not None and not self.isPrivate():
            container.triggerUpdateNotification(self)

    def newInstance(self: Self) -> Self:
        """
        Internal. Returns a new instance of this Key with the same default
        value.

        Returns:
            A new Key.
        """

        return self.__class__(
            default=self._default, serializer=self._serializer
        )

    def __repr__(self) -> str:
        type_name = self._type.__name__
        value = maybe_escape(self._serializer.toStr(self.get()))
        if not self.isSet():
            value = f"({value})"
        return f"<Key[{type_name}]:{value}>"
