from typing import Any, Optional, Type, TypeVar, Union, cast

from .protocols import Serializable

_AnySerializableType = Union[int, str, bool, float, Serializable]

AnySerializableType = TypeVar("AnySerializableType", bound=_AnySerializableType)


def serialize(value: _AnySerializableType) -> str:

    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, int) or isinstance(value, float):
        return str(value)
    elif isinstance(value, str):
        return value
    elif isinstance(cast(Any, value), Serializable):

        # Note the cast above. It's just so that linters don't complain that
        # we're using an isinstance() check when that's the only type the value
        # can possibly be, from the typechecker's point of view. But the
        # TypeError below is explicitly about catching this kind of user error.
        # So we do in fact want this isinstance() check.

        return value.toStr()

    else:
        raise TypeError(
            f"'{repr(value)}' is of type '{value.__class__.__name__}', which is"
            " not serializable"
        )


def deserialize(
    _type: Type[AnySerializableType], string: str
) -> Optional[AnySerializableType]:

    if issubclass(_type, bool):
        if string.strip().lower() in ("true", "yes", "y", "1"):
            # The cast is unnecessary, but works around a mypy bug.
            return cast(AnySerializableType, _type(True))
        if string.strip().lower() in ("false", "no", "n", "0"):
            # The cast is unnecessary, but works around a mypy bug.
            return cast(AnySerializableType, _type(False))
        return None

    if issubclass(_type, int):
        try:
            # The cast is unnecessary, but works around a mypy bug.
            return cast(AnySerializableType, _type(int(string)))
        except ValueError:
            return None

    if issubclass(_type, float):
        try:
            # The cast is unnecessary, but works around a mypy bug.
            return cast(AnySerializableType, _type(float(string)))
        except ValueError:
            return None

    if issubclass(_type, str):
        # The cast is unnecessary, but works around a mypy bug.
        return cast(AnySerializableType, _type(string))

    assert issubclass(_type, Serializable)

    # The cast is unnecessary, but works around a mypy bug.
    return cast(AnySerializableType, _type.fromStr(string))
