from typing import Optional

from pytest_mock import MockerFixture

import sunset


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

        s = sunset.Key(default="")
        assert isinstance(s, sunset.protocols.Inheriter)
        assert isinstance(s, sunset.protocols.ItemTemplate)
        assert isinstance(s, sunset.protocols.Dumpable)
        assert isinstance(s, sunset.protocols.Restorable)

    def test_default(self):

        s = sunset.Key(default="default")
        assert s.get() == "default"

    def test_set(self):

        s = sunset.Key(default="test")
        s.set("other")
        assert s.get() == "other"

    def test_clear(self):

        s = sunset.Key(default="default")
        s.set("other")
        assert s.get() != "default"

        s.clear()
        assert s.get() == "default"

    def test_serializable_type(self):

        t = ExampleSerializable.fromStr("dummy")
        assert t is not None
        s: sunset.Key[ExampleSerializable] = sunset.Key(default=t)

        assert s.get().toStr() == "dummy"

    def test_value_change_callback(self, mocker: MockerFixture):

        callback = mocker.stub()

        s = sunset.Key(default="default")

        s.onValueChangeCall(callback)

        s.set("default")
        callback.assert_not_called()
        callback.reset_mock()

        s.set("not default")
        callback.assert_called_once_with("not default")
        callback.reset_mock()

        s.clear()
        callback.assert_called_once_with("default")
        callback.reset_mock()

        s.clear()
        callback.assert_not_called()

    def test_value_change_callback_inheritance(self, mocker: MockerFixture):

        callback = mocker.stub()

        s = sunset.Key(default="default")
        s2 = sunset.Key(default="default")
        s2.setParent(s)

        s2.onValueChangeCall(callback)

        s.set("inheritance")
        callback.assert_called_once_with("inheritance")
        callback.reset_mock()

        s2.set("inheritance")
        callback.assert_not_called()
        callback.reset_mock()

        s2.clear()
        callback.assert_not_called()
        callback.reset_mock()

        s.clear()
        callback.assert_called_once_with("default")
        callback.reset_mock()

    def test_key_modified_callback(self, mocker: MockerFixture):

        callback = mocker.stub()

        s = sunset.Key(default="default")
        assert isinstance(s, sunset.protocols.ModificationNotifier)

        s.onKeyModifiedCall(callback)

        s.set("default")
        callback.assert_called_once_with(s)
        callback.reset_mock()

        s.set("not default")
        callback.assert_called_once_with(s)
        callback.reset_mock()

        s.set("not default")
        callback.assert_not_called()
        callback.reset_mock()

        s.clear()
        callback.assert_called_once_with(s)
        callback.reset_mock()

        s.clear()
        callback.assert_not_called()
        callback.reset_mock()

    def test_inheritance(self):

        a = sunset.Key(default="default a")
        b = sunset.Key(default="")

        assert b not in a.children()
        b.setParent(a)
        assert b in a.children()

        assert b.get() == "default a"

        a.set("new a")
        assert b.get() == "new a"

        b.set("new b")
        assert b.get() == "new b"

        a.clear()
        assert b.get() == "new b"

        b.clear()
        assert b.get() == "default a"

    def test_inherit_wrong_type(self):

        a = sunset.Key(default="str")
        b = sunset.Key(default=0)

        # Ignore the type error, as it's the whole point of the test.
        b.setParent(a)  # type: ignore

        assert b.parent() is None

    def test_inherit_revert(self):

        a = sunset.Key(default="default a")
        b = sunset.Key(default="default b")

        assert b not in a.children()
        assert b.parent() is None

        b.setParent(a)

        assert b in a.children()
        assert b.parent() is a

        b.setParent(None)

        assert b not in a.children()
        assert b.parent() is None

    def test_repr(self):

        a = sunset.Key(default="test")
        b = sunset.Key(default=12)

        assert repr(a) == "<Key[str]:test>"
        assert repr(b) == "<Key[int]:12>"

    def test_reparenting(self):

        a = sunset.Key(default="default a")
        b = sunset.Key(default="default b")
        c = sunset.Key(default="default c")

        assert c not in a.children()
        assert c not in b.children()

        c.setParent(a)
        assert c in a.children()
        assert c not in b.children()

        c.setParent(b)
        assert c not in a.children()
        assert c in b.children()

        c.setParent(None)
        assert c not in a.children()
        assert c not in b.children()

    def test_callback_triggered_on_parent_value_change(
        self, mocker: MockerFixture
    ):
        stub = mocker.stub()

        a = sunset.Key(default="default a")
        b = sunset.Key(default="default b")
        b.setParent(a)

        b.onValueChangeCall(stub)

        b.set("test 1")
        stub.assert_called_once_with("test 1")
        stub.reset_mock()

        b.clear()
        stub.assert_called_once_with("default a")
        stub.reset_mock()

        a.set("test 2")
        stub.assert_called_once_with("test 2")
        stub.reset_mock()

        a.clear()
        stub.assert_called_once_with("default a")

    def test_dump(self):

        s: sunset.Key[str] = sunset.Key(default="default")

        # No value has been set.
        assert list(s.dump()) == []

        s.set("test")
        assert s.dump() == [("", "test")]

    def test_dump_serialization(self):

        t = ExampleSerializable.fromStr("test")
        assert t is not None

        s = sunset.Key(default=t)
        assert s.dump() == []

        s.set(ExampleSerializable("value"))
        assert s.dump() == [("", "value")]

    def test_restore_invalid(self, mocker: MockerFixture):

        si: sunset.Key[int] = sunset.Key(default=0)
        callback = mocker.stub()
        si.onKeyModifiedCall(callback)

        si.restore([])
        assert si.get() == 0
        callback.assert_not_called()

        si = sunset.Key(default=0)
        si.onKeyModifiedCall(callback)
        si.restore(
            [
                ("invalid", "12"),
            ]
        )

        # Restoring a key with an attribute name is invalid, so the value should
        # not be updated.

        assert si.get() == 0
        callback.assert_not_called()
        callback.reset_mock()

        si = sunset.Key(default=0)
        si.onKeyModifiedCall(callback)
        si.restore(
            [
                ("", " invalid  "),
            ]
        )

        # Restoring a value that does not deserialize to the target type is
        # invalid and fails silently.

        assert si.get() == 0
        callback.assert_not_called()

        si = sunset.Key(default=0)
        si.onKeyModifiedCall(callback)
        si.restore(
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

        assert si.get() == 78
        callback.assert_called_once_with(si)
        callback.reset_mock()

    def test_restore_valid(self, mocker: MockerFixture):

        callback = mocker.stub()

        sstr: sunset.Key[str] = sunset.Key(default="")
        sstr.onKeyModifiedCall(callback)
        sstr.restore(
            [
                ("", "test"),
            ]
        )
        assert sstr.get() == "test"
        callback.assert_called_once_with(sstr)
        callback.reset_mock()

        si: sunset.Key[int] = sunset.Key(default=0)
        si.onKeyModifiedCall(callback)
        si.restore(
            [
                ("", "12"),
            ]
        )
        assert si.get() == 12
        callback.assert_called_once_with(si)
        callback.reset_mock()

        sb: sunset.Key[bool] = sunset.Key(default=False)
        sb.onKeyModifiedCall(callback)
        sb.restore(
            [
                ("", "true"),
            ]
        )
        assert sb.get()
        callback.assert_called_once_with(sb)
        callback.reset_mock()

        sser: sunset.Key[ExampleSerializable] = sunset.Key(
            default=ExampleSerializable("")
        )
        sser.onKeyModifiedCall(callback)
        sser.restore(
            [
                ("", "test"),
            ]
        )
        assert sser.get().toStr() == "test"
        callback.assert_called_once_with(sser)
        callback.reset_mock()

    def test_persistence(self):

        # A Key does not keep a reference to its parent or children.

        key: sunset.Key[str] = sunset.Key(default="")
        level1: sunset.Key[str] = sunset.Key(default="")
        level1.setParent(key)
        level2: sunset.Key[str] = sunset.Key(default="")
        level2.setParent(level1)

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del key
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 0
