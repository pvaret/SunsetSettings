import weakref

from dataclasses import field
from typing import (
    Any,
    Callable,
    Iterator,
    MutableSequence,
    Optional,
    Sequence,
    SupportsIndex,
    Type,
    Union,
)

from typing_extensions import Self

from .non_hashable_set import WeakNonHashableSet
from .registry import CallbackRegistry
from .section import SectionT


class List(MutableSequence[SectionT]):
    def __init__(self, _type: Type[SectionT]) -> None:

        self._contents: list[SectionT] = []

        self._parent: Optional[weakref.ref[Self]] = None
        self._children: WeakNonHashableSet[Self] = WeakNonHashableSet()
        self._modification_notification_callbacks: CallbackRegistry[
            Self
        ] = CallbackRegistry()

        self._type = _type

    def insert(self, index: SupportsIndex, value: SectionT) -> None:

        self._contents.insert(index, value)
        self._notifyModification(self)

        value.onSettingModifiedCall(self._notifyModification)

    def __getitem__(self, index: SupportsIndex) -> SectionT:

        return self._contents[index]

    def __setitem__(self, index: SupportsIndex, value: SectionT) -> None:

        self._contents[index] = value
        self._notifyModification(self)

        value.onSettingModifiedCall(self._notifyModification)

    def __delitem__(self, index: SupportsIndex) -> None:

        del self._contents[index]
        self._notifyModification(self)

    def __len__(self) -> int:

        return len(self._contents)

    def inheritFrom(self, parent: Optional[Self]):

        old_parent = self.parent()
        if old_parent is not None:
            old_parent._children.discard(self)

        if parent is None:
            self._parent = None
        else:
            self._parent = weakref.ref(parent)
            parent._children.add(self)

    def iterAll(self) -> Iterator[SectionT]:

        yield from self
        parent = self.parent()
        if parent is not None:
            yield from parent.iterAll()

    def parent(self) -> Optional[Self]:

        return self._parent() if self._parent is not None else None

    def children(self) -> Iterator[Self]:

        yield from self._children

    def onSettingModifiedCall(self, callback: Callable[[Self], None]) -> None:

        self._modification_notification_callbacks.add(callback)

    def dump(self) -> Sequence[tuple[str, str]]:

        ret: list[tuple[str, str]] = []

        # Count from 1, as it's more human friendly.

        for i, value in enumerate(self, start=1):
            for subAttrName, dump in value.dump():
                name = ".".join(s for s in (str(i), subAttrName) if s)
                ret.append((name, dump))

        return ret

    def restore(self, data: Sequence[tuple[str, str]]) -> None:

        subitems: dict[str, SectionT] = {}

        for name, dump in data:
            if "." in name:
                item_name, subname = name.split(".", 1)
            else:
                item_name, subname = name, ""
            if item_name not in subitems:
                subitems[item_name] = self._type()
                self.append(subitems[item_name])

            subitems[item_name].restore([(subname, dump)])

    def _notifyModification(self, value: Union[SectionT, Self]) -> None:

        if isinstance(value, List) or value in self:
            self._modification_notification_callbacks.callAll(self)


def NewList(section: Type[SectionT]) -> List[SectionT]:

    factory: Callable[[], List[Any]] = lambda: List[SectionT](section)
    return field(default_factory=factory)
