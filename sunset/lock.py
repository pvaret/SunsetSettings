import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from typing import ParamSpec, TypeVar

_R = TypeVar("_R")
_P = ParamSpec("_P")


class RWLock:
    """
    A reentrant read-write lock.

    Any number of threads can hold the lock for reads concurrently. Only one thread at a
    time can hold the lock for writes. When a thread holds the lock for writes, no other
    thread can hold the lock for reads, and vice versa.

    The lock is reentrant over both reads and writes in any combination.
    """

    _readers: dict[int, int]
    _readers_update: threading.Condition
    _writer_lock: threading.RLock

    def __init__(self) -> None:
        self._readers = {}
        self._readers_update = threading.Condition()
        self._writer_lock = threading.RLock()

    @staticmethod
    def _current_thread_id() -> int:
        return threading.current_thread().ident or 0

    def _acquire_read_lock(self, *, blocking: bool = True) -> bool:
        # Grab the writer lock before adding a reader, so that we don't add more readers
        # when there's a writer waiting.
        if not self._writer_lock.acquire(blocking):
            return False

        try:
            with self._readers_update:
                thread_id = self._current_thread_id()
                self._readers.setdefault(thread_id, 0)
                self._readers[thread_id] += 1

                # Enforce critical invariant.
                assert all(count > 0 for count in self._readers.values())  # noqa: S101

        finally:
            self._writer_lock.release()

        return True

    def _release_read_lock(self) -> None:
        with self._readers_update:
            thread_id = self._current_thread_id()
            if thread_id not in self._readers:
                msg = "Attempted to release read lock, but it was not held"
                raise RuntimeError(msg)

            self._readers[thread_id] -= 1

            if self._readers[thread_id] == 0:
                del self._readers[thread_id]
                self._readers_update.notify()

            # Enforce critical invariant.
            assert all(count > 0 for count in self._readers.values())  # noqa: S101

    def _acquire_write_lock(self, *, blocking: bool = True) -> bool:
        if not self._writer_lock.acquire(blocking):
            return False

        with self._readers_update:
            while self._readers:
                if (
                    len(self._readers) == 1
                    and self._current_thread_id() in self._readers
                ):
                    # Don't actually block if the only active reader is the current
                    # thread. This allows RWLock to be reentrant on any combination of
                    # reads and writes.
                    break

                if not blocking:
                    self._writer_lock.release()
                    return False

                self._readers_update.wait()

        return True

    def _release_write_lock(self) -> None:
        self._writer_lock.release()

    @contextmanager
    def lock_reads(self) -> Iterator[None]:
        self._acquire_read_lock(blocking=True)
        yield
        self._release_read_lock()

    @contextmanager
    def lock_writes(self) -> Iterator[None]:
        self._acquire_write_lock(blocking=True)
        yield
        self._release_write_lock()

    def with_read_lock(self, func: Callable[_P, _R]) -> Callable[_P, _R]:
        @wraps(func)
        def locked_func(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            with self.lock_reads():
                return func(*args, **kwargs)

        return locked_func

    def with_write_lock(self, func: Callable[_P, _R]) -> Callable[_P, _R]:
        @wraps(func)
        def locked_func(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            with self.lock_writes():
                return func(*args, **kwargs)

        return locked_func


SettingsLock = RWLock()
