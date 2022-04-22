from typing import Optional

import sunset


class ExampleSerializable:
    def __init__(self, value: str) -> None:

        self._value = value

    def toStr(self) -> str:

        return self._value

    @staticmethod
    def fromStr(value: str) -> Optional["ExampleSerializable"]:

        return ExampleSerializable(value)


def test_serialize_int():

    assert sunset.serializers.serialize(42) == "42"


def test_serialize_str():

    assert sunset.serializers.serialize(" !! test !!") == " !! test !!"


def test_serialize_bool():

    assert sunset.serializers.serialize(True) == "true"
    assert sunset.serializers.serialize(False) == "false"


def test_serialize_serializable():

    t = ExampleSerializable("serializable")
    assert sunset.serializers.serialize(t) == "serializable"


def test_deserialize_str():

    assert sunset.serializers.deserialize(str, "test") == "test"


def test_deserialize_int():

    assert sunset.serializers.deserialize(int, "test") is None
    assert sunset.serializers.deserialize(int, "   -32 ") == -32
    assert sunset.serializers.deserialize(int, "00017") == 17


def test_deserialize_bool():

    assert sunset.serializers.deserialize(bool, "YES")
    assert sunset.serializers.deserialize(bool, "  1 ")
    assert sunset.serializers.deserialize(bool, "true")

    assert not sunset.serializers.deserialize(bool, "NO")
    assert not sunset.serializers.deserialize(bool, "  0 ")
    assert not sunset.serializers.deserialize(bool, "false")

    assert sunset.serializers.deserialize(bool, "garbage") is None


def test_deserialize_serializable():

    t = sunset.serializers.deserialize(ExampleSerializable, "this is a test")
    assert t is not None
    assert isinstance(t, ExampleSerializable)
    assert t.toStr() == "this is a test"
