import weakref

from types import MethodType
from typing import Callable, Iterator, MutableSet, TypeVar

from .non_hashable_set import NonHashableSet

_T = TypeVar("_T")


class CallbackRegistry(MutableSet[Callable[[_T], None]]):

    _content: NonHashableSet[weakref.ref[Callable[[_T], None]]]

    def __init__(self) -> None:

        # We can just use a WeakIdSet because it does not know how to take
        # references to methods. Instead we do that ourselves, using a proper
        # IdSet.

        self._content = NonHashableSet()

    def add(self, value: Callable[[_T], None]) -> None:

        if isinstance(value, MethodType):

            # Note: WeakMethod has incorrect type annotations, so we have to
            # ignore types here.

            r = weakref.WeakMethod(value, self._onExpire)  # type: ignore

        else:
            r = weakref.ref(value, self._onExpire)
        self._content.add(r)

    def __contains__(self, callback: Callable[[_T], None]) -> bool:

        return any(
            self._isSameCallable(candidate, callback) for candidate in self
        )

    def __iter__(self) -> Iterator[Callable[[_T], None]]:

        for ref in self._content:
            value = ref()
            if value is not None:
                yield value

    def __len__(self) -> int:

        return len(self._content)

    def discard(self, value: Callable[[_T], None]) -> None:

        refs = list(self._content)
        for ref in refs:
            callable = ref()
            if callable is not None and self._isSameCallable(callable, value):
                self._content.discard(ref)

    def callAll(self, value: _T) -> None:

        for callback in self:
            callback(value)

    @staticmethod
    def _isSameCallable(
        callable1: Callable[[_T], None], callable2: Callable[[_T], None]
    ) -> bool:

        if isinstance(callable1, MethodType) and isinstance(
            callable2, MethodType
        ):
            return (
                callable1.__self__ is callable2.__self__
                and callable1.__name__ == callable2.__name__
            )

        else:
            return callable1 is callable2

    def _onExpire(self, ref: weakref.ref[Callable[[_T], None]]) -> None:

        self._content.discard(ref)
