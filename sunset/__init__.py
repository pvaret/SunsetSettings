"SunsetSettings: a type-safe, extensible settings system with inheritance."

__project__ = "SunsetSettings"
__version__ = "0.2-dev"
__author__ = "P. Varet"
__copyright__ = "2022, P. Varet"

from . import exporter, non_hashable_set, protocols, serializers

from .list import NewSectionList, NewSettingList, List
from .registry import CallbackRegistry
from .setting import NewSetting, Setting
from .settings import Settings, normalize
from .section import NewSection, Section

__all__ = [
    "CallbackRegistry",
    "List",
    "NewSection",
    "NewSectionList",
    "NewSetting",
    "NewSettingList",
    "Section",
    "Setting",
    "Settings",
    "exporter",
    "non_hashable_set",
    "normalize",
    "protocols",
    "serializers",
]
