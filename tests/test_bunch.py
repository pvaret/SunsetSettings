import sys
import warnings
import pytest
from pytest_mock import MockerFixture

from sunset import Bunch, Bundle, Key, List, protocols


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

    def test_bunch_dataclass_mro(self) -> None:
        # Bunch instantiation is a tad tricky. Here we make sure that attributes
        # of a Bunch that are not dataclass fields do work as expected.

        class TestBunch(Bunch):
            a = Key("test a")
            b = "random attribute"

            def test_a(self) -> str:
                return self.a.get()

        bunch = TestBunch()
        assert bunch.test_a() == "test a"
        assert bunch.b == "random attribute"

    def test_multiple_subclass_levels_work(self) -> None:
        class TestParentBunch(Bunch):
            key1: Key[int] = Key(default=0)
            key2: Key[int] = Key(default=0)

        class TestChildBunch(TestParentBunch):
            key2: Key[int] = Key(default=42)
            key3: Key[int] = Key(default=100)

        # Create a blank Bunch to validate that doing so does not disrupt the Bunch
        # instantiation logic of child classes.
        Bunch()

        bunch = TestParentBunch()
        child_bunch = TestChildBunch()
        assert bunch.key1.get() == 0
        assert bunch.key2.get() == 0
        assert child_bunch.key1.get() == 0
        assert child_bunch.key2.get() == 42
        assert child_bunch.key3.get() == 100

        # Check that the inherited field is properly instantiated too, and not shared
        # across instances.

        other_child_bunch = TestChildBunch()
        other_child_bunch.key1.set(256)
        assert child_bunch.key1.get() == 0

    def test_multiple_instances_work_as_expected(self) -> None:
        bunch1 = ExampleBunch()
        bunch2 = ExampleBunch()

        # The Bunch instantiation logic is tricky. Check that basic expectations about
        # multiple instances of the same class are met.

        bunch1.a.set("test value")
        assert bunch1.a.get() == "test value"
        assert bunch2.a.get() == "default a"
        assert type(bunch1) is type(bunch2)
        assert isinstance(bunch1, ExampleBunch)
        assert isinstance(bunch2, ExampleBunch)
        if sys.version_info >= (3, 12):
            assert bunch1.__class__.__module__ == ExampleBunch.__module__
            assert bunch2.__class__.__module__ == ExampleBunch.__module__

    def test_extra_dataclass_fields(self) -> None:
        class TestDataclassBunch(Bunch):
            key: Key[int] = Key(default=0)
            str_default_value: str = "default"
            int_type: int

        bunch = TestDataclassBunch()
        assert bunch.key.get() == 0
        assert bunch.str_default_value == "default"
        bunch.int_type = 42
        assert bunch.int_type == 42

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
        assert [item.c.get() for item in parent_bunch.list.iter()] == ["test parent"]
        assert [item.c.get() for item in child_bunch.list.iter()] == ["test parent"]
        child_bunch.list.appendOne().c.set("test child")
        assert [item.c.get() for item in parent_bunch.list.iter()] == ["test parent"]
        assert [item.c.get() for item in child_bunch.list.iter()] == [
            "test child",
            "test parent",
        ]
        del parent_bunch.list[0]
        assert [item.c.get() for item in parent_bunch.list.iter()] == []
        assert [item.c.get() for item in child_bunch.list.iter()] == ["test child"]

    def test_dump_fields(self) -> None:
        bunch = ExampleBunch()
        assert list(bunch.dumpFields()) == []

        bunch.a.set("test dump a")
        bunch.inner_bunch.b.set(101)
        bunch.list.appendOne().c.set("test dump c 1")
        bunch.list.appendOne()
        bunch.list.appendOne().c.set("test dump c 3")
        bunch._private.set("test private")

        assert list(bunch.dumpFields()) == [
            ("a", "test dump a"),
            ("inner_bunch.b", "101"),
            ("list.1.c", "test dump c 1"),
            ("list.2", None),
            ("list.3.c", "test dump c 3"),
        ]

    def test_restore_field(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        # Test all flavors of valid paths. Also, restoring a field should not
        # trigger a callback.

        bunch = ExampleBunch()
        bunch.onUpdateCall(callback)

        assert bunch.a.get() == "default a"
        bunch.restoreField("a", "restore a")
        assert bunch.a.get() == "restore a"
        callback.assert_not_called()

        assert len(bunch.list) == 0
        bunch.restoreField("list.2.c", "restore c 2")
        bunch.restoreField("list.1.c", "restore c 1")
        assert len(bunch.list) == 2
        assert bunch.list[0].c.get() == "restore c 1"
        assert bunch.list[1].c.get() == "restore c 2"
        callback.assert_not_called()

        bunch.restoreField("list.1.c", "other restore c 1")
        assert len(bunch.list) == 2
        assert bunch.list[0].c.get() == "other restore c 1"
        assert bunch.list[1].c.get() == "restore c 2"
        callback.assert_not_called()

        assert bunch.inner_bunch.b.get() == 42
        bunch.restoreField("inner_bunch.b", "101")
        assert bunch.inner_bunch.b.get() == 101
        callback.assert_not_called()

        # Test invalid paths.

        other_bunch = ExampleBunch()
        other_bunch.onUpdateCall(callback)

        other_bunch.restoreField("x", "invalid path")
        assert not other_bunch.isSet()

        other_bunch.restoreField("a.a", "invalid path")
        assert not other_bunch.isSet()

        other_bunch.restoreField(".", "invalid path")
        assert not other_bunch.isSet()

        other_bunch.restoreField(".a", "invalid path")
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

    def test_init_properly_called(self) -> None:
        called: list[Bunch] = []

        class TestBunch(Bunch):
            a = Key(default=0)

            def __init__(self) -> None:
                super().__init__()
                called.append(self)

        bunch = TestBunch()
        assert bunch in called
        assert bunch.a.get() == 0

    def test_missing_init_super_does_not_make_attribute_shared(self) -> None:
        class TestBunch(Bunch):
            a = Key(default=0)

            def __init__(self) -> None:
                # This incorrectly fails to call super().__init__().
                pass

        bunch1 = TestBunch()
        bunch2 = TestBunch()
        bunch1.a.set(42)

        assert bunch2.a.get() == 0


class TestBundle:
    def test_bundle_works(self) -> None:
        class TestBundle(Bundle):
            key: Key[int] = Key(default=0)
            bunch: ExampleBunch = ExampleBunch()

        try:
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            bundle = TestBundle()
        finally:
            warnings.resetwarnings()

        bundle.key.set(42)
        bundle.bunch.a.set("test")

        assert bundle.key.get() == 42
        assert bundle.bunch.a.get() == "test"

    def test_bundle_raises_deprecation_warning(self) -> None:
        try:
            warnings.filterwarnings("error", category=DeprecationWarning)
            with pytest.raises(DeprecationWarning):
                Bundle()
        finally:
            warnings.resetwarnings()
