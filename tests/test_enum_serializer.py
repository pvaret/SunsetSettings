import enum

from sunset.serializers import lookup


class ExampleEnum(enum.Enum):
    ONE = 1
    TWO = 2


class ExampleFlag(enum.Flag):
    A = enum.auto()
    B = enum.auto()
    C = enum.auto()
    D = A | B | C
    OTHER_A = A


class IntEnumExample(enum.IntEnum):
    ONE = 1
    TWO = 2


class IntFlagExample(enum.IntFlag):
    A = enum.auto()
    B = enum.auto()


class TestSerializableEnum:
    def test_simple_enum(self) -> None:
        serializer = lookup(ExampleEnum)
        assert serializer is not None

        assert serializer.toStr(ExampleEnum.ONE) == "ONE"

        assert serializer.fromStr("") is None
        assert serializer.fromStr("TWO") == ExampleEnum.TWO
        assert serializer.fromStr("INVALID") is None
        assert serializer.fromStr("ONE|TWO") is None

    def test_flag_enum_tostr(self) -> None:
        ab = ExampleFlag.A | ExampleFlag.B
        ba = ExampleFlag.B | ExampleFlag.A
        abc = ab | ExampleFlag.C

        serializer = lookup(ExampleFlag)
        assert serializer is not None

        assert serializer.toStr(ExampleFlag.A) == "A"
        assert serializer.toStr(ExampleFlag.OTHER_A) == "A"
        assert serializer.toStr(ab) == "A|B"
        assert serializer.toStr(ba) == "A|B"
        assert serializer.toStr(ExampleFlag.D) == "D"
        assert serializer.toStr(abc) == "D"

    def test_flag_enum_fromstr(self) -> None:
        ab = ExampleFlag.A | ExampleFlag.B

        serializer = lookup(ExampleFlag)
        assert serializer is not None

        assert serializer.fromStr("") is None
        assert serializer.fromStr("A") == ExampleFlag.A
        assert serializer.fromStr("D") == ExampleFlag.D
        assert serializer.fromStr("OTHER_A") == ExampleFlag.A
        assert serializer.fromStr("OTHER_A") == ExampleFlag.OTHER_A
        assert serializer.fromStr("A|B") == ab
        assert serializer.fromStr("B|A") == ab
        assert serializer.fromStr("A | B") == ab
        assert serializer.fromStr("A|B|C") == ExampleFlag.D
        assert serializer.fromStr("A|B|INVALID") == ab
        assert serializer.fromStr("A|INVALID") == ExampleFlag.A
        assert serializer.fromStr("INVALID|A") == ExampleFlag.A
        assert serializer.fromStr("INVALID") is None

    def test_int_enum(self) -> None:
        serializer = lookup(IntEnumExample)
        assert serializer is not None

        assert serializer.toStr(IntEnumExample.ONE) == "ONE"
        assert serializer.fromStr("TWO") == IntEnumExample.TWO

    def test_int_flag(self) -> None:
        serializer = lookup(IntFlagExample)
        assert serializer is not None

        assert serializer.toStr(IntFlagExample.A | IntFlagExample.B) == "A|B"
        assert serializer.fromStr("A|B") == IntFlagExample.A | IntFlagExample.B
