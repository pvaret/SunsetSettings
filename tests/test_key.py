from typing import Optional

import pytest

from pytest_mock import MockerFixture

from sunset import Bundle, Key, protocols


class ExampleSerializable:
    def __init__(self, value: str) -> None:

        self._value = value

    def toStr(self) -> str:

        return self._value

    @staticmethod
    def fromStr(value: str) -> Optional["ExampleSerializable"]:

        return ExampleSerializable(value)


class TestKey:
    def test_protocol_implementation(self):

        key = Key(default="")
        assert isinstance(key, protocols.Inheriter)
        assert isinstance(key, protocols.ItemTemplate)
        assert isinstance(key, protocols.Dumpable)
        assert isinstance(key, protocols.Restorable)
        assert isinstance(key, protocols.Containable)

    def test_default(self):

        assert Key(default="default").get() == "default"
        assert Key(default=0).get() == 0
        assert type(Key(default=False).get()) is bool
        assert not Key(default=False).get()
        assert Key(default=12.345e-67).get() == 12.345e-67
        with pytest.raises(TypeError):
            Key(default=(1, "test"))  # type: ignore - it's the point.

    def test_set(self):

        key = Key(default="test")
        key.set("other")
        assert key.get() == "other"

    def test_clear(self):

        key = Key(default="default")
        key.set("other")
        assert key.get() != "default"

        key.clear()
        assert key.get() == "default"

    def test_serializable_type(self):

        value = ExampleSerializable.fromStr("dummy")
        assert value is not None
        key: Key[ExampleSerializable] = Key(default=value)

        assert key.get().toStr() == "dummy"

    def test_value_change_callback(self, mocker: MockerFixture):

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

    def test_value_change_callback_inheritance(self, mocker: MockerFixture):

        callback = mocker.stub()

        parent_key = Key(default="default")
        child_key = Key(default="default")
        child_key.setParent(parent_key)

        child_key.onValueChangeCall(callback)

        parent_key.set("inheritance")
        callback.assert_called_once_with("inheritance")
        callback.reset_mock()

        child_key.set("inheritance")
        callback.assert_not_called()
        callback.reset_mock()

        child_key.clear()
        callback.assert_not_called()
        callback.reset_mock()

        parent_key.clear()
        callback.assert_called_once_with("default")
        callback.reset_mock()

    def test_key_updated_callback(self, mocker: MockerFixture):

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

    def test_inheritance(self):

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

    def test_inherit_wrong_type(self):

        parent_key = Key(default="str")
        child_key = Key(default=0)

        # Ignore the type error, as it's the whole point of the test.

        child_key.setParent(parent_key)  # type: ignore

        assert child_key.parent() is None

    def test_inherit_revert(self):

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

    def test_repr(self):

        key1 = Key(default="test")
        key2 = Key(default=12)
        key3 = Key(default=" test\ntest")

        assert repr(key1) == "<Key[str]:test>"
        assert repr(key2) == "<Key[int]:12>"
        assert repr(key3) == '<Key[str]:" test\\ntest">'

    def test_reparenting(self):

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
    ):
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

    def test_dump(self):

        key: Key[str] = Key(default="default")

        # No value has been set.
        assert list(key.dump()) == []

        key.set("test")
        assert key.dump() == [("", "test")]

    def test_dump_serialization(self):

        value = ExampleSerializable.fromStr("test")
        assert value is not None

        key = Key(default=value)
        assert key.dump() == []

        key.set(ExampleSerializable("value"))
        assert key.dump() == [("", "value")]

    def test_restore_invalid(self, mocker: MockerFixture):

        key: Key[int] = Key(default=0)
        callback = mocker.stub()
        key.onUpdateCall(callback)

        key.restore([])
        assert key.get() == 0
        callback.assert_not_called()

        key = Key(default=0)
        key.onUpdateCall(callback)
        key.restore(
            [
                ("invalid", "12"),
            ]
        )

        # Restoring a key with an attribute name is invalid, so the value should
        # not be updated.

        assert key.get() == 0
        callback.assert_not_called()
        callback.reset_mock()

        key = Key(default=0)
        key.onUpdateCall(callback)
        key.restore(
            [
                ("", " invalid  "),
            ]
        )

        # Restoring a value that does not deserialize to the target type is
        # invalid and fails silently.

        assert key.get() == 0
        callback.assert_not_called()

        key = Key(default=0)
        key.onUpdateCall(callback)
        key.restore(
            [
                ("", "56"),
                ("", "78"),
                ("", "invalid"),
                ("invalid", "96"),
            ]
        )

        # Restoring a key with multiple values is invalid. However, restoring
        # something is better than dropping everything. Arbitrarily, we restore
        # the last valid value.

        assert key.get() == 78
        callback.assert_called_once_with(key)
        callback.reset_mock()

    def test_restore_valid(self, mocker: MockerFixture):

        callback = mocker.stub()

        key_str: Key[str] = Key(default="")
        key_str.onUpdateCall(callback)
        key_str.restore(
            [
                ("", "test"),
            ]
        )
        assert key_str.get() == "test"
        callback.assert_called_once_with(key_str)
        callback.reset_mock()

        key_int: Key[int] = Key(default=0)
        key_int.onUpdateCall(callback)
        key_int.restore(
            [
                ("", "12"),
            ]
        )
        assert key_int.get() == 12
        callback.assert_called_once_with(key_int)
        callback.reset_mock()

        key_float: Key[float] = Key(default=1.2)
        key_float.onUpdateCall(callback)
        key_float.restore(
            [
                ("", "3.4"),
            ]
        )
        assert key_float.get() == 3.4
        callback.assert_called_once_with(key_float)
        callback.reset_mock()

        key_bool: Key[bool] = Key(default=False)
        key_bool.onUpdateCall(callback)
        key_bool.restore(
            [
                ("", "true"),
            ]
        )
        assert key_bool.get()
        callback.assert_called_once_with(key_bool)
        callback.reset_mock()

        key_custom: Key[ExampleSerializable] = Key(
            default=ExampleSerializable("")
        )
        key_custom.onUpdateCall(callback)
        key_custom.restore(
            [
                ("", "test"),
            ]
        )
        assert key_custom.get().toStr() == "test"
        callback.assert_called_once_with(key_custom)
        callback.reset_mock()

    def test_persistence(self):

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