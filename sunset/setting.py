import weakref

from dataclasses import field
from typing import Callable, Generic, Iterator, Optional, Sequence

from typing_extensions import Self

from .registry import CallbackRegistry
from .serializers import SerializableT, deserialize, serialize


class Setting(Generic[SerializableT]):
    def __init__(self, default: SerializableT, doc: str = ""):

        self._doc = doc
        self._default = default
        self._value = default
        self._isSet = False

        self._value_change_callbacks: CallbackRegistry[
            SerializableT
        ] = CallbackRegistry()
        self._modification_notification_callbacks: CallbackRegistry[
            Self
        ] = CallbackRegistry()

        self._parent: Optional[weakref.ref[Self]] = None
        self._children: weakref.WeakSet[Self] = weakref.WeakSet()

        # Keep a runtime reference to the practical type contained in this
        # setting.

        self._type = type(default)

    def get(self) -> SerializableT:

        if self.isSet():
            return self._value

        parent = self.parent()
        if parent is not None:
            return parent.get()

        return self._default

    def set(self, value: SerializableT) -> None:

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

        return self._isSet

    def onValueChangeCall(
        self, callback: Callable[[SerializableT], None]
    ) -> None:
        """
        Add a callback to be called whenever the value exported by this setting
        changes, even if it was not modified itself. (For instance, if it's
        unset and its parent's value changed.)
        """

        self._value_change_callbacks.add(callback)

    def onSettingModifiedCall(self, callback: Callable[[Self], None]) -> None:
        """
        Add a callback to be called whenever this setting is modified, even if
        the value it reports does not end up changing.
        """

        self._modification_notification_callbacks.add(callback)

    def inheritFrom(self: Self, parent: Optional[Self]) -> None:

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

        return self._parent() if self._parent is not None else None

    def children(self: Self) -> Iterator[Self]:

        yield from self._children

    def dump(self) -> Sequence[tuple[str, str]]:

        if self.isSet():
            return [("", serialize(self.get()))]
        else:
            return []

    def restore(self, data: Sequence[tuple[str, str]]) -> None:

        if len(data) != 1:

            # For a Setting there should only be one piece of data. If there is
            # more, this part of the dump is invalid. Abort here.

            return

        name, value = data[0]

        if name:

            # For a setting, there should be no name. If there is one, it
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


def NewSetting(default: SerializableT, doc: str = "") -> Setting[SerializableT]:

    return field(default_factory=lambda: Setting(default=default, doc=doc))
