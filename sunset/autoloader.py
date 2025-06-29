from __future__ import annotations

import logging
from pathlib import Path
from typing import IO, TYPE_CHECKING, Protocol

from .timer import PersistentTimer

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable
    from types import TracebackType
    from typing import Any, Self

    from sunset import Settings


class LoadableProtocol(Protocol):
    """
    This protocol lets AutoLoader know how to use a Settings instance without
    having to import the actual Settings class.
    """

    def load(self, file: IO[str]) -> None: ...


class MonitorProtocol(Protocol):
    def __init__(
        self, path: Path, callback: Callable[[], Any], monitor_period_s: int = 1
    ) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def triggerCallback(self) -> None: ...


class MonitorForChange:
    """
    A simple file monitor that calls a callback function when the file changes.
    """

    _path: Path
    _callback: Callable[[], Any]
    _monitor_period_s: int
    _timer: PersistentTimer | None = None

    def __init__(
        self,
        path: Path,
        callback: Callable[[], Any],
        monitor_period_s: int = 1,
    ) -> None:
        self._path = path
        self._callback = callback
        self._monitor_period_s = monitor_period_s
        self._timer = None

    def start(self) -> None:
        if self._timer is not None:
            return

        try:
            last_modified = self._path.stat().st_mtime
            pending_update = False
        except OSError:
            last_modified = None
            pending_update = True

        def loop() -> None:
            nonlocal last_modified, pending_update
            try:
                new_last_modified = self._path.stat().st_mtime
            except OSError:
                last_modified = None
                pending_update = True
            else:
                if new_last_modified == last_modified:
                    if pending_update:
                        self.triggerCallback()
                        pending_update = False
                else:
                    pending_update = True
                last_modified = new_last_modified

        self._timer = PersistentTimer(looping=True)
        self._timer.start(self._monitor_period_s, loop)

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def triggerCallback(self) -> None:
        self._callback()


def doLoad(
    path: Path,
    settings: LoadableProtocol,
    *,
    raise_on_error: bool = False,
    logger: logging.Logger | None = None,
    encoding: str = "UTF-8",
) -> bool:
    logger = logger or logging.getLogger()

    # Deal gracefully with missing paths. That will be a common case when the file
    # has not been saved yet.
    if not path.exists():
        msg = f"Not loading settings -- path {path} does not exist."
        logger.info(msg)
        return False

    msg = f"Loading settings from {path}..."
    logger.debug(msg)

    try:
        with path.open(encoding=encoding) as f:
            settings.load(f)

    except OSError as e:
        msg = f"Failed to load settings from {path}: {e}"
        logger.error(msg)  # noqa: TRY400

        if raise_on_error:
            raise

        return False

    logger.debug("Loaded.")

    return True


class AutoLoader:
    """
    A helper that loads settings from the given file and reloads them when the file
    changes.

    On instantiation, it automatically loads settings from the given file path.

    Afterward, it periodically checks the file for changes and reloads the settings
    whenever the file is modified. Note that the settings are only reloaded when the
    file has not been modified for a few seconds, in order to avoid attempting to load a
    file that is still being written to.

    AutoLoader can also be used as a context manager. Using it as a context manager is
    the recommended usage.

    Args:
        settings: The Settings instance to load settings for.

        path: The full path to the file to load the settings from.

        raise_on_error: Whether OS errors occurring while loading the settings should
            raise an exception. If False, errors will only be logged. Default: False.

        logger: A logger instance that will be used to log OS errors, if any, while
            loading settings. If none is given, the default root logger will be used.

    Example:

    >>> from sunset import Settings, AutoLoader
    >>> class ExampleSettings(Settings):
    ...     ...
    >>> settings = ExampleSettings()
    >>> with AutoLoader(settings, "~/.config/my_app.conf"):  # doctest: +SKIP
    ...     main_program_loop(settings)

    """

    _ENCODING: str = "UTF-8"

    _settings: Settings
    _path: Path
    _raise_on_error: bool
    _logger: logging.Logger

    def __init__(
        self,
        settings: Settings,
        path: str | Path,
        *,
        raise_on_error: bool = False,
        logger: logging.Logger | None = None,
        _monitor_factory: Callable[[Any, Any], MonitorProtocol] = MonitorForChange,
    ) -> None:
        self._settings = settings
        self._path = Path(path).expanduser()
        self._raise_on_error = raise_on_error
        self._monitor = _monitor_factory(self._path, self.doLoad)
        self._logger = logger or logging.getLogger()

        self.doLoad()
        self._monitor.start()

    def doLoad(self) -> bool:
        """
        Perform a load now, without waiting for the next detected change in the settings
        file.

        Unsaved settings, if any, will be lost.

        OS errors occurring during the load, if any, will be logged to the logger
        provided to this AutoLoader's constructor.

        If this AutoLoader was constructed with the parameter `raise_on_error` set to
        True, these OS errors will then be re-raised.

        Note that a missing file is not considered an error.

        Returns:
            True if loading succeeded, else False.

        """
        return doLoad(
            self._path, self._settings, logger=self._logger, encoding=self._ENCODING
        )

    def path(self) -> Path:
        return self._path

    def __enter__(self) -> Self:
        self._monitor.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._monitor.stop()

    def __del__(self) -> None:
        self._monitor.stop()
