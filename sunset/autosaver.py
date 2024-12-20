import logging
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import IO, Any, Protocol, TypeVar

from sunset.timer import PersistentTimer, TimerProtocol

_TimerT = TypeVar("_TimerT", bound=TimerProtocol)


class _SavableProtocol(Protocol):
    """
    This protocol lets AutoSaver know how to use a Settings instance without
    having to import the actual Settings class.
    """

    def load(self, file: IO[str]) -> None: ...

    def save(self, file: IO[str], *, blanklines: bool = False) -> None: ...

    def onUpdateCall(self, callback: Callable[[Any], Any]) -> None: ...


class AutoSaver:
    """
    AutoSaver is a helper class that can take care of loading and saving
    settings automatically and safely.

    On instantiation, it automatically loads settings from the given file path,
    if that file exists, unless the `load_on_init` argument is set to False.

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

        load_on_init: Whether to load the settings when instantiating this
            AutoSaver, provided the settings path exists. Default: True.

        save_delay: How long to wait, in seconds, before actually saving the
            settings when `save_on_update` is True and an update occurs. Setting
            this to a few seconds will batch updates for that long before
            triggering a save. If set to 0, the save is triggered immediately.
            Default: 0.

        logger: A logger instance that will be used to log OS errors, if any,
            while loading or saving settings. If none is given, the default root
            logger will be used.

    Example:

    >>> from sunset import AutoSaver, Settings
    >>> class ExampleSettings(Settings):
    ...     ...
    >>> settings = ExampleSettings()
    >>> with AutoSaver(settings, "~/.config/my_app.conf"):  # doctest: +SKIP
    ...     main_program_loop(settings)
    """

    _DIR_MODE: int = 0o755
    _FILE_MODE: int = 0o644
    _ENCODING: str = "UTF-8"

    _path: Path
    _settings: _SavableProtocol
    _dirty: bool
    _save_on_update: bool
    _save_on_delete: bool
    _save_delay: float
    _save_timer: TimerProtocol
    _logger: logging.Logger

    def __init__(  # noqa: PLR0913
        self,
        settings: _SavableProtocol,
        path: Path | str,
        *,
        save_on_update: bool = True,
        save_on_delete: bool = True,
        load_on_init: bool = True,
        save_delay: float = 0.0,
        logger: logging.Logger | None = None,
    ) -> None:
        if isinstance(path, str):
            path = Path(path)

        path = path.expanduser()

        if logger is None:
            logger = logging.getLogger()

        self._dirty = False
        self._path = path
        self._save_on_update = save_on_update
        self._save_on_delete = save_on_delete
        self._save_delay = save_delay
        self._save_timer = PersistentTimer(self.saveIfNeeded)
        self._settings = settings
        self._settings.onUpdateCall(self._onSettingsUpdated)
        self._logger = logger

        if load_on_init:
            self.doLoad()

    def path(self) -> Path:
        """
        Returns the settings path for this AutoSaver.

        Returns:
            A path. It may or may not exist; that's not up to AutoSaver.
        """

        return self._path

    def doLoad(self) -> bool:
        """
        Load the settings from this AutoSaver's settings file path, if it
        exists.

        Unsaved settings, if any, will be lost.

        Returns:
            True if loading succeeded, else False. If an unexpected error
            occurred, the error will be logged using the logger passed during
            initialization. Note that it's not considered an error if the
            settings file path does not exist yet.

        Note:
            Prefer letting AutoSaver load the settings during its initialization
            in order to avoid race conditions.
        """

        try:
            if (path := self._path).exists():
                self._logger.debug("Loading settings file '%s'...", path)
                with Path(path).open(encoding=self._ENCODING) as f:
                    self._settings.load(f)
                self._logger.debug("Loaded.")
                return True
            self._logger.error("Path %s not found.", path)

        except OSError:
            self._logger.exception("Error while loading from '%s':", self._path)

        return False

    def doSave(self) -> bool:
        """
        Unconditionally saves the settings attached to this AutoSaver instance.

        This method uses a two-steps mechanism to perform the save, in order to
        make the save atomic. The settings are first saved to a temporary file,
        and if successful, that temporary file then replaces the actual settings
        file.

        If the directory where the settings file is located does not exist, this
        method automatically creates it.

        Returns:
            True if saving succeeded, else False. If False, the error will be
            logged using the logger passed during initialization.
        """

        self._save_timer.cancel()

        directory = self._path.parent
        directory.mkdir(parents=True, mode=self._DIR_MODE, exist_ok=True)

        try:
            with tempfile.NamedTemporaryFile(
                dir=directory,
                prefix=self._path.name,
                mode="xt",
                encoding=self._ENCODING,
                delete=False,
            ) as tmp:
                self._logger.debug("Saving settings file '%s'...", self._path)
                self._settings.save(tmp.file, blanklines=True)
                tmp_path = Path(tmp.name)
                tmp_path.chmod(self._FILE_MODE)
                tmp_path.rename(self._path)
                self._logger.debug("Saved.")

        except OSError:
            self._logger.exception("Error while saving to '%s':", self._path)
            return False

        self._dirty = False
        return True

    def saveIfNeeded(self) -> bool:
        """
        Performs a save if and only if there are pending, unsaved changes in the
        settings attached to this AutoSaver instance.

        Returns:
            True if a save was performed and succeeded, else False.
        """

        save_needed = self._dirty

        self._save_timer.cancel()

        if save_needed:
            return self.doSave()

        return save_needed

    def _onSettingsUpdated(self, _: Any) -> None:  # noqa: ANN401
        self._dirty = True
        if self._save_on_update:
            self._save_timer.start(self._save_delay)

    def setSaveTimerClass(self, timer_class: type[_TimerT]) -> _TimerT:
        """
        Internal.
        """

        timer = timer_class(self.saveIfNeeded)
        self._save_timer = timer
        return timer

    def __del__(self) -> None:
        if self._save_on_delete:
            self.saveIfNeeded()

    def __enter__(self) -> "AutoSaver":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.saveIfNeeded()
