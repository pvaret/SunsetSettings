import threading

from functools import wraps
from typing import Callable, TypeVar

# TODO: Remove when it's time to deprecate Python 3.9 support.
from typing_extensions import Concatenate, ParamSpec


_Self = TypeVar("_Self", bound="Lockable")
_R = TypeVar("_R")
_P = ParamSpec("_P")


class Lockable:
    """
    Internal.

    A helper mixin that provides a context manager to lock a class method's
    against one another.
    """

    _lock: threading.RLock

    def __init__(self) -> None:
        super().__init__()

        self._lock = threading.RLock()

    @staticmethod
    def with_lock(
        method: Callable[Concatenate[_Self, _P], _R]
    ) -> Callable[Concatenate[_Self, _P], _R]:
        @wraps(method)
        def locked_method(
            self: _Self, *args: _P.args, **kwargs: _P.kwargs
        ) -> _R:
            # pylint: disable-next=protected-access
            with self._lock:
                return method(self, *args, **kwargs)

        return locked_method
