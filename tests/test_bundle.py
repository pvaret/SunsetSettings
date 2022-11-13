from pytest_mock import MockerFixture

from sunset import Bundle, Key, List, protocols


class ExampleBundle(Bundle):
    class InnerBundle(Bundle):
        b = Key(42)

    class Item(Bundle):
        c = Key("default c")

    a = Key("default a")
    inner_bundle = InnerBundle()
    list = List(Item())


class TestBundle:
    def test_protocol_implementation(self):

        t = ExampleBundle()
        assert isinstance(t, protocols.Inheriter)
        assert isinstance(t, protocols.ItemTemplate)
        assert isinstance(t, protocols.Dumpable)
        assert isinstance(t, protocols.Restorable)

    def test_creation(self):

        t = ExampleBundle()
        t.list.appendOne()
        assert t.a.get() == "default a"
        assert t.inner_bundle.b.get() == 42
        assert t.list[0].c.get() == "default c"

    def test_inheritance(self):

        t1 = ExampleBundle()
        t2 = ExampleBundle()

        assert t2 not in t1.children()
        assert t2.parent() is None

        t2.setParent(t1)
        assert t2 in t1.children()
        assert t2.parent() is t1

        t2.setParent(None)
        assert t2 not in t1.children()
        assert t2.parent() is None

    def test_reparenting(self):

        t1 = ExampleBundle()
        t2 = ExampleBundle()
        t3 = ExampleBundle()

        assert t3 not in t1.children()
        assert t3 not in t2.children()
        assert t3.parent() is None

        t3.setParent(t1)
        assert t3 in t1.children()
        assert t3 not in t2.children()
        assert t3.parent() is t1

        t3.setParent(t2)
        assert t3 not in t1.children()
        assert t3 in t2.children()
        assert t3.parent() is t2

        t3.setParent(None)
        assert t3 not in t1.children()
        assert t3 not in t2.children()
        assert t3.parent() is None

    def test_derivation(self):

        t1 = ExampleBundle()
        t2 = t1.derive()

        assert t2.parent() is t1
        assert t2 in t1.children()

    def test_inheritance_propagation(self):

        t1 = ExampleBundle()
        t2 = t1.derive()

        assert t2.a.parent() is t1.a
        assert t2.inner_bundle.parent() is t1.inner_bundle
        assert t2.inner_bundle.b.parent() is t1.inner_bundle.b
        assert t2.list.parent() is t1.list

    def test_inheritance_values(self):

        t1 = ExampleBundle()
        t2 = t1.derive()

        t1.a.set("test t1")
        assert t2.a.get() == "test t1"
        t2.a.set("test t2")
        assert t2.a.get() == "test t2"
        assert t1.a.get() == "test t1"

        t1.inner_bundle.b.set(101)
        assert t2.inner_bundle.b.get() == 101
        t2.inner_bundle.b.set(37)
        assert t2.inner_bundle.b.get() == 37
        assert t1.inner_bundle.b.get() == 101

        t1.list.appendOne()
        t1.list[0].c.set("test t1")
        assert [s.c.get() for s in t1.list.iterAll()] == ["test t1"]
        assert [s.c.get() for s in t2.list.iterAll()] == ["test t1"]
        t2.list.appendOne()
        t2.list[0].c.set("test t2")
        assert [s.c.get() for s in t1.list.iterAll()] == ["test t1"]
        assert [s.c.get() for s in t2.list.iterAll()] == [
            "test t2",
            "test t1",
        ]
        del t1.list[0]
        assert [s.c.get() for s in t1.list.iterAll()] == []
        assert [s.c.get() for s in t2.list.iterAll()] == ["test t2"]

    def test_dump(self):

        s = ExampleBundle()
        assert list(s.dump()) == []

        s.a.set("test dump a")
        s.inner_bundle.b.set(101)
        s.list.appendOne()
        s.list[-1].c.set("test dump c 1")
        s.list.appendOne()
        s.list[-1].c.set("test dump c 2")

        assert s.dump() == [
            ("a", "test dump a"),
            ("inner_bundle.b", "101"),
            ("list.1.c", "test dump c 1"),
            ("list.2.c", "test dump c 2"),
        ]

    def test_dump_ignores_private_attributes(self):
        class ExampleBundleWithPrivateAttr(Bundle):
            _private = Key(default=0)
            public = Key(default=0)

        s = ExampleBundleWithPrivateAttr()
        s.public.set(56)

        # Ignore the private attribute access warning, it's the whole point.

        s._private.set(42)  # type:ignore

        assert s.dump() == [
            ("public", "56"),
        ]

    def test_restore(self, mocker: MockerFixture):

        s = ExampleBundle()
        callback = mocker.stub()
        s.onUpdateCall(callback)

        s.restore(
            [
                ("a", "test a"),
                ("inner_bundle.b", "999"),
                ("list.1.c", "test c 1"),
                ("list.2.c", "test c 2"),
            ]
        )

        assert s.a.get() == "test a"
        assert s.inner_bundle.b.get() == 999
        assert len(s.list) == 2
        assert s.list[0].c.get() == "test c 1"
        assert s.list[1].c.get() == "test c 2"

        # Ensure that a restore only triggers one update notification.

        callback.assert_called_once_with(s)

    def test_persistence(self):

        # A Bundle does not keep a reference to its parent or children.

        bundle = ExampleBundle()
        level1 = bundle.derive()
        level2 = level1.derive()

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

        child = bundle.derive()

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
