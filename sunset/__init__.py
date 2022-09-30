"SunsetSettings: a type-safe, extensible settings system with inheritance."

__project__ = "SunsetSettings"
__version__ = "0.2-dev"
__author__ = "P. Varet"
__copyright__ = "2022, P. Varet"

from . import exporter, non_hashable_set, protocols, serializers

from .key import Key
from .list import List
from .registry import CallbackRegistry
from .section import Section
from .settings import Settings, normalize

__all__ = [
    "CallbackRegistry",
    "Key",
    "List",
    "Section",
    "Settings",
    "exporter",
    "non_hashable_set",
    "normalize",
    "protocols",
    "serializers",
]
