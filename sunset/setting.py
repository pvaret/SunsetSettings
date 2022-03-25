from dataclasses import field
from typing import Callable, Generic, Iterator, Optional, Sequence
import weakref

from .registry import CallbackRegistry
from .serializers import SerializableT, deserialize, serialize


class Setting(Generic[SerializableT]):
    def __init__(self, default: SerializableT, doc: str = ""):

        self.doc = doc
        self.default = default
        self.value = default
        self._isSet = False

        self.callbacks: CallbackRegistry[SerializableT] = CallbackRegistry()
        self._parent: Optional[weakref.ref[Setting[SerializableT]]] = None
        self._children: weakref.WeakSet[
            Setting[SerializableT]
        ] = weakref.WeakSet()

        # Keep a runtime reference to the practical type contained in this
        # setting.
        self._type = type(default)

    def get(self) -> SerializableT:

        if self.isSet():
            return self.value

        parent = self.parent()
        if parent is not None:
            return parent.get()

        return self.default

    def set(self, value: SerializableT) -> None:

        prev_value = self.get()
        self.value = value
        self._isSet = True
        if prev_value != self.get():
            self.callbacks.callAll(self.get())
            for child in self.children():
                child._notifyParentValueChanged()

    def clear(self) -> None:

        prev_value = self.get()
        self._isSet = False
        self.value = self.default
        if prev_value != self.get():
            self.callbacks.callAll(self.get())
            for child in self.children():
                child._notifyParentValueChanged()

    def isSet(self) -> bool:

        return self._isSet

    def onChangeCall(self, callback: Callable[[SerializableT], None]) -> None:

        self.callbacks.add(callback)

    def inheritFrom(
        self: "Setting[SerializableT]",
        parent: Optional["Setting[SerializableT]"],
    ) -> None:

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

    def parent(
        self: "Setting[SerializableT]",
    ) -> "Optional[Setting[SerializableT]]":

        return self._parent() if self._parent is not None else None

    def children(
        self: "Setting[SerializableT]",
    ) -> "Iterator[Setting[SerializableT]]":

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

        success, value = deserialize(self._type, value)
        if not success:
            # The given value is not a valid serialized value for this
            # setting. Abort here.
            return

        self.set(value)

    def _notifyParentValueChanged(self):

        if self.isSet():
            return

        self.callbacks.callAll(self.get())

    def __repr__(self) -> str:

        return f"<Setting[{self._type.__name__}]: '{self.get()}'>"


def NewSetting(default: SerializableT, doc: str = "") -> Setting[SerializableT]:

    return field(default_factory=lambda: Setting(default=default, doc=doc))
