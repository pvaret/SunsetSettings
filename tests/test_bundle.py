import pytest

from pytest_mock import MockerFixture

from sunset import Bundle, Key, List, protocols


class ExampleBundle(Bundle):
    class InnerBundle(Bundle):
        b = Key(42)

    class Item(Bundle):
        c = Key("default c")

    a = Key("default a")
    inner_bundle = InnerBundle()
    list = List(Item(), order=List.PARENT_LAST)
    _private = Key("private")


class TestBundle:
    def test_protocol_implementation(self):

        bundle = ExampleBundle()
        assert isinstance(bundle, protocols.Field)
        assert isinstance(bundle, protocols.Container)

    def test_creation(self):

        bundle = ExampleBundle()
        bundle.list.appendOne()
        assert bundle.a.get() == "default a"
        assert bundle.inner_bundle.b.get() == 42
        assert bundle.list[0].c.get() == "default c"

    def test_uninstantiated_field_fails(self):
        class InnerBundle(Bundle):
            pass

        class FaultyBundle(Bundle):
            inner = InnerBundle

        with pytest.raises(TypeError):
            FaultyBundle()

    def test_inner_bundle_definition_is_fine(self):
        class FineBundle(Bundle):
            class InnerBundle(Bundle):
                pass

            inner = InnerBundle()

        FineBundle()

    def test_fields_cant_override_existing_attributes(self):

        # "__init__" is an attribute that happens to exist on the class.

        assert getattr(Bundle, "__init__", None) is not None

        class FaultyBundle(Bundle):
            __init__ = Key(default="test")  # type: ignore[assignment]

        with pytest.raises(TypeError):
            FaultyBundle()

    def test_inheritance(self):

        parent_bundle = ExampleBundle()
        child_bundle = ExampleBundle()

        assert child_bundle not in parent_bundle.children()
        assert child_bundle.parent() is None

        child_bundle.setParent(parent_bundle)
        assert child_bundle in parent_bundle.children()
        assert child_bundle.parent() is parent_bundle

        child_bundle.setParent(None)
        assert child_bundle not in parent_bundle.children()
        assert child_bundle.parent() is None

    def test_parenting(self):

        parent_bundle = ExampleBundle()
        child_bundle = ExampleBundle()
        child_bundle.setParent(parent_bundle)

        assert child_bundle.parent() is parent_bundle
        assert child_bundle in parent_bundle.children()

    def test_reparenting(self):

        bundle1 = ExampleBundle()
        bundle2 = ExampleBundle()
        child_bundle = ExampleBundle()

        assert child_bundle not in bundle1.children()
        assert child_bundle not in bundle2.children()
        assert child_bundle.parent() is None

        child_bundle.setParent(bundle1)
        assert child_bundle in bundle1.children()
        assert child_bundle not in bundle2.children()
        assert child_bundle.parent() is bundle1

        child_bundle.setParent(bundle2)
        assert child_bundle not in bundle1.children()
        assert child_bundle in bundle2.children()
        assert child_bundle.parent() is bundle2

        child_bundle.setParent(None)
        assert child_bundle not in bundle1.children()
        assert child_bundle not in bundle2.children()
        assert child_bundle.parent() is None

    def test_inheritance_propagation(self):

        parent_bundle = ExampleBundle()
        child_bundle = ExampleBundle()
        child_bundle.setParent(parent_bundle)

        assert child_bundle.a.parent() is parent_bundle.a
        assert child_bundle.inner_bundle.parent() is parent_bundle.inner_bundle
        assert (
            child_bundle.inner_bundle.b.parent() is parent_bundle.inner_bundle.b
        )
        assert child_bundle.list.parent() is parent_bundle.list

    def test_inheritance_values(self):

        parent_bundle = ExampleBundle()
        child_bundle = ExampleBundle()
        child_bundle.setParent(parent_bundle)

        parent_bundle.a.set("test parent")
        assert child_bundle.a.get() == "test parent"
        child_bundle.a.set("test child")
        assert child_bundle.a.get() == "test child"
        assert parent_bundle.a.get() == "test parent"

        parent_bundle.inner_bundle.b.set(101)
        assert child_bundle.inner_bundle.b.get() == 101
        child_bundle.inner_bundle.b.set(37)
        assert child_bundle.inner_bundle.b.get() == 37
        assert parent_bundle.inner_bundle.b.get() == 101

        parent_bundle.list.appendOne().c.set("test parent")
        assert [item.c.get() for item in parent_bundle.list.iter()] == [
            "test parent"
        ]
        assert [item.c.get() for item in child_bundle.list.iter()] == [
            "test parent"
        ]
        child_bundle.list.appendOne().c.set("test child")
        assert [item.c.get() for item in parent_bundle.list.iter()] == [
            "test parent"
        ]
        assert [item.c.get() for item in child_bundle.list.iter()] == [
            "test child",
            "test parent",
        ]
        del parent_bundle.list[0]
        assert [item.c.get() for item in parent_bundle.list.iter()] == []
        assert [item.c.get() for item in child_bundle.list.iter()] == [
            "test child"
        ]

    def test_field_label(self):

        bundle = ExampleBundle()

        assert bundle.fieldLabel() == ""
        assert bundle.inner_bundle.fieldLabel() == "inner_bundle"

    def test_field_path(self):

        bundle = ExampleBundle()
        assert bundle.fieldPath() == "."
        assert bundle.a.fieldPath() == ".a"
        assert bundle.inner_bundle.fieldPath() == ".inner_bundle."
        assert bundle.inner_bundle.b.fieldPath() == ".inner_bundle.b"
        assert bundle.inner_bundle.b.fieldPath() == ".inner_bundle.b"
        assert bundle.list.fieldPath() == ".list."
        bundle.list.appendOne()
        assert bundle.list[0].fieldPath() == ".list.1."
        assert bundle.list[0].c.fieldPath() == ".list.1.c"

    def test_dump_fields(self):

        bundle = ExampleBundle()
        assert list(bundle.dumpFields()) == []

        bundle.a.set("test dump a")
        bundle.inner_bundle.b.set(101)
        bundle.list.appendOne().c.set("test dump c 1")
        bundle.list.appendOne()
        bundle.list.appendOne().c.set("test dump c 3")
        bundle._private.set("test private")  # type: ignore

        assert list(bundle.dumpFields()) == [
            (".a", "test dump a"),
            (".inner_bundle.b", "101"),
            (".list.1.c", "test dump c 1"),
            (".list.2", None),
            (".list.3.c", "test dump c 3"),
        ]

    def test_restore_field(self, mocker: MockerFixture):

        callback = mocker.stub()

        # Test all flavors of valid paths. Also, restoring a field should not
        # trigger a callbacak.

        bundle = ExampleBundle()
        bundle.onUpdateCall(callback)

        assert bundle.a.get() == "default a"
        bundle.restoreField(".a", "restore a")
        assert bundle.a.get() == "restore a"
        callback.assert_not_called()

        assert len(bundle.list) == 0
        bundle.restoreField(".list.2.c", "restore c 2")
        bundle.restoreField(".list.1.c", "restore c 1")
        assert len(bundle.list) == 2
        assert bundle.list[0].c.get() == "restore c 1"
        assert bundle.list[1].c.get() == "restore c 2"
        callback.assert_not_called()

        bundle.restoreField(".list.1.c", "other restore c 1")
        assert len(bundle.list) == 2
        assert bundle.list[0].c.get() == "other restore c 1"
        assert bundle.list[1].c.get() == "restore c 2"
        callback.assert_not_called()

        assert bundle.inner_bundle.b.get() == 42
        bundle.restoreField(".inner_bundle.b", "101")
        assert bundle.inner_bundle.b.get() == 101
        callback.assert_not_called()

        # Test invalid paths.

        other_bundle = ExampleBundle()
        other_bundle.onUpdateCall(callback)

        other_bundle.restoreField("a", "invalid path")
        assert other_bundle.a.get() == "default a"
        assert not other_bundle.isSet()

        other_bundle.restoreField("a.", "invalid path")
        assert other_bundle.a.get() == "default a"
        assert not other_bundle.isSet()

        other_bundle.restoreField(".", "invalid path")
        assert not other_bundle.isSet()

        other_bundle.restoreField(".invalid", "invalid path")
        assert not other_bundle.isSet()

        other_bundle.restoreField("", "invalid path")
        assert not other_bundle.isSet()

    def test_persistence(self):

        # A Bundle does not keep a reference to its parent or children.

        bundle = ExampleBundle()
        level1 = ExampleBundle()
        level2 = ExampleBundle()
        level1.setParent(bundle)
        level2.setParent(level1)

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del bundle
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 0

    def test_key_updated_notification(self, mocker: MockerFixture):

        callback = mocker.stub()

        bundle = ExampleBundle()
        bundle.onUpdateCall(callback)

        child = ExampleBundle()
        child.setParent(bundle)

        bundle.a.set("test 1")
        callback.assert_called_once_with(bundle.a)
        callback.reset_mock()

        bundle.inner_bundle.b.set(123)
        callback.assert_called_once_with(bundle.inner_bundle.b)
        callback.reset_mock()

        bundle.list.appendOne()
        callback.assert_called_once_with(bundle.list)
        callback.reset_mock()

        bundle.list[0].c.set("test 2")
        callback.assert_called_once_with(bundle.list[0].c)
        callback.reset_mock()

        child.a.set("test 3")
        callback.assert_not_called()
        callback.reset_mock()
