import enum
from typing import Generic, TypeVar, cast

from sunset.enum_serializer import EnumSerializer
from sunset.protocols import Serializable, Serializer

_T = TypeVar("_T")
_Serializable = TypeVar("_Serializable", bound=Serializable)
_Castable = TypeVar("_Castable", int, float, str)


class StraightCastSerializer(Generic[_Castable]):
    _type: type[_Castable]

    def __init__(self, type_: type[_Castable]) -> None:
        self._type = type_

    def toStr(self, value: _Castable) -> str:
        return str(value)

    def fromStr(self, string: str) -> _Castable | None:
        try:
            return self._type(string)
        except ValueError:
            return None


class BoolSerializer:
    def toStr(self, value: bool) -> str:  # noqa: FBT001
        return "true" if value else "false"

    def fromStr(self, string: str) -> bool | None:
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

    def fromStr(self, string: str) -> _Serializable | None:
        return self._type.fromStr(string)


def lookup(type_: type[_T]) -> Serializer[_T] | None:
    # Note the cast on the return values. It's unfortunate, but works around a
    # mypy limitation where it fails to recognize our serializers as rightful
    # implementation of the generic Serializer protocol.

    if issubclass(type_, Serializable):
        return cast(Serializer[_T], SerializableSerializer(type_))

    if type_ is bool:
        return cast(Serializer[_T], BoolSerializer())

    if issubclass(type_, enum.Enum):
        return cast(Serializer[_T], EnumSerializer(type_))

    # Note: these need to come after the Enum case, because Enum can be a
    # subclass of these.

    if issubclass(type_, int) or issubclass(type_, float) or issubclass(type_, str):
        return cast(Serializer[_T], StraightCastSerializer(type_))

    return None
