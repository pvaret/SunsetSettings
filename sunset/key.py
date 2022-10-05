import weakref

from typing import (
    Callable,
    Generic,
    Iterator,
    Optional,
    Sequence,
    Type,
)

from typing_extensions import Self

from .exporter import maybeEscape
from .registry import CallbackRegistry
from .serializers import SerializableT, deserialize, serialize


class Key(Generic[SerializableT]):
    """
    A single setting key containing a typed value.

    Keys support inheritance. If a Key does not have a value explicitly set, and
    it has a parent, then its value will be that of its parent.

    Keys can call a callback when their value changes, regardless of if its
    their own value that changed, or that inherited from a parent. Set this
    callback with the :meth:`onValueChangeCall()` method.

    Args:
        default: (str, int, bool, float, or anything that implements the
            :class:`protocols.Serializable` protocol) The value that this Key
            will return when not otherwise set; the type of this default
            determines the type of the values that can be set on this Key.

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

    _default: SerializableT
    _value: SerializableT
    _isSet: bool
    _value_change_callbacks: CallbackRegistry[SerializableT]
    _update_notification_callbacks: CallbackRegistry[Self]
    _parent: Optional[weakref.ref[Self]]
    _children: weakref.WeakSet[Self]
    _type: Type[SerializableT]

    def __init__(self, default: SerializableT):

        # serialize() raises an exception if the given value is not
        # serializable, so this call guarantees that the provided default is of
        # a type allowed in a Key. In case the user went ahead and ignored the
        # typechecker error when instantiating their Key with a bad default.

        serialize(default)

        super().__init__()

        self._default = default
        self._value = default
        self._isSet = False

        self._value_change_callbacks = CallbackRegistry()
        self._update_notification_callbacks = CallbackRegistry()

        self._parent = None
        self._children = weakref.WeakSet()

        # Keep a runtime reference to the practical type contained in this
        # key.

        self._type = type(default)

    def get(self) -> SerializableT:
        """
        Returns the current value of this Key.

        If this Key does not currently have a value set on it, return that of
        its parent if any. If it does not have a parent, return the default
        value for this Key.

        Returns:
            This Key's current value.
        """

        if self.isSet():
            return self._value

        if (parent := self.parent()) is not None:
            return parent.get()

        return self._default

    def set(self, value: SerializableT) -> None:
        """
        Sets the given value on this Key.

        Args:
            value: The value that this Key will now hold. Must be of the type
                bound to this Key, i.e. the type of this Key's default value.

        Returns:
            None.
        """

        # Safety check in case the user is holding it wrong.

        if not isinstance(value, self._type):
            return

        prev_value = self.get()
        previously_set = self.isSet()

        self._value = value
        self._isSet = True

        if prev_value != self.get():
            self._value_change_callbacks.callAll(self.get())
            for child in self.children():
                child._notifyParentValueChanged()

        if not previously_set or prev_value != self.get():
            self._notifyUpdate()

    def clear(self) -> None:
        """
        Clears the value currently set on this Key, if any.

        Returns:
            None.
        """

        if not self.isSet():
            return

        prev_value = self.get()
        self._isSet = False
        self._value = self._default

        if prev_value != self.get():
            self._value_change_callbacks.callAll(self.get())
            for child in self.children():
                child._notifyParentValueChanged()

        self._notifyUpdate()

    def isSet(self) -> bool:
        """
        Returns whether there is a value currently set on this Key.

        Returns:
            True if a value is set on this Key, else False.
        """

        return self._isSet

    def onValueChangeCall(
        self, callback: Callable[[SerializableT], None]
    ) -> None:
        """
        Adds a callback to be called whenever the value exported by this Key
        changes, even if it was not updated itself; for instance, this will
        happen if there is no value currently set on it and its parent's value
        changed.

        The callback will be called with the new value as its argument.

        If you want a callback to be called whenever this Key is updated, even
        if its apparent value does not change, use :meth:onUpdateCall() instead,
        For example, if you call set(0) on Key with a default value of 0,
        callbacks added with onUpdateCall() are called and callbacks added with
        onValueChangeCall() are not.


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

    def onUpdateCall(self, callback: Callable[[Self], None]) -> None:
        """
        Adds a callback to be called whenever this Key is updated, even if the
        value returned by :meth:get() does not end up changing.

        The callback will be called with this Key instance as its argument.

        If you want a callback to be called only when the apparent value of this
        Key changes, use :meth:onValueChangeCall() instead. For example, if a
        Key has no value set on it and has a parent whose value is updated, then
        callbacks added on this Key with onValueChangeCall() are called, and
        callbacks added with onUpdateCall() are not, because it's not this Key
        that was updated.

        Args:
            callback: A callable that takes one argument of the same type as
                this Key, and that returns None.

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

        return self._parent() if self._parent is not None else None

    def children(self: Self) -> Iterator[Self]:
        """
        Returns an iterator over the Keys that have this Key as their parent.

        Returns:
            An iterator over Keys of the same type as this one.
        """

        yield from self._children

    def dump(self) -> Sequence[tuple[str, str]]:
        """
        Internal.
        """

        if self.isSet():
            return [("", serialize(self.get()))]
        else:
            return []

    def restore(self, data: Sequence[tuple[str, str]]) -> None:
        """
        Internal.
        """

        # Normally, a Key should be restored from one single item of data, with
        # an empty name. However, if we are loading a partially corrupted dump
        # where an entry is duplicated, it's better to restore one of the
        # duplicates than drop them all. Arbitrarily, we restore the last valid
        # one.

        for name, dump in reversed(data):

            if name:

                # For a Key there should be no name. This entry is not valid.

                continue

            value = deserialize(self._type, dump)
            if value is None:

                # The given string is not a valid serialized value for this
                # key. This entry is not valid.

                continue

            # Found a valid entry. Set it and finish.

            self.set(value)
            break

    def _notifyParentValueChanged(self):

        if self.isSet():
            return

        self._value_change_callbacks.callAll(self.get())

    def _notifyUpdate(self):

        self._update_notification_callbacks.callAll(self)

    def new(self) -> Self:
        """
        Returns a new instance of this Key with the same default value.

        Returns:
            A new Key.
        """

        return self.__class__(default=self._default)

    def __repr__(self) -> str:

        return (
            f"<Key[{self._type.__name__}]:{maybeEscape(serialize(self.get()))}>"
        )
