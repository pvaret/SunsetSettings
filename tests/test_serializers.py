from typing import Optional

from sunset import serializers


class ExampleSerializable:
    def __init__(self, value: str) -> None:
        self._value = value

    def toStr(self) -> str:
        return self._value

    @staticmethod
    def fromStr(value: str) -> Optional["ExampleSerializable"]:
        return ExampleSerializable(value)


def test_serialize_int() -> None:
    assert serializers.serialize(42) == "42"


def test_serialize_str() -> None:
    assert serializers.serialize(" !! test !!") == " !! test !!"


def test_serialize_bool() -> None:
    assert serializers.serialize(True) == "true"
    assert serializers.serialize(False) == "false"


def test_serialize_float() -> None:
    assert serializers.serialize(1.0) == "1.0"
    assert serializers.serialize(2.34e-56) == "2.34e-56"


def test_serialize_serializable() -> None:
    t = ExampleSerializable("serializable")
    assert serializers.serialize(t) == "serializable"


def test_deserialize_str() -> None:
    assert serializers.deserialize(str, "test") == "test"


def test_deserialize_int() -> None:
    assert serializers.deserialize(int, "test") is None
    assert serializers.deserialize(int, "   -32 ") == -32
    assert serializers.deserialize(int, "00017") == 17


def test_deserialize_float() -> None:
    assert serializers.deserialize(float, "test") is None
    assert serializers.deserialize(float, "   -32.10 ") == -32.1
    assert serializers.deserialize(float, "2.34e-56") == 2.34e-56


def test_deserialize_bool() -> None:
    assert serializers.deserialize(bool, "YES")
    assert serializers.deserialize(bool, "  1 ")
    assert serializers.deserialize(bool, "true")

    assert not serializers.deserialize(bool, "NO")
    assert not serializers.deserialize(bool, "  0 ")
    assert not serializers.deserialize(bool, "false")

    assert serializers.deserialize(bool, "garbage") is None


def test_deserialize_serializable() -> None:
    t = serializers.deserialize(ExampleSerializable, "this is a test")
    assert t is not None
    assert isinstance(t, ExampleSerializable)
    assert t.toStr() == "this is a test"
