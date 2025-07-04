"SunsetSettings: a type-safe, extensible INI-style settings system with inheritance."

__project__ = "SunsetSettings"
__version__ = "0.7.1-dev"
__author__ = "P. Varet"
__copyright__ = "2022-2025, P. Varet"

import warnings

from sunset import exporter, serializers, sets, stringutils
from sunset.autoloader import AutoLoader
from sunset.autosaver import AutoSaver
from sunset.bunch import Bunch
from sunset.enum_serializer import SerializableEnum, SerializableFlag
from sunset.key import Key
from sunset.list import List
from sunset.protocols import Serializable, Serializer
from sunset.settings import Settings, normalize
from sunset.timer import PersistentTimer


class Bundle(Bunch):
    # Backward compatibility: Bunch used to be called Bundle prior to version 0.4.0.
    # Retain compatibility by keeping this name around for a few versions.
    def __init__(self) -> None:
        version_tuple = tuple(
            int(s) if s.isdigit() else 0 for s in __version__.split(".")
        )
        msg = "'Bundle' is deprecated. Use 'Bunch' instead."
        if version_tuple < (1, 0):
            warnings.warn(msg, DeprecationWarning, stacklevel=1)
        else:  # pragma: no cover
            raise DeprecationWarning(msg)
        super().__init__()


__all__ = [
    "AutoLoader",
    "AutoSaver",
    "Bunch",
    "Bundle",
    "Key",
    "List",
    "PersistentTimer",
    "Serializable",
    "SerializableEnum",
    "SerializableFlag",
    "Serializer",
    "Settings",
    "exporter",
    "normalize",
    "serializers",
    "sets",
    "stringutils",
]
