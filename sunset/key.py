import logging
import sys
import weakref
from collections.abc import Callable, Iterator
from types import GenericAlias
from typing import (
    Any,
    Generic,
    TypeVar,
    cast,
)

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self

from sunset.exporter import maybe_escape
from sunset.lockable import Lockable
from sunset.notifier import Notifier
from sunset.protocols import BaseField, Serializer, UpdateNotifier
from sunset.serializers import lookup

_T = TypeVar("_T")


class Key(Generic[_T], BaseField, Lockable):
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

        value_type: If given, the type that will be used by runtime safety
            checks instead of the type of the default value. This is rarely
            needed, but can be useful e.g. if the Key is meant to hold values
            from multiple possible subclasses of a base class.

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
    _value: _T | None
    _serializer: Serializer[_T]
    _validator: Callable[[_T], bool]
    _bad_value_string: str | None
    _value_change_notifier: Notifier[_T]
    _update_notifier: Notifier[[UpdateNotifier]]
    _loaded_notifier: Notifier[[]]
    _parent_ref: weakref.ref["Key[_T]"] | None
    _children_ref: weakref.WeakSet["Key[_T]"]
    _type: type[_T]

    def __init__(
        self,
        default: _T,
        serializer: Serializer[_T] | None = None,
        validator: Callable[[_T], bool] | None = None,
        value_type: type[_T] | None = None,
    ) -> None:
        super().__init__()

        # Keep a runtime reference to the practical type contained in this
        # key.

        if value_type is not None:
            if not isinstance(default, value_type):
                msg = (
                    f"Default Key value '{default}' has type"
                    f" '{default.__class__.__name__}', which is not compatible"
                    " with explicitly given value type"
                    f" '{value_type.__name__}'."
                )
                raise TypeError(msg)
            self._type = value_type
        else:
            self._type = default.__class__

        self._default = default
        self._value = None
        self._bad_value_string = None

        if serializer is None:
            serializer = lookup(self._type)
            if serializer is None:
                msg = (
                    f"Default Key value '{default}' has type"
                    f" '{self._type.__name__}', which is not supported by a native"
                    " serializer. Please construct the Key with an explicit serializer"
                    " argument."
                )
                raise TypeError(msg)

        if validator is not None:
            self._validator = validator
        else:
            self._validator = lambda _: True

        self._serializer = serializer

        self._value_change_notifier = Notifier()
        self._update_notifier = Notifier()
        self._loaded_notifier = Notifier()

        self._parent_ref = None
        self._children_ref = weakref.WeakSet()

    def get(self) -> _T:
        """
        Returns the current value of this Key.

        If this Key does not currently have a value set on it, return its
        fallback value, that being, the value of its parent if it has one, else
        the default.

        Returns:
            This Key's apparent value.
        """

        return self.fallback() if (value := self._value) is None else value

    def fallback(self) -> _T:
        """
        Returns the value that this Key will fall back to when it does not have
        a value currently set.

        That value is the value of its parent if it has one, or the default
        value for the Key if not.
        """

        return self._default if (parent := self.parent()) is None else parent.get()

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
            logging.debug("Validator rejected value for Key %r: %r", self, value)
            return False

        # Setting a Key's value programmatically always resets bad values.

        self._bad_value_string = None

        previously_set = self.isSet()
        prev_value = self.get()

        self._value = value

        if prev_value != self.get():
            self._value_change_notifier.trigger(self.get())
            for child in self.children():
                child._notifyParentValueChanged()  # noqa: SLF001

        if not previously_set or prev_value != self.get():
            self._update_notifier.trigger(self)

        return True

    def clear(self) -> None:
        """
        Clears the value currently set on this Key, if any.
        """

        # Clearing the Key always resets bad values.

        self._bad_value_string = None

        if not self.isSet():
            return

        prev_value = self.get()
        self._value = None

        if prev_value != self.get():
            self._value_change_notifier.trigger(self.get())
            for child in self.children():
                child._notifyParentValueChanged()  # noqa: SLF001

        self._update_notifier.trigger(self)

    @Lockable.with_lock
    def updateValue(self, updater: Callable[[_T], _T]) -> None:
        """
        Atomically updates this Key's value using the given update function. The
        function will be called with the Key's current value, and the value it
        returns will be set as the Key's new value.

        Args:
            updater: A function that takes an argument of the same type held in
                this key, and returns an argument of the same type.
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

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._value_change_notifier.add(callback)

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

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._update_notifier.add(callback)  # type: ignore[arg-type]

    def onLoadedCall(self, callback: Callable[[], Any]) -> None:
        """
        Adds a callback to be called whenever settings were just loaded. This
        Key itself may or may not have been modified during the load.

        Args:
            callback: A callable that takes no argument.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._loaded_notifier.add(callback)

    def setValidator(self, validator: Callable[[_T], bool]) -> None:
        """
        Replaces this Key's validator.

        Args:
            validator: A function that returns True if the given value can be
                set on this Key, else False. This allows you to control what
                values are allowable for this Key.
        """

        self._validator = validator

    def setParent(self, parent: Self | None) -> None:
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

        Note:
            A Key and its parent, if any, do not increase each other's
            reference count.
        """

        # Runtime check to affirm the type check of the method.

        if parent is not None and type(self) is not type(parent):
            return

        old_parent = self.parent()
        if old_parent is not None:
            old_parent._children_ref.discard(self)  # noqa: SLF001

        if parent is None:
            self._parent_ref = None
            return

        if parent._type is not self._type:  # noqa: SLF001
            # This should not happen... unless the user is holding it wrong.
            # So, better safe than sorry.

            return

        parent._children_ref.add(self)  # noqa: SLF001
        self._parent_ref = weakref.ref(parent)

    def parent(self) -> Self | None:
        """
        Returns the parent of this Key, if any.

        Returns:
            A Key instance of the same type as this one, or None.
        """

        # Make the type of self._parent_ref more specific for the purpose of
        # type checking.

        parent = cast(weakref.ref[Self] | None, self._parent_ref)
        return parent() if parent is not None else None

    def children(self) -> Iterator[Self]:
        """
        Returns an iterator over the Keys that have this Key as their parent.

        Returns:
            An iterator over Keys of the same type as this one.
        """

        for child in self._children_ref:
            yield cast(Self, child)

    def dumpFields(self) -> Iterator[tuple[str, str | None]]:
        if not self.skipOnSave():
            if self.isSet():
                yield "", self._serializer.toStr(self.get())

            elif self._bad_value_string is not None:
                # If a bad value was set in the settings file for this Key, and
                # the Key was not modified since, then save the bad value again.
                # This way, typos in the settings file don't outright destroy
                # the entry.

                yield "", self._bad_value_string

    def restoreField(self, path: str, value: str | None) -> bool:
        if value is None:
            # Note that doing nothing when the given value is None, is
            # considered a success.

            return True

        if path != "":
            # Keys don't have sub-fields. If a path was given, then the path is
            # incorrect.
            return False

        with self._update_notifier.inhibit():
            if (val := self._serializer.fromStr(value)) is not None:
                return self.set(val)

            # Keep track of the value that failed to restore, so that we can dump it
            # again when saving. That way, if a user makes a typo while editing the
            # settings file, the faulty entry is not entirely lost when we save.

            logging.error("Invalid value for Key %r: %s", self, value)
            self._bad_value_string = value
            return False

    def _notifyParentValueChanged(self) -> None:
        if self.isSet():
            return

        self._value_change_notifier.trigger(self.get())
        for child in self.children():
            child._notifyParentValueChanged()  # noqa: SLF001

    def _typeHint(self) -> GenericAlias:
        return GenericAlias(type(self), self._type)

    def _newInstance(self) -> Self:
        """
        Internal. Returns a new instance of this Key with the same default
        value.

        Returns:
            A new Key.
        """

        return self.__class__(
            default=self._default,
            serializer=self._serializer,
            validator=self._validator,
            value_type=self._type,
        )

    def __repr__(self) -> str:
        type_name = self._type.__name__
        value = maybe_escape(self._serializer.toStr(self.get()))
        if not self.isSet():
            value = f"({value})"
        return f"<Key[{type_name}]:{value}>"
