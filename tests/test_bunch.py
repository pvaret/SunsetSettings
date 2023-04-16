import pytest

from pytest_mock import MockerFixture

from sunset import Bunch, Key, List, protocols


class ExampleBunch(Bunch):
    class InnerBunch(Bunch):
        b = Key(42)

    class Item(Bunch):
        c = Key("default c")

    a = Key("default a")
    inner_bunch = InnerBunch()
    list = List(Item(), order=List.PARENT_LAST)
    _private = Key("private")


class TestBunch:
    def test_protocol_implementation(self) -> None:
        bunch = ExampleBunch()
        assert isinstance(bunch, protocols.Field)
        assert isinstance(bunch, protocols.Container)

    def test_creation(self) -> None:
        bunch = ExampleBunch()
        bunch.list.appendOne()
        assert bunch.a.get() == "default a"
        assert bunch.inner_bunch.b.get() == 42
        assert bunch.list[0].c.get() == "default c"

    def test_uninstantiated_field_fails(self) -> None:
        class InnerBunch(Bunch):
            pass

        class FaultyBunch(Bunch):
            inner = InnerBunch

        with pytest.raises(TypeError):
            FaultyBunch()

    def test_inner_bunch_definition_is_fine(self) -> None:
        class FineBunch(Bunch):
            class InnerBunch(Bunch):
                pass

            inner = InnerBunch()

        FineBunch()

    def test_fields_cant_override_existing_attributes(self) -> None:
        # "__init__" is an attribute that happens to exist on the class.

        assert getattr(Bunch, "__init__", None) is not None

        class FaultyBunch(Bunch):
            __init__ = Key(default="test")  # type: ignore[assignment]

        with pytest.raises(TypeError):
            FaultyBunch()

    def test_inheritance(self) -> None:
        parent_bunch = ExampleBunch()
        child_bunch = ExampleBunch()

        assert child_bunch not in parent_bunch.children()
        assert child_bunch.parent() is None

        child_bunch.setParent(parent_bunch)
        assert child_bunch in parent_bunch.children()
        assert child_bunch.parent() is parent_bunch

        child_bunch.setParent(None)
        assert child_bunch not in parent_bunch.children()
        assert child_bunch.parent() is None

    def test_parenting(self) -> None:
        parent_bunch = ExampleBunch()
        child_bunch = ExampleBunch()
        child_bunch.setParent(parent_bunch)

        assert child_bunch.parent() is parent_bunch
        assert child_bunch in parent_bunch.children()

    def test_reparenting(self) -> None:
        bunch1 = ExampleBunch()
        bunch2 = ExampleBunch()
        child_bunch = ExampleBunch()

        assert child_bunch not in bunch1.children()
        assert child_bunch not in bunch2.children()
        assert child_bunch.parent() is None

        child_bunch.setParent(bunch1)
        assert child_bunch in bunch1.children()
        assert child_bunch not in bunch2.children()
        assert child_bunch.parent() is bunch1

        child_bunch.setParent(bunch2)
        assert child_bunch not in bunch1.children()
        assert child_bunch in bunch2.children()
        assert child_bunch.parent() is bunch2

        child_bunch.setParent(None)
        assert child_bunch not in bunch1.children()
        assert child_bunch not in bunch2.children()
        assert child_bunch.parent() is None

    def test_inheritance_propagation(self) -> None:
        parent_bunch = ExampleBunch()
        child_bunch = ExampleBunch()
        child_bunch.setParent(parent_bunch)

        assert child_bunch.a.parent() is parent_bunch.a
        assert child_bunch.inner_bunch.parent() is parent_bunch.inner_bunch
        assert child_bunch.inner_bunch.b.parent() is parent_bunch.inner_bunch.b
        assert child_bunch.list.parent() is parent_bunch.list

    def test_inheritance_values(self) -> None:
        parent_bunch = ExampleBunch()
        child_bunch = ExampleBunch()
        child_bunch.setParent(parent_bunch)

        parent_bunch.a.set("test parent")
        assert child_bunch.a.get() == "test parent"
        child_bunch.a.set("test child")
        assert child_bunch.a.get() == "test child"
        assert parent_bunch.a.get() == "test parent"

        parent_bunch.inner_bunch.b.set(101)
        assert child_bunch.inner_bunch.b.get() == 101
        child_bunch.inner_bunch.b.set(37)
        assert child_bunch.inner_bunch.b.get() == 37
        assert parent_bunch.inner_bunch.b.get() == 101

        parent_bunch.list.appendOne().c.set("test parent")
        assert [item.c.get() for item in parent_bunch.list.iter()] == [
            "test parent"
        ]
        assert [item.c.get() for item in child_bunch.list.iter()] == [
            "test parent"
        ]
        child_bunch.list.appendOne().c.set("test child")
        assert [item.c.get() for item in parent_bunch.list.iter()] == [
            "test parent"
        ]
        assert [item.c.get() for item in child_bunch.list.iter()] == [
            "test child",
            "test parent",
        ]
        del parent_bunch.list[0]
        assert [item.c.get() for item in parent_bunch.list.iter()] == []
        assert [item.c.get() for item in child_bunch.list.iter()] == [
            "test child"
        ]

    def test_field_label(self) -> None:
        bunch = ExampleBunch()

        assert bunch.fieldLabel() == ""
        assert bunch.inner_bunch.fieldLabel() == "inner_bunch"

    def test_field_path(self) -> None:
        bunch = ExampleBunch()
        assert bunch.fieldPath() == "."
        assert bunch.a.fieldPath() == ".a"
        assert bunch.inner_bunch.fieldPath() == ".inner_bunch."
        assert bunch.inner_bunch.b.fieldPath() == ".inner_bunch.b"
        assert bunch.inner_bunch.b.fieldPath() == ".inner_bunch.b"
        assert bunch.list.fieldPath() == ".list."
        bunch.list.appendOne()
        assert bunch.list[0].fieldPath() == ".list.1."
        assert bunch.list[0].c.fieldPath() == ".list.1.c"

    def test_dump_fields(self) -> None:
        bunch = ExampleBunch()
        assert list(bunch.dumpFields()) == []

        bunch.a.set("test dump a")
        bunch.inner_bunch.b.set(101)
        bunch.list.appendOne().c.set("test dump c 1")
        bunch.list.appendOne()
        bunch.list.appendOne().c.set("test dump c 3")
        bunch._private.set("test private")  # type: ignore

        assert list(bunch.dumpFields()) == [
            (".a", "test dump a"),
            (".inner_bunch.b", "101"),
            (".list.1.c", "test dump c 1"),
            (".list.2", None),
            (".list.3.c", "test dump c 3"),
        ]

    def test_restore_field(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        # Test all flavors of valid paths. Also, restoring a field should not
        # trigger a callbacak.

        bunch = ExampleBunch()
        bunch.onUpdateCall(callback)

        assert bunch.a.get() == "default a"
        bunch.restoreField(".a", "restore a")
        assert bunch.a.get() == "restore a"
        callback.assert_not_called()

        assert len(bunch.list) == 0
        bunch.restoreField(".list.2.c", "restore c 2")
        bunch.restoreField(".list.1.c", "restore c 1")
        assert len(bunch.list) == 2
        assert bunch.list[0].c.get() == "restore c 1"
        assert bunch.list[1].c.get() == "restore c 2"
        callback.assert_not_called()

        bunch.restoreField(".list.1.c", "other restore c 1")
        assert len(bunch.list) == 2
        assert bunch.list[0].c.get() == "other restore c 1"
        assert bunch.list[1].c.get() == "restore c 2"
        callback.assert_not_called()

        assert bunch.inner_bunch.b.get() == 42
        bunch.restoreField(".inner_bunch.b", "101")
        assert bunch.inner_bunch.b.get() == 101
        callback.assert_not_called()

        # Test invalid paths.

        other_bunch = ExampleBunch()
        other_bunch.onUpdateCall(callback)

        other_bunch.restoreField("a", "invalid path")
        assert other_bunch.a.get() == "default a"
        assert not other_bunch.isSet()

        other_bunch.restoreField("a.", "invalid path")
        assert other_bunch.a.get() == "default a"
        assert not other_bunch.isSet()

        other_bunch.restoreField(".", "invalid path")
        assert not other_bunch.isSet()

        other_bunch.restoreField(".invalid", "invalid path")
        assert not other_bunch.isSet()

        other_bunch.restoreField("", "invalid path")
        assert not other_bunch.isSet()

    def test_persistence(self) -> None:
        # A Bunch does not keep a reference to its parent or children.

        bunch = ExampleBunch()
        level1 = ExampleBunch()
        level2 = ExampleBunch()
        level1.setParent(bunch)
        level2.setParent(level1)

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del bunch
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 0

    def test_key_updated_notification(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        bunch = ExampleBunch()
        bunch.onUpdateCall(callback)

        child = ExampleBunch()
        child.setParent(bunch)

        bunch.a.set("test 1")
        callback.assert_called_once_with(bunch.a)
        callback.reset_mock()

        bunch.inner_bunch.b.set(123)
        callback.assert_called_once_with(bunch.inner_bunch.b)
        callback.reset_mock()

        bunch.list.appendOne()
        callback.assert_called_once_with(bunch.list)
        callback.reset_mock()

        bunch.list[0].c.set("test 2")
        callback.assert_called_once_with(bunch.list[0].c)
        callback.reset_mock()

        child.a.set("test 3")
        callback.assert_not_called()
        callback.reset_mock()

    def test_callback_type_is_flexible(self) -> None:
        bunch = ExampleBunch()

        class Dummy:
            pass

        def callback(_: ExampleBunch) -> Dummy:
            return Dummy()

        bunch.onUpdateCall(callback)
