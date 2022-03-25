import sunset


class ExampleSerializable:
    def __init__(self, value: str) -> None:

        self._value = value

    def toStr(self) -> str:

        return self._value

    @staticmethod
    def fromStr(value: str) -> "tuple[bool, ExampleSerializable]":

        return True, ExampleSerializable(value)


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

    assert sunset.serializers.deserialize(str, "test") == (True, "test")


def test_deserialize_int():

    assert sunset.serializers.deserialize(int, "test") == (False, 0)
    assert sunset.serializers.deserialize(int, "   -32 ") == (True, -32)
    assert sunset.serializers.deserialize(int, "00017") == (True, 17)


def test_deserialize_bool():

    assert sunset.serializers.deserialize(bool, "YES") == (True, True)
    assert sunset.serializers.deserialize(bool, "  1 ") == (True, True)
    assert sunset.serializers.deserialize(bool, "true") == (True, True)

    assert sunset.serializers.deserialize(bool, "NO") == (True, False)
    assert sunset.serializers.deserialize(bool, "  0 ") == (True, False)
    assert sunset.serializers.deserialize(bool, "false") == (True, False)

    assert sunset.serializers.deserialize(bool, "garbage") == (False, False)


def test_deserialize_serializable():

    success, t = sunset.serializers.deserialize(
        ExampleSerializable, "this is a test"
    )
    assert success
    assert isinstance(t, ExampleSerializable)
    assert t.toStr() == "this is a test"
