"SunsetSettings: a type-safe, extensible settings system with inheritance."

__project__ = "SunsetSettings"
__version__ = "0.6.1-dev"
__author__ = "P. Varet"
__copyright__ = "2022-2024, P. Varet"

from sunset import exporter, serializers, sets
from sunset.autosaver import AutoSaver
from sunset.bunch import Bunch
from sunset.enum_serializer import SerializableEnum, SerializableFlag
from sunset.key import Key
from sunset.list import List
from sunset.protocols import Serializable, Serializer
from sunset.settings import Settings, normalize
from sunset.timer import PersistentTimer

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
