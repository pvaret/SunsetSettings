import threading

from unittest.mock import MagicMock

from pytest import MonkeyPatch

from sunset import PersistentTimer


class TestPersistentTimer:
    def test_timer_no_delay(self, monkeypatch: MonkeyPatch) -> None:
        mock_cls = MagicMock(threading.Timer, autospec=True)
        mock = mock_cls.return_value
        monkeypatch.setattr(threading, "Timer", mock_cls)

        def test():
            pass

        timer = PersistentTimer(test)

        assert timer._timer is None  # type: ignore

        timer.start(0.0)

        mock_cls.assert_not_called()
        mock.start.assert_not_called()

        assert timer._timer is None  # type: ignore

        timer.cancel()

        assert timer._timer is None  # type: ignore

    def test_timer_with_delay(self, monkeypatch: MonkeyPatch) -> None:
        mock_cls = MagicMock(threading.Timer, autospec=True)
        mock = mock_cls.return_value
        monkeypatch.setattr(threading, "Timer", mock_cls)

        def test():
            pass

        timer = PersistentTimer(test)

        assert timer._timer is None  # type: ignore

        timer.start(1.0)

        mock_cls.assert_called_once_with(1.0, timer._timeout)  # type: ignore
        assert timer._timer is mock  # type: ignore
        mock.start.assert_called_once()  # type: ignore

        timer.cancel()

        assert timer._timer is None  # type: ignore
