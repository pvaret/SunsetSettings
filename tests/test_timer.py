from collections.abc import Callable
import threading
from typing import Any

from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from sunset import PersistentTimer


class TestPersistentTimer:
    def test_timer_no_delay(
        self, mocker: MockerFixture, monkeypatch: MonkeyPatch
    ) -> None:
        mock_cls = mocker.MagicMock(threading.Timer, autospec=True)
        mock = mock_cls.return_value
        monkeypatch.setattr(threading, "Timer", mock_cls)

        def test() -> None: ...

        timer = PersistentTimer()

        assert timer._timer is None

        timer.start(0.0, test)

        mock_cls.assert_not_called()
        mock.start.assert_not_called()

        assert timer._timer is None

        timer.cancel()

        assert timer._timer is None

    def test_timer_with_delay(
        self, mocker: MockerFixture, monkeypatch: MonkeyPatch
    ) -> None:
        mock = mocker.MagicMock(threading.Timer, autospec=True)
        mock.return_value = mock
        monkeypatch.setattr(threading, "Timer", mock)

        def test() -> None: ...

        timer = PersistentTimer()

        assert timer._timer is None

        timer.start(1.0, test)

        mock.assert_called_once_with(1.0, timer._triggerFunction, [test])
        assert timer._timer is mock
        mock.start.assert_called_once()

        timer.cancel()

        assert timer._timer is None

    def test_timer_looping(
        self, mocker: MockerFixture, monkeypatch: MonkeyPatch
    ) -> None:
        timer_mock = mocker.MagicMock(threading.Timer, autospec=True)

        def mock_factory(
            interval: float, function: Callable[[], Any], args: list[Any]
        ) -> threading.Timer:
            timer_mock.interval = interval
            return timer_mock

        monkeypatch.setattr(threading, "Timer", mock_factory)

        called = mocker.Mock()

        persistent_timer = PersistentTimer(looping=True)

        assert persistent_timer._timer is None

        persistent_timer.start(1.0, called)

        assert persistent_timer._timer is timer_mock
        timer_mock.start.assert_called_once()
        timer_mock.start.reset_mock()

        called.assert_not_called()

        # Simulate the timer firing.
        persistent_timer._triggerFunction(called)

        # The callback should have been called.
        called.assert_called_once()

        # The timer should have restarted for a new loop.
        timer_mock.start.assert_called_once()

        persistent_timer.cancel()
        assert persistent_timer._timer is None


class MockTimer:
    # Not actually used in this file, but needed by other tests, so it makes sense to
    # have it defined somewhere semantically relevant.
    _clock: float
    _interval: float
    _function: Callable[[], Any] | None

    def __init__(self, *, looping: bool = False) -> None:
        self._function = None
        self._interval = 0
        self._clock = -1.0

    def cancel(self) -> None:
        self._clock = -1.0

    def start(self, interval: float, function: Callable[[], Any]) -> None:
        self._function = function
        if self._clock < 0:
            self._interval = interval
            self._clock = 0.0

    def advanceTime(self, time: float) -> None:
        if self._clock >= 0:
            self._clock += time
            if self._clock >= self._interval and self._function is not None:
                self._function()
