"SunsetSettings: a type-safe, extensible settings system with inheritance."

__project__ = "SunsetSettings"
__version__ = "0.3.1"
__author__ = "P. Varet"
__copyright__ = "2022, P. Varet"

from . import exporter, non_hashable_set, serializers

from .bundle import Bundle
from .key import Key
from .list import List
from .protocols import Serializable
from .registry import CallbackRegistry
from .settings import Settings, normalize

__all__ = [
    "Bundle",
    "CallbackRegistry",
    "Key",
    "List",
    "Serializable",
    "Settings",
    "exporter",
    "non_hashable_set",
    "normalize",
    "serializers",
]
