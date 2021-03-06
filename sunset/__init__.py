"SunsetSettings: a type-safe, extensible settings system with inheritance."

__version__ = "0.1"

from . import exporter, non_hashable_set, protocols, serializers

from .list import NewList, List
from .registry import CallbackRegistry
from .setting import NewSetting, Setting
from .settings import Settings, idify
from .section import NewSection, Section

__all__ = [
    "CallbackRegistry",
    "List",
    "NewList",
    "NewSection",
    "NewSetting",
    "Section",
    "Setting",
    "Settings",
    "exporter",
    "idify",
    "non_hashable_set",
    "protocols",
    "serializers",
]
