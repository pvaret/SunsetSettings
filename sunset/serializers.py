import enum
from typing import Generic, Protocol, TypeVar, cast

from sunset.enum_serializer import EnumSerializer
from sunset.protocols import Serializable, Serializer

_T = TypeVar("_T")
_Serializable = TypeVar("_Serializable", bound=Serializable)
_Bool = TypeVar("_Bool", bound=bool)


class _Castable(Protocol):
    def __init__(self, obj: str) -> None: ...


_CastableT = TypeVar("_CastableT", bound=_Castable)


class StraightCastSerializer(Generic[_CastableT]):
    _type: type[_CastableT]

    def __init__(self, type_: type[_CastableT]) -> None:
        self._type = type_

    def toStr(self, value: _CastableT) -> str:
        return str(value)

    def fromStr(self, string: str) -> _CastableT | None:
        try:
            return self._type(string)
        except ValueError:
            return None


class BoolSerializer(Generic[_Bool]):
    def __init__(self, type_: type[_Bool]) -> None:
        self._type = type_

    def toStr(self, value: _Bool) -> str:
        return "true" if value else "false"

    def fromStr(self, string: str) -> _Bool | None:
        string = string.strip().lower()
        if string in ("true", "yes", "y", "1"):
            return self._type(True)  # noqa: FBT003
        if string in ("false", "no", "n", "0"):
            return self._type(False)  # noqa: FBT003
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
    if issubclass(type_, Serializable):
        return cast(Serializer[_T], SerializableSerializer(type_))

    if issubclass(type_, bool):
        return cast(Serializer[_T], BoolSerializer(type_))

    if issubclass(type_, enum.Enum):
        return cast(Serializer[_T], EnumSerializer(type_))

    # Note: these need to come after the Enum case, because Enum can be a
    # subclass of these.

    if issubclass(type_, int) or issubclass(type_, float) or issubclass(type_, str):
        return StraightCastSerializer(type_)

    return None
