from typing import Iterator, MutableMapping, MutableSet, TypeVar
import weakref


_T = TypeVar("_T")


class IdSet(MutableSet[_T]):
    def __init__(self) -> None:

        self._contents: MutableMapping[int, _T] = {}

    def _computeHash(self, value: _T) -> int:

        # Try to return the normal hash for the value if possible. This is
        # because hash is more selective than id. For instance! If value is a
        # weakref, then hash properly identifies two distinct weakrefs to the
        # same object as equivalent, whereas id does not.
        # Sadly testing whether the value implements the Hashable proto does not
        # suffice. Dataclasses, for instance, implement the Hashable proto but
        # are not necessarily hashable.

        try:
            return hash(value)
        except TypeError:
            return id(value)

    def add(self, value: _T) -> None:

        self._contents[self._computeHash(value)] = value

    def discard(self, value: _T) -> None:

        try:
            del self._contents[self._computeHash(value)]
        except KeyError:
            pass

    def __contains__(self, value: _T) -> bool:

        return self._computeHash(value) in self._contents

    def __iter__(self) -> Iterator[_T]:

        yield from self._contents.values()

    def __len__(self) -> int:

        return len(self._contents)


class WeakIdSet(IdSet[_T]):
    def __init__(self) -> None:

        super().__init__()

        self._contents: MutableMapping[int, _T] = weakref.WeakValueDictionary()
