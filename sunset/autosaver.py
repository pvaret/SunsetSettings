import os
import pathlib
import tempfile

from typing import Any, TypeVar, Union

from .settings import Settings
from .timer import PersistentTimer, TimerProtocol

_TimerT = TypeVar("_TimerT", bound=TimerProtocol)


class AutoSaver:
    """
    AutoSaver is a helper class that can take care of loading and saving
    settings automatically and safely.

    On instantiation, it automatically loads settings from the given file path,
    if that file exists.

    When saving, it uses a two-steps mechanism to ensure the atomicity of the
    operation. That is to say, the operation either entirely succeeds or
    entirely fails; AutoSaver will never write an incomplete settings file.

    Saving automatically creates the parent directories of the target path if
    those don't exist yet.

    If the `save_on_update` argument is set to True, AutoSaver will save the
    settings whenever they are updated. If the `save_on_delete` argument is set
    to True, AutoSaver will save the settings when its own instance is about to
    get deleted.

    AutoSaver can also be used as a context manager. Using it as a context
    manager is the recommended usage.

    Args:
        settings: The Settings instance to load to and save from.

        path: The full path to the file to load the settings from and save
            them to. If this file does not exist yet, it will be created when
            saving for the first time.

        save_on_update: Whether to save the settings when they
            are updated in any way. Default: True.

        save_on_delete: Whether to save the settings when this AutoSaver
            instance is deleted. Default: True.

        save_delay: How long to wait, in seconds, before actually saving the
            settings when `save_on_update` is True and an update occurs. Setting
            this to a few seconds will batch updates for that long before
            triggering a save. If set to 0, the save is triggered immediately.
            Default: 0.

    Example:

    >>> from sunset import AutoSaver, Settings
    >>> class ExampleSettings(Settings):
    ...     ...
    >>> settings = ExampleSettings()
    >>> with AutoSaver(settings, "/path/to/settings.conf"):  # doctest: +SKIP
    ...     main_program_loop(settings)
    """

    _DIR_MODE: int = 0o755
    _FILE_MODE: int = 0o644
    _ENCODING: str = "UTF-8"

    _path: pathlib.Path
    _settings: Settings
    _dirty: bool
    _save_on_update: bool
    _save_on_delete: bool
    _save_delay: float
    _save_timer: TimerProtocol

    def __init__(
        self,
        settings: Settings,
        path: Union[pathlib.Path, str],
        save_on_update: bool = True,
        save_on_delete: bool = True,
        save_delay: float = 0.0,
    ) -> None:

        if isinstance(path, str):
            path = pathlib.Path(path)

        if path.exists():
            with open(path, encoding=self._ENCODING) as f:
                settings.load(f)

        self._dirty = False
        self._path = path
        self._save_on_update = save_on_update
        self._save_on_delete = save_on_delete
        self._save_delay = save_delay
        self._save_timer = PersistentTimer(self.saveIfNeeded)
        self._settings = settings
        self._settings.onUpdateCall(self._onSettingsUpdated)

    def doSave(self) -> None:
        """
        Unconditionally saves the settings attached to this AutoSaver instance.

        This method uses a two-steps mechanism to perform the save, in order to
        make the save atomic. The settings are first saved to a temporary file,
        and if successful, that temporary file then replaces the actual settings
        file.

        If the directory where the settings file is located does not exist, this
        method automatically creates it.

        Returns:
            None.
        """

        self._save_timer.cancel()

        dir = self._path.parent
        dir.mkdir(parents=True, mode=self._DIR_MODE, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            dir=dir,
            prefix=self._path.name,
            mode="xt",
            encoding=self._ENCODING,
            delete=False,
        ) as tmp:
            self._settings.save(tmp.file, blanklines=True)
            os.chmod(tmp.name, self._FILE_MODE)
            os.rename(tmp.name, self._path)

        self._dirty = False

    def saveIfNeeded(self) -> bool:
        """
        Performs a save if and only if there are pending, unsaved changes in the
        settings attached to this AutoSaver instance.

        Returns:
            True if a save was performed, else False.
        """

        save_needed = self._dirty

        self._save_timer.cancel()

        if save_needed:
            self.doSave()

        return save_needed

    def _onSettingsUpdated(self, _: Any) -> None:

        self._dirty = True
        if self._save_on_update:
            self._save_timer.start(self._save_delay)

    def setSaveTimerClass(self, timer_class: type[_TimerT]) -> _TimerT:
        """
        Internal.
        """

        self._save_timer = timer = timer_class(self.saveIfNeeded)
        return timer

    def __del__(self) -> None:

        if self._save_on_delete:
            self.saveIfNeeded()

    def __enter__(self) -> "AutoSaver":

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore

        self.saveIfNeeded()
