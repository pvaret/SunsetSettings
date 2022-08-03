import weakref

from dataclasses import field
from typing import Callable, Generic, Iterator, Optional, Sequence

from typing_extensions import Self

from .registry import CallbackRegistry
from .serializers import SerializableT, deserialize, serialize


class Setting(Generic[SerializableT]):
    """
    A single setting containing a typed value.

    When adding a Setting to a Section or a Settings definition, do not
    instantiate the Setting class directly; use the `sunset.NewSetting()`
    function instead.

    Setting instances support inheritance. If a Setting does not have a value
    explicitly set, and has a parent, then the value it will report is that of
    its parent.

    Setting instances can call a callback when their value changes, regardless
    of if its their own value that changed, or that inherited from a parent.
    Set this callback with the `onValueChangeCall()` method.

    Args:
        default: (str, int, bool, or anything that implements the
            `sunset.protocols.Serializable` protocol) The value that this
            Setting will return when not otherwise set; the type of this
            default determines the type of the Setting.

    Example:

    >>> import sunset
    >>> setting: sunset.Setting[int] = sunset.Setting(default=0)
    >>> setting.get()
    0
    >>> setting.set(42)
    >>> setting.get()
    42
    >>> child_setting: sunset.Setting[int] = sunset.Setting(default=0)
    >>> child_setting.setParent(setting)
    >>> child_setting.get()
    42
    >>> child_setting.set(101)
    >>> child_setting.get()
    101
    >>> setting.set(36)
    >>> setting.get()
    36
    >>> child_setting.get()
    101
    >>> child_setting.clear()
    >>> child_setting.get()
    36
    """

    _default: SerializableT
    _value: SerializableT
    _isSet: bool
    _value_change_callbacks: CallbackRegistry[SerializableT]
    _modification_notification_callbacks: CallbackRegistry[Self]
    _parent: Optional[weakref.ref[Self]]
    _children: weakref.WeakSet[Self]
    _type: type

    def __init__(self, default: SerializableT):

        self._default = default
        self._value = default
        self._isSet = False

        self._value_change_callbacks = CallbackRegistry()
        self._modification_notification_callbacks = CallbackRegistry()

        self._parent = None
        self._children = weakref.WeakSet()

        # Keep a runtime reference to the practical type contained in this
        # setting.

        self._type = type(default)

    def get(self) -> SerializableT:
        """
        Returns the current value of this setting.

        If this Setting instance does not currently have a value set on it,
        return that of its parent if any. If it does not have a parent, return
        the default value for this Setting.

        Returns:
            This Setting's current value.
        """

        if self.isSet():
            return self._value

        parent = self.parent()
        if parent is not None:
            return parent.get()

        return self._default

    def set(self, value: SerializableT) -> None:
        """
        Sets the given value on this Setting.

        Args:
            value: The value that this Setting will now hold.

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
        Clears the value currently set on this Setting, if any.

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
        Returns whether there is a value currently set on this Setting.

        Returns:
            True if a value is set on this Setting, else False.
        """

        return self._isSet

    def onValueChangeCall(
        self, callback: Callable[[SerializableT], None]
    ) -> None:
        """
        Adds a callback to be called whenever the value exported by this setting
        changes, even if it was not modified itself; for instance, if there is
        no value currently set on it and its parent's value changed.

        The callback will be called with the new value as its argument.

        Args:
            callback: A callable that takes one argument of the same type of the
                values held by this Setting, and that returns None.

        Returns:
            None.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._value_change_callbacks.add(callback)

    def onSettingModifiedCall(self, callback: Callable[[Self], None]) -> None:
        """
        Adds a callback to be called whenever this setting is modified, even if
        the value it reports does not end up changing.

        The callback will be called with this Setting instance as its argument.

        Args:
            callback: A callable that takes one argument of the same type as
                this Setting, and that returns None.

        Returns:
            None.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._modification_notification_callbacks.add(callback)

    def setParent(self: Self, parent: Optional[Self]) -> None:
        """
        Makes the given Setting the parent of this one. If None, remove this
        Setting's parent, if any.

        A Setting with a parent will inherit its parent's value when this
        Setting's own value is not currently set.

        This method is for internal purposes and you will typically not need to
        call it directly.

        Args:
            parent: Either a Setting that will become this Setting's parent, or
                None. The parent Setting must have the same type as this
                Setting.

        Returns:
            None.

        Note:
            A Setting and its parent, if any, do not increase each other's
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
        Returns the parent of this Setting, if any.

        Returns:
            A Setting instance of the same type as this one, or None.
        """

        return self._parent() if self._parent is not None else None

    def children(self: Self) -> Iterator[Self]:
        """
        Returns an iterator over the Setting instances that have this Setting
        as their parent.

        Returns:
            An iterator over Setting instances of the same type as this one.
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

        if len(data) != 1:

            # For a Setting there should only be one piece of data. If there is
            # more, this part of the dump is invalid. Abort here.

            return

        name, value = data[0]

        if name:

            # For a Setting, there should be no name. If there is one, it
            # means the dump is invalid. Abort here.

            return

        value = deserialize(self._type, value)
        if value is None:

            # The given value is not a valid serialized value for this
            # setting. Abort here.

            return

        self.set(value)

    def _notifyParentValueChanged(self):

        if self.isSet():
            return

        self._value_change_callbacks.callAll(self.get())

    def _notifyModification(self):

        self._modification_notification_callbacks.callAll(self)

    def __repr__(self) -> str:

        return f"<Setting[{self._type.__name__}]: '{self.get()}'>"


def NewSetting(default: SerializableT) -> Setting[SerializableT]:
    """
    Creates a new Setting field with the given default value, to be used in the
    definition of a Section or a Settings. The type of the Setting is inferred
    from the type of the default value.

    This function must be used instead of normal instantiation when adding a
    Setting to a Settings or a Section definition. (This is because, under the
    hood, both Section and Settings classes are dataclasses, and their
    attributes must be dataclass fields. This function takes care of that.)

    Args:
        default: The value that this Setting will return when not otherwise set;
            the type of this default determines the type of the Setting.

    Returns:
        A dataclass field bound to a Setting of the requisite type.

    Note:
        It typically does not make sense to call this function outside of the
        definition of a Settings or a Section.

    Example:

    >>> import sunset
    >>> class ExampleSettings(sunset.Settings):
    ...     example_setting: sunset.Setting[int] = sunset.NewSetting(default=0)

    >>> settings = ExampleSettings()
    """

    return field(default_factory=lambda: Setting(default=default))
