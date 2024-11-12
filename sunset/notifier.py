import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, Generic, ParamSpec

from sunset.sets import WeakCallableSet

_P = ParamSpec("_P")


class Notifier(Generic[_P]):
    """
    Records a set of callables of compatible types, and calls each of them with
    the given arguments when triggered.

    Recording a callable does not increase its reference count.
    """

    _callbacks: WeakCallableSet[Callable[_P, Any]]
    _inhibited: int = 0
    _lock: threading.Lock

    def __init__(self) -> None:
        self._callbacks = WeakCallableSet()
        self._lock = threading.Lock()

    def trigger(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        """
        Calls the recorded callables with the given arguments.

        Args:
            Anything compatible with the callable type recorded in this
            notifier.
        """

        if not self._inhibited:
            for callback in self._callbacks:
                callback(*args, **kwargs)

    def add(self, callback: Callable[_P, Any]) -> None:
        """
        Records a callable in this notifier.

        This does not increase the reference count of the callable.

        Args:
            callback: A callable to be recorded in this notifier.
        """

        self._callbacks.add(callback)

    def discard(self, callback: Callable[_P, Any]) -> None:
        """
        Forgets the given callable, if it was recorded in this notifier.

        If the callable was not previous recorded in this notifier, does
        nothing.

        Args:
            callback: The callable to be forgotten.
        """

        self._callbacks.discard(callback)

    @contextmanager
    def inhibit(self) -> Iterator[None]:
        """
        Returns a context manager that inhibits this notifier while active.

        An inhibited notifier no longer calls its recorded callable when triggered.

        Returns:
            A context manager. During its lifetime, triggering this notifier
            does nothing.
        """

        with self._lock:
            self._inhibited += 1
        try:
            yield None
        finally:
            with self._lock:
                self._inhibited -= 1
