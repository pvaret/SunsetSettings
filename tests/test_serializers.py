from typing import Optional

from sunset import serializers


class ExampleSerializable:
    def __init__(self, value: str) -> None:
        self._value = value

    def toStr(self) -> str:
        return self._value

    @staticmethod
    def fromStr(string: str) -> Optional["ExampleSerializable"]:
        return ExampleSerializable(string)


def test_serialize_int() -> None:
    serializer = serializers.lookup(int)
    assert serializer is not None
    assert serializer.toStr(42) == "42"


def test_serialize_str() -> None:
    serializer = serializers.lookup(str)
    assert serializer is not None
    assert serializer.toStr(" !! test !!") == " !! test !!"


def test_serialize_bool() -> None:
    serializer = serializers.lookup(bool)
    assert serializer is not None
    assert serializer.toStr(True) == "true"
    assert serializer.toStr(False) == "false"


def test_serialize_float() -> None:
    serializer = serializers.lookup(float)
    assert serializer is not None
    assert serializer.toStr(1.0) == "1.0"
    assert serializer.toStr(2.34e-56) == "2.34e-56"


def test_serialize_serializable() -> None:
    t = ExampleSerializable("serializable")
    serializer = serializers.lookup(type(t))
    assert serializer is not None
    assert serializer.toStr(t) == "serializable"


def test_deserialize_str() -> None:
    serializer = serializers.lookup(str)
    assert serializer is not None
    assert serializer.fromStr("test") == "test"


def test_deserialize_int() -> None:
    serializer = serializers.lookup(int)
    assert serializer is not None
    assert serializer.fromStr("test") is None
    assert serializer.fromStr("   -32 ") == -32
    assert serializer.fromStr("00017") == 17


def test_deserialize_float() -> None:
    serializer = serializers.lookup(float)
    assert serializer is not None
    assert serializer.fromStr("test") is None
    assert serializer.fromStr("   -32.10 ") == -32.1
    assert serializer.fromStr("2.34e-56") == 2.34e-56


def test_deserialize_bool() -> None:
    serializer = serializers.lookup(bool)
    assert serializer is not None
    assert serializer.fromStr("YES")
    assert serializer.fromStr("  1 ")
    assert serializer.fromStr("true")

    assert not serializer.fromStr("NO")
    assert not serializer.fromStr("  0 ")
    assert not serializer.fromStr("false")

    assert serializer.fromStr("garbage") is None


def test_deserialize_serializable() -> None:
    serializer = serializers.lookup(ExampleSerializable)
    assert serializer is not None
    t = serializer.fromStr("this is a test")
    assert t is not None
    assert isinstance(t, ExampleSerializable)
    assert t.toStr() == "this is a test"


def test_serializer_not_found() -> None:
    assert serializers.lookup(object) is None
