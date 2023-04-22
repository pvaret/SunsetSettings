import threading

from typing import Any, Callable, Optional, Protocol


class TimerProtocol(Protocol):
    def __init__(self, function: Callable[[], Any]) -> None:
        ...

    def start(self, interval: float) -> None:
        ...

    def cancel(self) -> None:
        ...


class PersistentTimer:
    _timer: Optional[threading.Timer]
    _function: Callable[[], Any]
    _lock: threading.Lock

    def __init__(self, function: Callable[[], Any]) -> None:
        self._timer = None
        self._function = function
        self._lock = threading.Lock()

    def start(self, interval: float) -> None:
        if interval <= 0.0:
            self._timeout()
            return

        with self._lock:
            if self._timer is None:
                self._timer = threading.Timer(interval, self._timeout)
                self._timer.start()

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _timeout(self) -> None:
        self.cancel()
        self._function()

    def __del__(self) -> None:
        self.cancel()
