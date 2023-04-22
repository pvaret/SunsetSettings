import logging
import pathlib

from typing import Any, Callable

import pytest

from pytest_mock import MockerFixture

from sunset import AutoSaver, Key, Settings


class MockTimer:
    _clock: float
    _interval: float
    _function: Callable[[], None]

    def __init__(self, function: Callable[[], Any]) -> None:
        self._function = function
        self._interval = 0
        self._clock = -1.0

    def cancel(self) -> None:
        self._clock = -1.0

    def start(self, interval: float) -> None:
        if self._clock < 0:
            self._interval = interval
            self._clock = 0.0

    def advanceTime(self, time: float) -> None:
        if self._clock >= 0:
            self._clock += time
            if self._clock >= self._interval:
                self._function()


class ExampleSettings(Settings):
    key_str = Key(default="")


class TestAutosaver:
    def test_load_on_init(self, tmp_path: pathlib.Path) -> None:
        settings_file = tmp_path / "test.conf"
        settings_file.write_text("[main]\nkey_str = test\n")

        settings = ExampleSettings()

        assert settings.key_str.get() == ""

        AutoSaver(settings, settings_file)

        assert settings.key_str.get() == "test"

    def test_no_load_on_init(self, tmp_path: pathlib.Path) -> None:
        settings_file = tmp_path / "test.conf"
        settings_file.write_text("[main]\nkey_str = test\n")

        settings = ExampleSettings()

        assert settings.key_str.get() == ""

        AutoSaver(settings, settings_file, load_on_init=False)

        assert settings.key_str.get() == ""

    def test_no_unneeded_saving(self, tmp_path: pathlib.Path) -> None:
        settings_file = tmp_path / "test.conf"
        settings = ExampleSettings()
        autosaver = AutoSaver(
            settings, settings_file, save_on_update=True, save_on_delete=True
        )

        assert not settings_file.exists()

        autosaver.__del__()  # Simulate garbage collection.

        assert not settings_file.exists()

    def test_autosave_on_update(self, tmp_path: pathlib.Path) -> None:
        settings_file = tmp_path / "test.conf"
        settings = ExampleSettings()
        autosaver = AutoSaver(settings, settings_file, save_on_delete=False)

        assert not settings_file.exists()

        settings.key_str.set("test")

        assert settings_file.exists()
        assert settings_file.read_text() == "[main]\nkey_str = test\n"

        del autosaver  # So that it's not unused.

    def test_autosave_on_delete(self, tmp_path: pathlib.Path) -> None:
        settings_file = tmp_path / "test.conf"
        settings = ExampleSettings()
        autosaver = AutoSaver(settings, settings_file, save_on_update=False)

        settings.key_str.set("test")

        assert not settings_file.exists()

        autosaver.__del__()  # Simulate garbage collection.

        assert settings_file.exists()
        assert settings_file.read_text() == "[main]\nkey_str = test\n"

    def test_autosave_creates_missing_dirs(
        self, tmp_path: pathlib.Path
    ) -> None:
        settings = ExampleSettings()
        settings_file = tmp_path / "multiple" / "levels" / "deep" / "test.conf"
        autosaver = AutoSaver(
            settings, settings_file, save_on_update=False, save_on_delete=False
        )

        assert not settings_file.parent.exists()

        autosaver.doSave()

        assert settings_file.parent.exists()

    def test_context_manager(self, tmp_path: pathlib.Path) -> None:
        settings = ExampleSettings()
        settings_file = tmp_path / "test.conf"
        with AutoSaver(
            settings, settings_file, save_on_update=False, save_on_delete=False
        ):
            settings.key_str.set("test")
            assert not settings_file.exists()

        assert settings_file.exists()
        assert settings_file.read_text() == "[main]\nkey_str = test\n"

    def test_delayed_save(self, tmp_path: pathlib.Path) -> None:
        settings_file = tmp_path / "test.conf"
        settings = ExampleSettings()
        autosaver = AutoSaver(
            settings, settings_file, save_on_delete=False, save_delay=2.0
        )

        mock_timer = autosaver.setSaveTimerClass(MockTimer)

        assert not settings_file.exists()

        settings.key_str.set("test 1")

        assert not settings_file.exists()

        settings.key_str.set("test 2")
        settings.key_str.set("test 3")

        mock_timer.advanceTime(1.0)

        assert not settings_file.exists()

        mock_timer.advanceTime(2.0)

        assert settings_file.exists()

    def test_expand_user(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def expanduser(path: pathlib.Path) -> pathlib.Path:
            if not str(path).startswith("~"):
                return path
            return pathlib.Path("HOME") / str(path).lstrip("~").lstrip("/")

        monkeypatch.setattr(pathlib.Path, "expanduser", expanduser)

        saver1 = AutoSaver(ExampleSettings(), "/no/tilde", load_on_init=False)
        assert str(saver1.path()) == "/no/tilde"

        saver2 = AutoSaver(
            ExampleSettings(), "~/with/tilde", load_on_init=False
        )
        assert str(saver2.path()) == "HOME/with/tilde"

    def test_exceptions(
        self, tmp_path: pathlib.Path, mocker: MockerFixture
    ) -> None:
        settings_file = tmp_path / "actually_a_folder"
        settings_file.mkdir(parents=True)

        logger_stub = mocker.MagicMock(logging.Logger)

        saver = AutoSaver(
            ExampleSettings(),
            settings_file,
            load_on_init=False,
            logger=logger_stub,
        )

        logger_stub.error.assert_not_called()  # type: ignore
        assert settings_file.exists()
        assert not saver.doLoad()
        logger_stub.error.assert_called_once()  # type: ignore
        logger_stub.error.reset_mock()  # type: ignore

        assert not saver.doSave()
        logger_stub.error.assert_called_once()  # type: ignore
