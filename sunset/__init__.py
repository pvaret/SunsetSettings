"SunsetSettings: a type-safe, extensible settings system with inheritance."

__project__ = "SunsetSettings"
__version__ = "0.4.0"
__author__ = "P. Varet"
__copyright__ = "2022-2023, P. Varet"

from . import exporter, non_hashable_set, serializers

from .autosaver import AutoSaver
from .bunch import Bunch
from .key import Key
from .list import List
from .protocols import Serializable
from .registry import CallbackRegistry
from .serializable_enum import (
    SerializableEnum,
    SerializableFlag,
)
from .settings import Settings, normalize
from .timer import PersistentTimer

# Backward compatibility: Bunch used to be called Bundle. Retain compatibility
# by keeping this name around for a few versions.
Bundle = Bunch

__all__ = [
    "AutoSaver",
    "Bunch",
    "Bundle",
    "CallbackRegistry",
    "Key",
    "List",
    "PersistentTimer",
    "Serializable",
    "SerializableEnum",
    "SerializableFlag",
    "Settings",
    "exporter",
    "non_hashable_set",
    "normalize",
    "serializers",
]
