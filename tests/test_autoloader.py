from pathlib import Path
from typing import cast

from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from sunset import AutoLoader, Key, Settings
from sunset.autoloader import MonitorForChange, MonitorProtocol
from sunset.timer import TimerProtocol

from .test_timer import MockTimer


class DummyMonitor(MonitorForChange):
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class ExampleSettings(Settings):
    key_str = Key(default="")


class TestMonitor:
    def test_monitor_triggers_callback_on_change(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        callback = mocker.stub()
        path = mocker.patch("sunset.autoloader.Path", mocker.Mock(Path))
        mstats = mocker.Mock()
        mstats.st_mtime = 0
        path.stat.return_value = mstats
        mocker.patch("sunset.autoloader.PersistentTimer", MockTimer)
        monitor = MonitorForChange(path, callback)
        monitor.start()
        timer = monitor._timer
        assert timer is not None
        timer = cast(MockTimer, timer)

        # Simulate timer ticks by advancing time
        timer.advanceTime(1.0)
        path.stat.assert_called()
        path.stat.reset_mock()
        callback.assert_not_called()

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_not_called()

        mstats.st_mtime = 1

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_not_called()

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_called_once()
        callback.reset_mock()

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_not_called()

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_not_called()

        mstats.st_mtime = 2

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_not_called()

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_called_once()
        callback.reset_mock()

        monitor.stop()

    def test_monitor_supports_live_file_creation(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        path = mocker.patch("sunset.autoloader.Path", mocker.Mock(Path))
        path.stat = mocker.stub()
        path.stat.side_effect = OSError("File not found")

        mocker.patch("sunset.autoloader.PersistentTimer", MockTimer)

        callback = mocker.stub()
        monitor = MonitorForChange(path, callback)
        monitor.start()

        timer = monitor._timer
        assert timer is not None
        timer = cast(MockTimer, timer)

        callback.assert_not_called()

        timer.advanceTime(1.0)
        path.stat.assert_called()
        path.stat.reset_mock()
        callback.assert_not_called()

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_not_called()

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_not_called()

        # Simulate file creation.
        path.stat.side_effect = None
        mstats = mocker.Mock()
        mstats.st_mtime = 0
        path.stat.return_value = mstats

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_not_called()

        timer.advanceTime(1.0)
        path.stat.assert_called_once()
        path.stat.reset_mock()
        callback.assert_called_once()
        monitor.stop()

    def test_starting_and_stopping_a_monitor_is_idempotent(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        path = tmp_path / "test.conf"
        callback = mocker.Mock()
        mock_timer = mocker.Mock(TimerProtocol)

        mocker.patch("sunset.autoloader.PersistentTimer", mock_timer)
        monitor = MonitorForChange(path, callback)

        mock_timer().start.assert_not_called()

        monitor.start()
        mock_timer().start.assert_called_once()
        mock_timer().start.reset_mock()

        monitor.start()
        mock_timer().start.assert_not_called()
        mock_timer().cancel.assert_not_called()

        monitor.stop()
        mock_timer().cancel.assert_called_once()
        mock_timer().cancel.reset_mock()

        monitor.stop()
        mock_timer().cancel.assert_not_called()


class TestAutoLoader:
    def test_autoloader_loads_settings_on_init(self, tmp_path: Path) -> None:
        settings_file = tmp_path / "test.conf"
        settings_file.write_text("[main]\nkey_str = test\n")

        settings = ExampleSettings()
        assert settings.key_str.get() == ""

        with AutoLoader(settings, settings_file, _monitor_factory=DummyMonitor):
            assert settings.key_str.get() == "test"

    def test_autoloader_reloads_settings_on_change(self, tmp_path: Path) -> None:
        settings_file = tmp_path / "test.conf"

        settings = ExampleSettings()

        with AutoLoader(
            settings, settings_file, _monitor_factory=DummyMonitor
        ) as autoloader:
            assert settings.key_str.get() == ""

            # Simulate a change in the settings file.
            settings_file.write_text("[main]\nkey_str = new value\n")
            autoloader._monitor.triggerCallback()

            assert settings.key_str.get() == "new value"

    def test_autoloader_start_and_stops_monitor(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        monitor = mocker.Mock(spec=MonitorProtocol)
        monitor().start = mocker.stub()
        monitor().stop = mocker.stub()
        monitor().trigger_callback = mocker.stub()

        settings_file = tmp_path / "test.conf"
        settings_file.write_text("")

        autoloader = AutoLoader(Settings(), settings_file, _monitor_factory=monitor)

        # The file monitor is started on init.
        monitor().start.assert_called_once()
        monitor().start.reset_mock()
        monitor().stop.assert_not_called()

        with autoloader:
            # The file monitor is started on entering the context manager.
            monitor().start.assert_called_once()
            monitor().start.reset_mock()
            monitor().stop.assert_not_called()

        # The file monitor is stopped on exiting the context manager.
        monitor().stop.assert_called_once()
        monitor().stop.reset_mock()
        monitor().start.assert_not_called()

        # This remains true if the context manager is entered again later on.
        with autoloader:
            monitor().start.assert_called_once()
            monitor().start.reset_mock()
            monitor().stop.assert_not_called()

        monitor().stop.assert_called_once()
        monitor().stop.reset_mock()
        monitor().start.assert_not_called()

        # The monitor is stopped when the autoloader is garbage collected.
        monitor.reset_mock()  # Clear the mock's references to the autoloader object.
        del autoloader
        monitor().start.assert_not_called()
        monitor().stop.assert_called_once()

    def test_expand_user(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        def expanduser(path: Path) -> Path:
            if not str(path).startswith("~"):
                return path
            return Path("HOME") / str(path).lstrip("~").lstrip("/")

        monkeypatch.setattr(Path, "expanduser", expanduser)

        autoloader1 = AutoLoader(
            ExampleSettings(), "/no/tilde", _monitor_factory=DummyMonitor
        )
        assert str(autoloader1.path()) == "/no/tilde"

        autoloader2 = AutoLoader(
            ExampleSettings(), "~/with/tilde", _monitor_factory=DummyMonitor
        )
        assert str(autoloader2.path()) == "HOME/with/tilde"
