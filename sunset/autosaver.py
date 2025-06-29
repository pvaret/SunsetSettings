import logging
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import IO, Any, Protocol

from .autoloader import LoadableProtocol, doLoad
from .timer import PersistentTimer, TimerProtocol


class SavableProtocol(LoadableProtocol, Protocol):
    """
    This protocol lets AutoSaver know how to use a Settings instance without having to
    import the actual Settings class.
    """

    def save(self, file: IO[str], *, blanklines: bool = False) -> None: ...

    def onUpdateCall(self, callback: Callable[[Any], Any]) -> None: ...


class AutoSaver:
    """
    AutoSaver is a helper class that can take care of loading and saving settings
    automatically and safely.

    On instantiation, it automatically loads settings from the given file path, if that
    file exists, unless the `load_on_init` argument is set to False.

    When saving, it uses a two-steps mechanism to ensure the atomicity of the operation.
    That is to say, the operation either entirely succeeds or entirely fails; AutoSaver
    will never write an incomplete settings file.

    Saving automatically creates the parent directories of the target path if those
    don't exist yet.

    If the `save_on_update` argument is set to True, AutoSaver will save the settings
    whenever they are updated from inside the application. If the `save_on_delete`
    argument is set to True, AutoSaver will save the settings when its own instance is
    about to get deleted.

    AutoSaver can also be used as a context manager. Using it as a context manager is
    the recommended usage.

    Args:
        settings: The Settings instance to load to and save from.

        path: The full path to the file from which to load and save the settings. If
            this file does not exist yet, it will be created when saving for the first
            time.

        save_on_update: Whether to save the settings when they are updated in any way.
            Default: True.

        save_on_delete: Whether to save the settings when this AutoSaver instance is
            garbage collected. Default: True.

        load_on_init: Whether to load the settings when instantiating this AutoSaver,
            provided the settings path exists. Default: True.

        save_delay: How long to wait, in seconds, before actually saving the settings
            when `save_on_update` is True and an update occurs. Setting this to a few
            seconds will batch updates for that long before triggering a save. If set to
            0, the save is triggered immediately. Default: 0.

        raise_on_error: Whether OS errors occurring while loading and saving the
            settings should raise an exception. If False, errors will only be logged.
            Default: False.

        logger: A logger instance that will be used to log OS errors, if any, while
            loading or saving settings. If none is given, the default root logger will
            be used.

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
    _settings: SavableProtocol
    _dirty: bool
    _save_on_update: bool
    _save_on_delete: bool
    _save_delay: float
    _save_timer: TimerProtocol
    _raise_on_error: bool
    _logger: logging.Logger

    def __init__(  # noqa: PLR0913
        self,
        settings: SavableProtocol,
        path: Path | str,
        *,
        save_on_update: bool = True,
        save_on_delete: bool = True,
        load_on_init: bool = True,
        save_delay: float = 0.0,
        raise_on_error: bool = False,
        logger: logging.Logger | None = None,
    ) -> None:
        self._dirty = False
        self._path = Path(path).expanduser()
        self._save_on_update = save_on_update
        self._save_on_delete = save_on_delete
        self._save_delay = save_delay
        self._raise_on_error = raise_on_error
        self._save_timer = PersistentTimer()
        self._settings = settings
        self._settings.onUpdateCall(self._onSettingsUpdated)
        self._logger = logger or logging.getLogger()

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
        Load the settings from this AutoSaver's settings file path, if it exists.

        Unsaved settings, if any, will be lost.

        OS errors occurring while loading, if any, will be logged to the logger provided
        to this AutoLoader's constructor.

        If this AutoSaver was constructed with the parameter `raise_on_error` set to
        True, these OS errors will then be re-raised.

        Note that a missing file is not considered an error.

        Returns:
            True if loading succeeded, else False.

        Note:
            Prefer letting AutoSaver load the settings during its initialization in
            order to avoid race conditions.
        """

        return doLoad(
            self._path,
            self._settings,
            raise_on_error=self._raise_on_error,
            logger=self._logger,
            encoding=self._ENCODING,
        )

    def doSave(self) -> bool:
        """
        Unconditionally saves the settings attached to this AutoSaver instance.

        This method uses a two-steps mechanism to perform the save, in order to make the
        save atomic. The settings are first saved to a temporary file, and if
        successful, that temporary file then replaces the actual settings file.

        If the directory where the settings file is located does not exist, this method
        automatically creates it.

        OS errors occurring while saving, if any, will be logged to the logger provided
        to this AutoLoader's constructor.

        If this AutoSaver was constructed with the parameter `raise_on_error` set to
        True, these OS errors will then be re-raised.

        Returns:
            True if saving succeeded, else False.
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

        except OSError as e:
            msg = f"Failed to save settings to {self._path}: {e}"
            self._logger.error(msg)  # noqa: TRY400

            if self._raise_on_error:
                raise

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

        return self.doSave() if save_needed else False

    def _onSettingsUpdated(self, _: Any) -> None:  # noqa: ANN401
        self._dirty = True
        if self._save_on_update:
            self._save_timer.start(self._save_delay, self.saveIfNeeded)

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
