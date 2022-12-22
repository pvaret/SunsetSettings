"SunsetSettings: a type-safe, extensible settings system with inheritance."

__project__ = "SunsetSettings"
__version__ = "0.3.2"
__author__ = "P. Varet"
__copyright__ = "2022, P. Varet"

from . import exporter, non_hashable_set, serializers

from .autosaver import AutoSaver
from .bundle import Bundle
from .key import Key
from .list import List
from .protocols import Serializable
from .registry import CallbackRegistry
from .settings import Settings, normalize
from .timer import PersistentTimer

__all__ = [
    "AutoSaver",
    "Bundle",
    "CallbackRegistry",
    "Key",
    "List",
    "PersistentTimer",
    "Serializable",
    "Settings",
    "exporter",
    "non_hashable_set",
    "normalize",
    "serializers",
]
