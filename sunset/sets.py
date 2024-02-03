import weakref

from collections.abc import MutableSet
from types import MethodType

from typing import (
    Any,
    Callable,
    Iterator,
    MutableMapping,
    MutableSet,
    Type,
    TypeVar,
)

_T = TypeVar("_T")
_R = TypeVar("_R")


class NonHashableSet(MutableSet[_T]):
    """
    An implementation of a set that can contain non-hashable elements.

    Elements that are not hashable are distinguished by their id.
    """

    _contents: MutableMapping[int, _T]

    def __init__(
        self, mapping_type: Type[MutableMapping[int, _T]] = dict
    ) -> None:
        super().__init__()

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

    def __contains__(self, obj: Any) -> bool:
        return self._computeHash(obj) in self._contents

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


class WeakCallableSet(MutableSet[Callable[[_T], _R]]):
    """
    A set-like type that stores callables without keeping references to them.

    The callables must have the same argument types and return type.
    """

    _content: NonHashableSet[weakref.ref[Callable[[_T], _R]]]

    def __init__(self) -> None:
        super().__init__()

        # We can't just use a WeakNonHashableSet because it does not know how to
        # take references to methods. Instead we use a regular NonHashableSet
        # and manually take the proper type of weak reference when adding a
        # callable to the set.

        self._content = NonHashableSet()

    def add(self, value: Callable[[_T], _R]) -> None:
        if isinstance(value, MethodType):
            # Note: WeakMethod has incorrect type annotations, so we have to
            # ignore types here.

            r = weakref.WeakMethod(value, self._onExpire)  # type: ignore

        else:
            r = weakref.ref(value, self._onExpire)

        self._content.add(r)

    def __contains__(self, value: Any) -> bool:
        return any(self._isSameCallable(candidate, value) for candidate in self)

    def __iter__(self) -> Iterator[Callable[[_T], _R]]:
        for ref in self._content:
            value = ref()
            if value is not None:
                yield value

    def __len__(self) -> int:
        return len(self._content)

    def discard(self, value: Callable[[_T], _R]) -> None:
        refs = list(self._content)
        for ref in refs:
            callable_ = ref()
            if callable_ is not None and self._isSameCallable(callable_, value):
                self._content.discard(ref)

    def callAll(self, value: _T) -> None:
        for callback in self:
            callback(value)

    @staticmethod
    def _isSameCallable(
        callable1: Callable[[_T], _R], callable2: Callable[[_T], _R]
    ) -> bool:
        if isinstance(callable1, MethodType) and isinstance(
            callable2, MethodType
        ):
            return (
                callable1.__self__ is callable2.__self__
                and callable1.__name__ == callable2.__name__
            )

        return callable1 is callable2

    def _onExpire(self, ref: weakref.ref[Callable[[_T], _R]]) -> None:
        self._content.discard(ref)
