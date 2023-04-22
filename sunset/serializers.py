import enum

from typing import Generic, Optional, TypeVar, Union, cast

from .enum_serializer import EnumSerializer
from .protocols import Serializable, Serializer

_T = TypeVar("_T")
_Serializable = TypeVar("_Serializable", bound=Serializable)
_Castable = TypeVar("_Castable", bound=Union[int, float, str])


class StraightCastSerializer(Generic[_Castable]):
    _type: type[_Castable]

    def __init__(self, type_: type[_Castable]) -> None:
        self._type = type_

    def toStr(self, value: _Castable) -> str:
        return str(value)

    def fromStr(self, string: str) -> Optional[_Castable]:
        try:
            return cast(_Castable, self._type(string))
        except ValueError:
            return None


class BoolSerializer:
    def toStr(self, value: bool) -> str:
        return "true" if value else "false"

    def fromStr(self, string: str) -> Optional[bool]:
        string = string.strip().lower()
        if string in ("true", "yes", "y", "1"):
            return True
        if string in ("false", "no", "n", "0"):
            return False
        return None


class SerializableSerializer(Generic[_Serializable]):
    _type: type[_Serializable]

    def __init__(self, type_: type[_Serializable]) -> None:
        self._type = type_

    def toStr(self, value: _Serializable) -> str:
        return value.toStr()

    def fromStr(self, string: str) -> Optional[_Serializable]:
        return self._type.fromStr(string)


def lookup(type_: type[_T]) -> Optional[Serializer[_T]]:
    # Note the cast on the return values. It's unfortunate, but works around a
    # mypy limitation where it fails to recognize our serializers as rightful
    # implementation of the generic Serializer protocol.

    if issubclass(type_, Serializable):
        return cast(Serializer[_T], SerializableSerializer(type_))

    if type_ is bool:
        return cast(Serializer[_T], BoolSerializer())

    if type_ is int or type_ is float or type_ is str:
        return cast(Serializer[_T], StraightCastSerializer(type_))

    if issubclass(type_, enum.Enum):
        return cast(Serializer[_T], EnumSerializer(type_))

    return None
