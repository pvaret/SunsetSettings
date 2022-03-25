from typing import Iterator, MutableMapping, MutableSet, TypeVar
import weakref


_T = TypeVar("_T")


class IdSet(MutableSet[_T]):
    def __init__(self) -> None:

        self._contents: MutableMapping[int, _T] = {}

    def add(self, value: _T) -> None:

        self._contents[id(value)] = value

    def discard(self, value: _T) -> None:

        try:
            del self._contents[id(value)]
        except KeyError:
            pass

    def __contains__(self, value: _T) -> bool:

        return id(value) in self._contents

    def __iter__(self) -> Iterator[_T]:

        yield from self._contents.values()

    def __len__(self) -> int:

        return len(self._contents)


class WeakIdSet(IdSet[_T]):
    def __init__(self) -> None:

        super().__init__()

        self._contents: MutableMapping[int, _T] = weakref.WeakValueDictionary()
