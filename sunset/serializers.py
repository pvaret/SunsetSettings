from typing import Optional, Type, TypeVar, Union, cast

from .protocols import Serializable

AnySerializableType = Union[int, str, bool, float, Serializable]

SerializableT = TypeVar("SerializableT", bound=AnySerializableType)


def serialize(value: AnySerializableType) -> str:

    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, int) or isinstance(value, float):
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
            # The cast is unnecessary, but works around a mypy bug.
            return cast(SerializableT, _type(True))
        if string.strip().lower() in ("false", "no", "n", "0"):
            # The cast is unnecessary, but works around a mypy bug.
            return cast(SerializableT, _type(False))
        return None

    if issubclass(_type, int):
        try:
            # The cast is unnecessary, but works around a mypy bug.
            return cast(SerializableT, _type(int(string)))
        except ValueError:
            return None

    if issubclass(_type, float):
        try:
            # The cast is unnecessary, but works around a mypy bug.
            return cast(SerializableT, _type(float(string)))
        except ValueError:
            return None

    if issubclass(_type, str):
        # The cast is unnecessary, but works around a mypy bug.
        return cast(SerializableT, _type(string))

    assert issubclass(_type, Serializable)
    return _type.fromStr(string)
