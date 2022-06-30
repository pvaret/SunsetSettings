import weakref

from typing import Any, Iterator, MutableMapping, MutableSet, Type, TypeVar

_T = TypeVar("_T")


class NonHashableSet(MutableSet[_T]):
    """
    An implementation of a set that can contain non-hashable elements.

    Elements that are not hashable are distinguished by their id.
    """

    _contents: MutableMapping[int, _T]

    def __init__(
        self, mapping_type: Type[MutableMapping[int, _T]] = dict
    ) -> None:

        self._contents = mapping_type()

    def _computeHash(self, value: Any) -> int:

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

    def __contains__(self, object: Any) -> bool:

        return self._computeHash(object) in self._contents

    def __iter__(self) -> Iterator[_T]:

        yield from self._contents.values()

    def __len__(self) -> int:

        return len(self._contents)


class WeakNonHashableSet(NonHashableSet[_T]):
    """
    An implementation of a weak set that can contain non-hashable elements.

    Elements that are not hashable are distinguished by their id.
    """

    def __init__(self) -> None:

        super().__init__(mapping_type=weakref.WeakValueDictionary)
