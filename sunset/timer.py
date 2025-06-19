import threading
from collections.abc import Callable
from typing import Any, Protocol


class TimerProtocol(Protocol):
    def __init__(self, *, looping: bool = False) -> None: ...

    def start(self, interval: float, function: Callable[[], Any]) -> None: ...

    def cancel(self) -> None: ...


class PersistentTimer:
    _timer: threading.Timer | None
    _lock: threading.Lock
    _looping: bool

    def __init__(self, *, looping: bool = False) -> None:
        self._timer = None
        self._looping = looping
        self._lock = threading.Lock()

    def start(self, interval: float, function: Callable[[], Any]) -> None:
        if interval <= 0.0:
            self._triggerFunction(function)
            return

        with self._lock:
            if self._timer is None:
                self._timer = threading.Timer(
                    interval, self._triggerFunction, [function]
                )
                self._timer.start()

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _triggerFunction(self, function: Callable[[], Any]) -> None:
        interval = self._timer.interval if self._timer else None
        self.cancel()
        function()

        if self._looping and interval is not None:
            self.start(interval, function)

    def __del__(self) -> None:
        self.cancel()
