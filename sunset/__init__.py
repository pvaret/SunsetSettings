"SunsetSettings: a type-safe, extensible settings system with inheritance."

__project__ = "SunsetSettings"
__version__ = "0.6.1-dev"
__author__ = "P. Varet"
__copyright__ = "2022-2024, P. Varet"

from . import exporter, serializers, sets
from .autosaver import AutoSaver
from .bunch import Bunch
from .enum_serializer import (
    SerializableEnum,
    SerializableFlag,
)
from .key import Key
from .list import List
from .protocols import Serializable, Serializer
from .settings import Settings, normalize
from .timer import PersistentTimer

# Backward compatibility: Bunch used to be called Bundle prior to version 0.4.0.
# Retain compatibility by keeping this name around for a few versions.
Bundle = Bunch

__all__ = [
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
    "sets",
    "normalize",
    "serializers",
]
