from typing import MutableSet, Sequence, TextIO
from typing_extensions import Self

from .exporter import idify, loadFromFile, saveToFile
from .idset import IdSet
from .section import Section

_MAIN = "main"


class Settings(Section):

    MAIN: str = _MAIN

    def __post_init__(self) -> None:

        super().__post_init__()
        self._id: str = self.MAIN
        self._children: MutableSet[Self] = IdSet()

    def derive(self: Self) -> Self:

        new = super().derive()
        new._id = ""
        return new

    def deriveAs(self: Self, name: str) -> Self:

        for child in self.children():
            if idify(name) == child.id():
                return child

        new = self.derive()
        new.setId(name)
        return new

    def setId(self, id: str) -> None:

        self._id = idify(id)

    def id(self) -> str:

        return self._id

    def hierarchy(self) -> list[str]:

        if not self.id():
            return []

        parent = self.parent()
        if parent is not None and not parent.hierarchy():
            return []

        return (parent.hierarchy() if parent is not None else []) + [self.id()]

    def dumpAll(
        self,
    ) -> Sequence[tuple[Sequence[str], Sequence[tuple[str, str]]]]:

        hierarchy = self.hierarchy()
        if not hierarchy:
            # This is an anonymous structure, don't dump it.
            return []

        ret: list[tuple[Sequence[str], Sequence[tuple[str, str]]]] = []
        ret.append((hierarchy, self.dump()))

        children = list(self.children())
        children.sort(key=lambda child: child.id())
        for child in children:
            for hierarchy, dump in child.dumpAll():
                ret.append((hierarchy, dump))

        return ret

    def restoreAll(
        self,
        data: Sequence[tuple[Sequence[str], Sequence[tuple[str, str]]]],
    ) -> None:

        own_children: dict[str, Settings] = {}
        own_children_data: list[
            tuple[Sequence[str], Sequence[tuple[str, str]]]
        ] = []

        for hierarchy, dump in data:

            hierarchy = list(map(idify, hierarchy))
            if not hierarchy:
                continue

            if not hierarchy[0]:
                continue

            if hierarchy[0] != self.id():
                continue

            if len(hierarchy) == 1:
                # This dump applies specifically to this instance.
                self.restore(dump)

            else:
                child_id = idify(hierarchy[1])
                if not child_id:
                    continue

                if child_id not in own_children:
                    own_children[child_id] = self.deriveAs(child_id)
                own_children_data.append((hierarchy[1:], dump))

        for child in own_children.values():
            child.restoreAll(own_children_data)

    def save(self, file: TextIO) -> None:

        saveToFile(file, self.dumpAll(), self.MAIN)

    def load(self, file: TextIO) -> None:

        data = loadFromFile(file, self.MAIN)
        self.restoreAll(data)
