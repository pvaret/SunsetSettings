from typing import Any, Type, TypeVar

from .protocols import Serializable

SerializableT = TypeVar("SerializableT", int, str, bool, Serializable[Any])


def serialize(value: SerializableT) -> str:

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
) -> tuple[bool, SerializableT]:

    if issubclass(_type, bool):
        if string.strip().lower() in ("true", "yes", "y", "1"):
            return True, _type(True)
        if string.strip().lower() in ("false", "no", "n", "0"):
            return True, _type(False)
        return False, _type(False)

    if issubclass(_type, int):
        try:
            return True, _type(int(string))
        except ValueError:
            return False, _type(0)

    if issubclass(_type, str):
        return True, _type(string)

    assert issubclass(_type, Serializable)
    return _type.fromStr(string)
