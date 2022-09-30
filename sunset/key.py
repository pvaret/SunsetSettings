import weakref

from dataclasses import field
from typing import Callable, Generic, Iterator, Optional, Sequence, Type

from typing_extensions import Self

from .registry import CallbackRegistry
from .serializers import SerializableT, deserialize, serialize


class Key(Generic[SerializableT]):
    """
    A single setting key containing a typed value.

    When adding a Key to a :class:`Section` or a :class:`Settings` definition,
    do not instantiate the Key class directly; use the :func:`sunset.NewKey()`
    function instead.

    Keys support inheritance. If a Key does not have a value explicitly set, and
    it has a parent, then its value will be that of its parent.

    Keys can call a callback when their value changes, regardless of if its
    their own value that changed, or that inherited from a parent. Set this
    callback with the :meth:`onValueChangeCall()` method.

    Args:
        default: (str, int, bool, or anything that implements the
            :class:`sunset.protocols.Serializable` protocol) The value that this
            Key will return when not otherwise set; the type of this default
            determines the type of the Key.

    Example:

    >>> import sunset
    >>> key: sunset.Key[int] = sunset.Key(default=0)
    >>> key.get()
    0
    >>> key.set(42)
    >>> key.get()
    42
    >>> child_key: sunset.Key[int] = sunset.Key(default=0)
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
    _modification_notification_callbacks: CallbackRegistry[Self]
    _parent: Optional[weakref.ref[Self]]
    _children: weakref.WeakSet[Self]
    _type: Type[SerializableT]

    def __init__(self, default: SerializableT):

        self._default = default
        self._value = default
        self._isSet = False

        self._value_change_callbacks = CallbackRegistry()
        self._modification_notification_callbacks = CallbackRegistry()

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
            value: The value that this Key will now hold.

        Returns:
            None.
        """

        prev_value = self.get()
        previously_set = self.isSet()

        self._value = value
        self._isSet = True

        if prev_value != self.get():
            self._value_change_callbacks.callAll(self.get())
            for child in self.children():
                child._notifyParentValueChanged()

        if not previously_set or prev_value != self.get():
            self._notifyModification()

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

        self._notifyModification()

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
        changes, even if it was not modified itself; for instance, this will
        happen if there is no value currently set on it and its parent's value
        changed.

        The callback will be called with the new value as its argument.

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

    def onKeyModifiedCall(self, callback: Callable[[Self], None]) -> None:
        """
        Adds a callback to be called whenever this Key is modified, even if
        the value it reports does not end up changing.

        The callback will be called with this Key instance as its argument.

        Args:
            callback: A callable that takes one argument of the same type as
                this Key, and that returns None.

        Returns:
            None.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._modification_notification_callbacks.add(callback)

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

    def _notifyModification(self):

        self._modification_notification_callbacks.callAll(self)

    def new(self) -> Self:
        """
        Returns a new instance of this Key with the same default value.

        Returns:
            A new Key.
        """

        return self.__class__(default=self._default)

    def __repr__(self) -> str:

        return f"<Key[{self._type.__name__}]:{serialize(self.get())}>"


def NewKey(default: SerializableT) -> Key[SerializableT]:
    """
    Creates a new Key field with the given default value, to be used in the
    definition of a Section or a Settings class. The type of the Key is inferred
    from the type of the default value.

    This function must be used instead of normal instantiation when adding a
    Key to a Settings or a Section definition. (This is because, under the
    hood, both Section and Settings classes are dataclasses, and their
    attributes must be dataclass fields. This function takes care of that.)

    Args:
        default: The value that this Key will return when not otherwise set;
            the type of this default determines the type of the Key.

    Returns:
        A dataclass field bound to a Key of the requisite type.

    Note:
        It typically does not make sense to call this function outside of the
        definition of a Settings or a Section class.

    Example:

    >>> import sunset
    >>> class ExampleSettings(sunset.Settings):
    ...     example_key: sunset.Key[int] = sunset.NewKey(default=0)

    >>> settings = ExampleSettings()
    """

    return field(default_factory=Key(default=default).new)
