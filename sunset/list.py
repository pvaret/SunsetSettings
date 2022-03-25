from dataclasses import field
from typing import Any, Callable, Iterator, Optional, Sequence, Type
import weakref

from .idset import WeakIdSet
from .section import SectionT


class List(list[SectionT]):
    def __init__(self, _type: Type[SectionT]) -> None:

        self._parent: Optional[weakref.ref[List[SectionT]]] = None
        self._children: WeakIdSet[List[SectionT]] = WeakIdSet()

        self._type = _type

    def inheritFrom(self, parent: Optional["List[SectionT]"]):

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

    def parent(self) -> "Optional[List[SectionT]]":

        return self._parent() if self._parent is not None else None

    def children(self) -> "Iterator[List[SectionT]]":

        yield from self._children

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


def NewList(section: Type[SectionT]) -> List[SectionT]:

    factory: Callable[[], List[Any]] = lambda: List[SectionT](section)
    return field(default_factory=factory)
