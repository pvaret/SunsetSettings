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


class TestBundle:
    def test_protocol_implementation(self):

        bundle = ExampleBundle()
        assert isinstance(bundle, protocols.Inheriter)
        assert isinstance(bundle, protocols.ItemTemplate)
        assert isinstance(bundle, protocols.Dumpable)
        assert isinstance(bundle, protocols.Restorable)
        assert isinstance(bundle, protocols.Container)
        assert isinstance(bundle, protocols.Containable)

    def test_creation(self):

        bundle = ExampleBundle()
        bundle.list.appendOne()
        assert bundle.a.get() == "default a"
        assert bundle.inner_bundle.b.get() == 42
        assert bundle.list[0].c.get() == "default c"

    def test_uninstantiated_attribute_fails(self):
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

        # "dump" is an attribute that happens to exist on the class.

        assert getattr(Bundle, "dump", None) is not None

        class FaultyBundle(Bundle):
            dump = Key(default="test")  # type: ignore -- that's the point

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

    def test_dump(self):

        bundle = ExampleBundle()
        assert list(bundle.dump()) == []

        bundle.a.set("test dump a")
        bundle.inner_bundle.b.set(101)
        bundle.list.appendOne()
        bundle.list[-1].c.set("test dump c 1")
        bundle.list.appendOne()
        bundle.list[-1].c.set("test dump c 2")

        assert bundle.dump() == [
            ("a", "test dump a"),
            ("inner_bundle.b", "101"),
            ("list.1.c", "test dump c 1"),
            ("list.2.c", "test dump c 2"),
        ]

    def test_dump_ignores_private_attributes(self):
        class ExampleBundleWithPrivateAttr(Bundle):
            _private = Key(default=0)
            public = Key(default=0)

        bundle = ExampleBundleWithPrivateAttr()
        bundle.public.set(56)

        # Ignore the private attribute access warning, it's the whole point.

        bundle._private.set(42)  # type:ignore

        assert bundle.dump() == [
            ("public", "56"),
        ]

    def test_restore(self, mocker: MockerFixture):

        bundle = ExampleBundle()
        callback = mocker.stub()
        bundle.onUpdateCall(callback)

        bundle.restore(
            [
                ("a", "test a"),
                ("inner_bundle.b", "999"),
                ("list.1.c", "test c 1"),
                ("list.2.c", "test c 2"),
            ]
        )

        assert bundle.a.get() == "test a"
        assert bundle.inner_bundle.b.get() == 999
        assert len(bundle.list) == 2
        assert bundle.list[0].c.get() == "test c 1"
        assert bundle.list[1].c.get() == "test c 2"

        # Ensure that a restore only triggers one update notification.

        callback.assert_called_once_with(bundle)

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
        callback.assert_called_once_with(bundle)
        callback.reset_mock()

        bundle.inner_bundle.b.set(123)
        callback.assert_called_once_with(bundle)
        callback.reset_mock()

        bundle.list.appendOne()
        callback.assert_called_once_with(bundle)
        callback.reset_mock()

        bundle.list[0].c.set("test 2")
        callback.assert_called_once_with(bundle)
        callback.reset_mock()

        child.a.set("test 3")
        callback.assert_not_called()
        callback.reset_mock()