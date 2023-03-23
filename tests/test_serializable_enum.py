import enum

from sunset import SerializableEnum, SerializableFlag


class ExampleEnum(SerializableEnum):
    ONE = 1
    TWO = 2


class ExampleFlag(SerializableFlag):
    A = enum.auto()
    B = enum.auto()
    C = enum.auto()
    D = A | B | C
    OTHER_A = A


class TestSerializableEnum:
    def test_simple_enum(self) -> None:
        assert ExampleEnum.ONE.toStr() == "ONE"

        assert ExampleEnum.fromStr("") is None
        assert ExampleEnum.fromStr("TWO") == ExampleEnum.TWO
        assert ExampleEnum.fromStr("INVALID") is None
        assert ExampleEnum.fromStr("ONE|TWO") is None

    def test_flag_enum_tostr(self) -> None:
        ab = ExampleFlag.A | ExampleFlag.B
        ba = ExampleFlag.B | ExampleFlag.A
        abc = ab | ExampleFlag.C

        assert ExampleFlag.A.toStr() == "A"
        assert ExampleFlag.OTHER_A.toStr() == "A"
        assert ab.toStr() == "A|B"
        assert ba.toStr() == "A|B"
        assert ExampleFlag.D.toStr() == "D"
        assert abc.toStr() == "D"

    def test_flag_enum_fromstr(self) -> None:
        ab = ExampleFlag.A | ExampleFlag.B

        assert ExampleFlag.fromStr("") is None
        assert ExampleFlag.fromStr("A") == ExampleFlag.A
        assert ExampleFlag.fromStr("D") == ExampleFlag.D
        assert ExampleFlag.fromStr("OTHER_A") == ExampleFlag.A
        assert ExampleFlag.fromStr("OTHER_A") == ExampleFlag.OTHER_A
        assert ExampleFlag.fromStr("A|B") == ab
        assert ExampleFlag.fromStr("B|A") == ab
        assert ExampleFlag.fromStr("A | B") == ab
        assert ExampleFlag.fromStr("A|B|C") == ExampleFlag.D
        assert ExampleFlag.fromStr("A|B|INVALID") == ab
        assert ExampleFlag.fromStr("A|INVALID") == ExampleFlag.A
        assert ExampleFlag.fromStr("INVALID|A") == ExampleFlag.A
        assert ExampleFlag.fromStr("INVALID") is None
