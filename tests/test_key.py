from typing import Optional

import pytest

from pytest_mock import MockerFixture

from sunset import Bunch, Key, protocols, SerializableEnum, SerializableFlag


class ExampleSerializable:
    def __init__(self, value: str) -> None:
        self._value = value

    def toStr(self) -> str:
        return self._value

    @staticmethod
    def fromStr(string: str) -> Optional["ExampleSerializable"]:
        return ExampleSerializable(string)


class ExampleEnum(SerializableEnum):
    ONE = 1
    TWO = 2


class ExampleFlag(SerializableFlag):
    ONE = 1
    TWO = 2
    THREE = ONE | TWO


class TestKey:
    def test_protocol_implementation(self) -> None:
        key = Key(default="")
        assert isinstance(key, protocols.Field)

    def test_default(self) -> None:
        assert Key(default="default").get() == "default"
        assert Key(default=0).get() == 0
        assert type(Key(default=False).get()) is bool
        assert not Key(default=False).get()
        assert Key(default=12.345e-67).get() == 12.345e-67
        assert Key(default=ExampleEnum.ONE).get() == ExampleEnum.ONE
        assert (
            Key(default=ExampleFlag.ONE | ExampleFlag.TWO).get()
            == ExampleFlag.THREE
        )
        with pytest.raises(TypeError):
            Key(default=object())  # type: ignore # It's the point!

    def test_set(self) -> None:
        key = Key(default="test")
        key.set("other")
        assert key.get() == "other"

    def test_clear(self) -> None:
        key = Key(default="default")
        key.set("other")
        assert key.get() != "default"

        key.clear()
        assert key.get() == "default"

    def test_serializable_type(self) -> None:
        value = ExampleSerializable.fromStr("dummy")
        assert value is not None
        key: Key[ExampleSerializable] = Key(default=value)

        assert key.get().toStr() == "dummy"

    def test_missing_serializer(self) -> None:
        class NotSerializable:
            pass

        with pytest.raises(TypeError):
            Key(default=NotSerializable())

    def test_explicit_serializer(self) -> None:
        class NotSerializable:
            pass

        class Serializer:
            def toStr(self, value: NotSerializable) -> str:
                return "test"

            def fromStr(self, string: str) -> NotSerializable:
                return NotSerializable()

        key = Key(default=NotSerializable(), serializer=Serializer())
        key.set(NotSerializable())
        assert list(key.dumpFields()) == [("", "test")]

    def test_serializer_override(self) -> None:
        class Serializer:
            def toStr(self, value: str) -> str:
                return value + "-TEST"

            def fromStr(self, string: str) -> Optional[str]:
                if string.endswith("-TEST"):
                    return string[:-5]
                return None

        key = Key(default="", serializer=Serializer())
        key.set("value")
        assert list(key.dumpFields()) == [("", "value-TEST")]

        key.restoreField("", "other value-TEST")
        assert key.get() == "other value"

    def test_validator(self) -> None:
        def isEven(i: int) -> bool:
            return i % 2 == 0

        key: Key[int] = Key(default=0, validator=isEven)

        assert not key.set(1)
        assert key.get() == 0

        assert key.set(2)
        assert key.get() == 2

        assert not key.restoreField("", "3")
        assert key.get() == 2

        assert key.restoreField("", "4")
        assert key.get() == 4

        def isOdd(i: int) -> bool:
            return i % 2 == 1

        key.setValidator(isOdd)

        assert key.set(5)
        assert key.get() == 5

        assert not key.set(6)
        assert key.get() == 5

    def test_value_change_callback(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        key = Key(default="default")

        key.onValueChangeCall(callback)

        key.set("default")
        callback.assert_not_called()
        callback.reset_mock()

        key.set("not default")
        callback.assert_called_once_with("not default")
        callback.reset_mock()

        key.clear()
        callback.assert_called_once_with("default")
        callback.reset_mock()

        key.clear()
        callback.assert_not_called()

    def test_value_change_callback_inheritance(
        self, mocker: MockerFixture
    ) -> None:
        callback_sub_child1 = mocker.stub()
        callback_sub_child2 = mocker.stub()

        # Set up keys so that one parent key has two children key, each with one
        # child of its own.

        parent_key = Key(default="default")
        child1_key = Key(default="default")
        child2_key = Key(default="default")
        sub_child1_key = Key(default="default")
        sub_child2_key = Key(default="default")

        child1_key.setParent(parent_key)
        child2_key.setParent(parent_key)
        sub_child1_key.setParent(child1_key)
        sub_child2_key.setParent(child2_key)

        # Set up callbacks on the grandchildren keys.

        sub_child1_key.onValueChangeCall(callback_sub_child1)
        sub_child2_key.onValueChangeCall(callback_sub_child2)

        # One of the first generation children gets a value set on it. That
        # should count as set even if the value is the same as the default value
        # of the parent! But the sub-child's apparent value does not change, so
        # its callback shouldn't be called.

        child1_key.set("default")
        callback_sub_child1.assert_not_called()

        # If the toplevel parent's value changes to something new, the apparent
        # value change should be propagated down the inheritance chain through
        # all *unset* children. So only the second one in this case.

        parent_key.set("test")
        callback_sub_child1.assert_not_called()
        callback_sub_child2.assert_called_once_with("test")
        callback_sub_child2.reset_mock()

        # Updating the intermediate child should update the value of its own
        # child.

        child1_key.set("test")
        callback_sub_child1.assert_called_once_with("test")
        callback_sub_child1.reset_mock()

        # Clearing it causes its child to now inherit the value from the
        # toplevel parent, but that value is the same; so the child's value is
        # not updated.

        child1_key.clear()
        callback_sub_child1.assert_not_called()
        callback_sub_child1.reset_mock()

        # Clearing the parent does change the value inherited by the grandchild.

        parent_key.clear()
        callback_sub_child1.assert_called_once_with("default")
        callback_sub_child1.reset_mock()

    def test_key_updated_callback(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        key = Key(default="default")
        assert isinstance(key, protocols.UpdateNotifier)

        key.onUpdateCall(callback)

        key.set("default")
        callback.assert_called_once_with(key)
        callback.reset_mock()

        key.set("not default")
        callback.assert_called_once_with(key)
        callback.reset_mock()

        key.set("not default")
        callback.assert_not_called()
        callback.reset_mock()

        key.clear()
        callback.assert_called_once_with(key)
        callback.reset_mock()

        key.clear()
        callback.assert_not_called()
        callback.reset_mock()

    def test_callback_type_is_flexible(self) -> None:
        key = Key("")

        class Dummy:
            pass

        def callback1(_: Key[str]) -> Dummy:
            return Dummy()

        def callback2(_: str) -> Dummy:
            return Dummy()

        key.onUpdateCall(callback1)
        key.onValueChangeCall(callback2)

    def test_updater(self) -> None:
        key = Key("")

        def updater(value: str) -> str:
            return value + "x"

        assert key.get() == ""
        key.updateValue(updater)
        assert key.get() == "x"
        key.updateValue(updater)
        assert key.get() == "xx"

    def test_inheritance(self) -> None:
        parent_key = Key(default="default a")
        child_key = Key(default="")

        assert child_key not in parent_key.children()
        child_key.setParent(parent_key)
        assert child_key in parent_key.children()

        assert child_key.get() == "default a"

        parent_key.set("new a")
        assert child_key.get() == "new a"

        child_key.set("new b")
        assert child_key.get() == "new b"

        parent_key.clear()
        assert child_key.get() == "new b"

        child_key.clear()
        assert child_key.get() == "default a"

    def test_inherit_wrong_type(self) -> None:
        parent_key = Key(default="str")
        child_key = Key(default=0)

        # Ignore the type error, as it's the whole point of the test.

        child_key.setParent(parent_key)  # type: ignore

        assert child_key.parent() is None

    def test_inherit_revert(self) -> None:
        parent_key = Key(default="default a")
        child_key = Key(default="default b")

        assert child_key not in parent_key.children()
        assert child_key.parent() is None

        child_key.setParent(parent_key)

        assert child_key in parent_key.children()
        assert child_key.parent() is parent_key

        child_key.setParent(None)

        assert child_key not in parent_key.children()
        assert child_key.parent() is None

    def test_repr(self) -> None:
        key1 = Key(default="test")
        key2 = Key(default=12)
        key3 = Key(default="  test\ntest  ")

        assert repr(key1) == "<Key[str]:(test)>"
        assert repr(key2) == "<Key[int]:(12)>"
        assert repr(key3) == '<Key[str]:("  test\\ntest  ")>'

        key1.set("test")
        key2.set(12)
        key3.set("  test\ntest  ")

        assert repr(key1) == "<Key[str]:test>"
        assert repr(key2) == "<Key[int]:12>"
        assert repr(key3) == '<Key[str]:"  test\\ntest  ">'

    def test_reparenting(self) -> None:
        key1 = Key(default="default a")
        key2 = Key(default="default b")
        child_key = Key(default="default c")

        assert child_key not in key1.children()
        assert child_key not in key2.children()

        child_key.setParent(key1)
        assert child_key in key1.children()
        assert child_key not in key2.children()

        child_key.setParent(key2)
        assert child_key not in key1.children()
        assert child_key in key2.children()

        child_key.setParent(None)
        assert child_key not in key1.children()
        assert child_key not in key2.children()

    def test_callback_triggered_on_parent_value_change(
        self, mocker: MockerFixture
    ) -> None:
        stub = mocker.stub()

        parent_key = Key(default="default a")
        child_key = Key(default="default b")
        child_key.setParent(parent_key)

        child_key.onValueChangeCall(stub)

        child_key.set("test 1")
        stub.assert_called_once_with("test 1")
        stub.reset_mock()

        child_key.clear()
        stub.assert_called_once_with("default a")
        stub.reset_mock()

        parent_key.set("test 2")
        stub.assert_called_once_with("test 2")
        stub.reset_mock()

        parent_key.clear()
        stub.assert_called_once_with("default a")

    def test_field_label(self) -> None:
        class TestBunch(Bunch):
            key1 = Key("test")
            key2 = Key("test")

        bunch = TestBunch()
        assert bunch.key1.fieldLabel() == "key1"
        assert bunch.key2.fieldLabel() == "key2"

        key = Key("test")
        assert key.fieldLabel() == ""

    def test_field_path(self) -> None:
        assert Key("").fieldPath() == ""

        class TestBunch(Bunch):
            key1 = Key("test")
            key2 = Key("test")

        bunch = TestBunch()
        assert bunch.key1.fieldPath() == ".key1"
        assert bunch.key2.fieldPath() == ".key2"

    def test_dump_fields(self) -> None:
        # An unattached Key should get dumped. It just doesn't have a label.

        key = Key("")
        assert list(key.dumpFields()) == []
        key.set("test")
        assert list(key.dumpFields()) == [("", "test")]

        class TestBunch(Bunch):
            str_key = Key(default="")
            serializable_key = Key(default=ExampleSerializable("empty"))
            _private = Key(default=0)

        bunch = TestBunch()

        # A public Key should get dumped.

        assert list(bunch.str_key.dumpFields()) == []
        bunch.str_key.set("test")
        assert list(bunch.str_key.dumpFields()) == [(".str_key", "test")]

        # A Key's value should be serialized in its dump.

        assert list(bunch.serializable_key.dumpFields()) == []
        bunch.serializable_key.set(ExampleSerializable("not empty"))
        assert list(bunch.serializable_key.dumpFields()) == [
            (".serializable_key", "not empty")
        ]

        # A Key with a private label should not get dumped.

        assert list(bunch._private.dumpFields()) == []  # type: ignore
        bunch._private.set(111)  # type: ignore
        assert list(bunch._private.dumpFields()) == []  # type: ignore

    def test_restore_field(self, mocker: MockerFixture) -> None:
        key: Key[int] = Key(0)
        callback = mocker.stub()
        key.onUpdateCall(callback)

        # The value should be set if the given label matches that of the Key. In
        # this case, "". In all other cases the value should not be set. As
        # well, restoring a field should not trigger a callback.

        assert not key.isSet()
        assert key.restoreField("", "1")
        assert key.isSet()
        assert key.get() == 1
        callback.assert_not_called()

        key.clear()
        callback.reset_mock()
        assert not key.restoreField("invalid", "1")
        assert not key.isSet()
        callback.assert_not_called()
        assert not key.restoreField(".invalid", "1")
        assert not key.isSet()
        callback.assert_not_called()
        assert not key.restoreField("invalid.", "1")
        assert not key.isSet()
        callback.assert_not_called()
        assert not key.restoreField(".", "1")
        assert not key.isSet()
        callback.assert_not_called()

        # If multiple values are set, the last one sticks.

        key.clear()
        callback.reset_mock()
        assert key.restoreField("", "1")
        assert key.restoreField("", "2")
        assert key.get() == 2
        callback.assert_not_called()

        # Invalid values do not update the Key.

        key.clear()
        callback.reset_mock()
        assert not key.restoreField("", "?")
        assert not key.isSet()
        callback.assert_not_called()
        assert not key.restoreField("", "")
        assert not key.isSet()
        callback.assert_not_called()
        assert key.restoreField("", None)
        assert not key.isSet()
        callback.assert_not_called()

        class TestBunch(Bunch):
            str_key = Key("")

        # Same as the above when the Key has a non-empty label.

        bunch = TestBunch()
        assert not bunch.str_key.restoreField("", "test")
        assert not bunch.str_key.isSet()
        assert not bunch.str_key.restoreField("test", "test")
        assert not bunch.str_key.isSet()
        assert not bunch.str_key.restoreField(".str_key", "test")
        assert not bunch.str_key.isSet()
        assert not bunch.str_key.restoreField("str_key.", "test")
        assert not bunch.str_key.isSet()

        assert bunch.str_key.restoreField("str_key", "test")
        assert bunch.str_key.isSet()
        assert bunch.str_key.get() == "test"

    def test_restore_field_serialization(self) -> None:
        key_str: Key[str] = Key(default="")
        assert key_str.restoreField("", "test")
        assert key_str.get() == "test"

        key_int: Key[int] = Key(default=0)
        assert key_int.restoreField("", "12")
        assert key_int.get() == 12

        key_float: Key[float] = Key(default=1.2)
        assert key_float.restoreField("", "3.4")
        assert key_float.get() == 3.4

        key_bool: Key[bool] = Key(default=False)
        assert key_bool.restoreField("", "true")
        assert key_bool.get()

        key_custom: Key[ExampleSerializable] = Key(
            default=ExampleSerializable("")
        )
        assert key_custom.restoreField("", "test")
        assert key_custom.get().toStr() == "test"

    def test_invalid_restore_value_is_still_dumped(self) -> None:
        key = Key[int](default=0)

        assert not key.restoreField("", "12error")
        assert key.get() == 0

        assert list(key.dumpFields()) == [("", "12error")]

        # Clearing or setting the Key also clears the bad value.

        key.clear()
        assert list(key.dumpFields()) == []

        assert not key.restoreField("", "12error")
        key.set(0)
        assert list(key.dumpFields()) == [("", "0")]

    def test_persistence(self) -> None:
        # A Key does not keep a reference to its parent or children.

        key: Key[str] = Key(default="")
        level1: Key[str] = Key(default="")
        level1.setParent(key)
        level2: Key[str] = Key(default="")
        level2.setParent(level1)

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del key
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 0

    def test_new_instance_non_serializable(self) -> None:
        class NotSerializable:
            pass

        class Serializer:
            def toStr(self, value: NotSerializable) -> str:
                return "test"

            def fromStr(self, string: str) -> NotSerializable:
                return NotSerializable()

        key = Key(default=NotSerializable(), serializer=Serializer())
        other_key = key.newInstance()
        other_key.set(NotSerializable())

        assert list(other_key.dumpFields()) == [("", "test")]
