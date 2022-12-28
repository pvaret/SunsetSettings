import weakref

from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Optional,
    Type,
    TypeVar,
    cast,
)

from .exporter import maybe_escape
from .lockable import Lockable
from .protocols import ContainableImpl
from .registry import CallbackRegistry
from .serializers import AnySerializableType, deserialize, serialize


# TODO: Replace with typing.Self when mypy finally supports that.
Self = TypeVar("Self", bound="Key[Any]")


class Key(Generic[AnySerializableType], ContainableImpl, Lockable):
    """
    A single setting key containing a typed value.

    Keys support inheritance. If a Key does not have a value explicitly set, and
    it has a parent, then its value will be that of its parent. Else its value
    if unset is the default value it was instantiated with.

    Keys can call a callback when their value changes, regardless of if its
    their own value that changed, or that inherited from a parent. Set this
    callback with the :meth:`onValueChangeCall()` method.

    Args:
        default: (str, int, bool, float, or any type that implements the
            :class:`~sunset.Serializable` protocol) The value that this Key will
            return when not otherwise set; the type of this default determines
            the type of the values that can be set on this Key.

    Example:

    >>> from sunset import Key
    >>> key: Key[int] = Key(default=0)
    >>> key.get()
    0
    >>> key.set(42)
    >>> key.get()
    42
    >>> child_key: Key[int] = Key(default=0)
    >>> child_key.setParent(key)
    >>> child_key.get()
    42
    >>> child_key.set(101)
    >>> child_key.get()
    101
    >>> key.set(36)
    >>> key.get()
    36
    >>> child_key.get()
    101
    >>> child_key.clear()
    >>> child_key.get()
    36
    """

    _default: AnySerializableType
    _value: Optional[AnySerializableType]
    _value_change_callbacks: CallbackRegistry[AnySerializableType]
    _update_notification_callbacks: CallbackRegistry["Key[AnySerializableType]"]
    _update_notification_enabled: bool
    _parent: Optional[weakref.ref["Key[AnySerializableType]"]]
    _children: weakref.WeakSet["Key[AnySerializableType]"]
    _type: Type[AnySerializableType]

    def __init__(self, default: AnySerializableType):

        # serialize() raises an exception if the given value is not
        # serializable, so this call guarantees that the provided default is of
        # a type allowed in a Key. In case the user went ahead and ignored the
        # typechecker error when instantiating their Key with a bad default.

        serialize(default)

        super().__init__()

        self._default = default
        self._value = None

        self._value_change_callbacks = CallbackRegistry()
        self._update_notification_callbacks = CallbackRegistry()
        self._update_notification_enabled = True

        self._parent = None
        self._children = weakref.WeakSet()

        # Keep a runtime reference to the practical type contained in this
        # key.

        self._type = cast(Type[AnySerializableType], default.__class__)

    def get(self) -> AnySerializableType:
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

    def set(self, value: AnySerializableType) -> None:
        """
        Sets the given value on this Key.

        Args:
            value: The value that this Key will now hold. Must be of the type
                bound to this Key, i.e. the same type as this Key's default
                value.

        Returns:
            None.
        """

        # Safety check in case the user is holding it wrong.

        if not isinstance(value, self._type):
            return

        previously_set = self.isSet()
        prev_value = self.get()

        self._value = value

        if prev_value != self.get():
            self._value_change_callbacks.callAll(self.get())
            for child in self.children():
                child._notifyParentValueChanged()

        if not previously_set or prev_value != self.get():
            self.triggerUpdateNotification()

    def clear(self) -> None:
        """
        Clears the value currently set on this Key, if any.

        Returns:
            None.
        """

        if not self.isSet():
            return

        prev_value = self.get()
        self._value = None

        if prev_value != self.get():
            self._value_change_callbacks.callAll(self.get())
            for child in self.children():
                child._notifyParentValueChanged()

        self.triggerUpdateNotification()

    @Lockable.with_lock
    def updateValue(
        self, updater: Callable[[AnySerializableType], AnySerializableType]
    ) -> None:
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

    def onValueChangeCall(
        self, callback: Callable[[AnySerializableType], None]
    ) -> None:
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
            callback: A callable that takes one argument of the same type of the
                values held by this Key, and that returns None.

        Returns:
            None.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._value_change_callbacks.add(callback)

    def onUpdateCall(
        self, callback: Callable[["Key[AnySerializableType]"], None]
    ) -> None:
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

        if self.isSet() and not self.isPrivate():
            yield self.fieldPath(), serialize(self.get())

    def restoreField(self, path: str, value: Optional[str]) -> None:

        if value is None:
            return

        self._update_notification_enabled = False

        if path == self.fieldLabel():
            if (val := deserialize(self._type, value)) is not None:
                self.set(val)

        self._update_notification_enabled = True

    def _notifyParentValueChanged(self):

        if self.isSet():
            return

        self._value_change_callbacks.callAll(self.get())
        for child in self.children():
            child._notifyParentValueChanged()

    def triggerUpdateNotification(self):
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

        return self.__class__(default=self._default)

    def __repr__(self) -> str:

        type_name = self._type.__name__
        value = maybe_escape(serialize(self.get()))
        if not self.isSet():
            value = f"({value})"
        return f"<Key[{type_name}]:{value}>"
