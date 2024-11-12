import threading
import weakref
from collections.abc import Callable, Iterator, MutableMapping, MutableSet
from types import MethodType
from typing import Any, TypeVar, cast

_T = TypeVar("_T")
_C = TypeVar("_C", bound=Callable[..., Any])


class NonHashableSet(MutableSet[_T]):
    """
    An implementation of a set that can contain non-hashable elements.

    Elements that are not hashable are distinguished by their id.
    """

    _contents: MutableMapping[int, _T]
    _lock: threading.RLock

    def __init__(self, mapping_type: type[MutableMapping[int, _T]] = dict) -> None:
        super().__init__()

        self._contents = mapping_type()
        self._lock = threading.RLock()

    @staticmethod
    def _computeHash(value: object) -> int:
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
        with self._lock:
            self._contents[self._computeHash(value)] = value

    def discard(self, value: _T) -> None:
        try:
            with self._lock:
                del self._contents[self._computeHash(value)]
        except KeyError:
            pass

    def __contains__(self, obj: object) -> bool:
        return self._computeHash(obj) in self._contents

    def __iter__(self) -> Iterator[_T]:
        with self._lock:
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


class WeakCallableSet(MutableSet[_C]):
    """
    A set-like type that stores callables without keeping references to them.

    The callables must have the same argument types and return type.
    """

    _content: NonHashableSet[weakref.ReferenceType[_C]]

    def __init__(self) -> None:
        super().__init__()

        # We can't just use a WeakNonHashableSet because it does not know how to
        # take references to methods. Instead we use a regular NonHashableSet
        # and manually take the proper type of weak reference when adding a
        # callable to the set.

        self._content = NonHashableSet()

    def add(self, value: _C) -> None:
        if isinstance(value, MethodType):
            r: weakref.ReferenceType[_C] = weakref.WeakMethod(
                cast(_C, value), self._onExpire
            )

        else:
            r = weakref.ref(value, self._onExpire)

        self._content.add(r)

    def __contains__(self, value: object) -> bool:
        return any(self._isSameCallable(candidate, value) for candidate in self)

    def __iter__(self) -> Iterator[_C]:
        for ref in self._content:
            value = ref()
            if value is not None:
                yield value

    def __len__(self) -> int:
        return len(self._content)

    def discard(self, value: _C) -> None:
        to_discard: list[weakref.ReferenceType[_C]] = []
        for ref in self._content:
            callable_ = ref()
            if callable_ is not None and self._isSameCallable(callable_, value):
                to_discard.append(ref)

        for ref in to_discard:
            self._content.discard(ref)

    @staticmethod
    def _isSameCallable(callable1: _C, callable2: object) -> bool:
        if isinstance(callable1, MethodType) and isinstance(callable2, MethodType):
            return (
                callable1.__self__ is callable2.__self__
                and callable1.__name__ == callable2.__name__
            )

        return callable1 is callable2

    def _onExpire(self, ref: weakref.ReferenceType[_C]) -> None:
        self._content.discard(ref)
