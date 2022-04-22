from typing import Optional, Type, TypeVar, Union

from .protocols import Serializable

AnySerializableType = Union[int, str, bool, Serializable]

SerializableT = TypeVar("SerializableT", bound=AnySerializableType)


def serialize(value: AnySerializableType) -> str:

    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        return value
    else:
        assert isinstance(value, Serializable)
        return value.toStr()


def deserialize(
    _type: Type[SerializableT], string: str
) -> Optional[SerializableT]:

    if issubclass(_type, bool):
        if string.strip().lower() in ("true", "yes", "y", "1"):
            return _type(True)
        if string.strip().lower() in ("false", "no", "n", "0"):
            return _type(False)
        return None

    if issubclass(_type, int):
        try:
            return _type(int(string))
        except ValueError:
            return None

    if issubclass(_type, str):
        return _type(string)

    assert issubclass(_type, Serializable)
    return _type.fromStr(string)
