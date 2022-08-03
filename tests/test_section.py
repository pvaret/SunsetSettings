import pytest

from pytest_mock import MockerFixture

import sunset


class ExampleSection(sunset.Section):
    class Subsection(sunset.Section):
        b: sunset.Setting[int] = sunset.NewSetting(42)

    class Item(sunset.Section):
        c: sunset.Setting[str] = sunset.NewSetting("default c")

    a: sunset.Setting[str] = sunset.NewSetting("default a")
    subsection: Subsection = sunset.NewSection(Subsection)
    list: sunset.List[Item] = sunset.NewList(Item)


class TestSection:
    def test_protocol_implementation(self):

        t = ExampleSection()
        assert isinstance(t, sunset.protocols.Inheriter)
        assert isinstance(t, sunset.protocols.Dumpable)

    def test_creation(self):

        t = ExampleSection()
        t.list.append(ExampleSection.Item())
        assert t.a.get() == "default a"
        assert t.subsection.b.get() == 42
        assert t.list[0].c.get() == "default c"

    def test_inheritance(self):

        t1 = ExampleSection()
        t2 = ExampleSection()

        assert t2 not in t1.children()
        assert t2.parent() is None

        t2.setParent(t1)
        assert t2 in t1.children()
        assert t2.parent() is t1

        t2.setParent(None)
        assert t2 not in t1.children()
        assert t2.parent() is None

    def test_reparenting(self):

        t1 = ExampleSection()
        t2 = ExampleSection()
        t3 = ExampleSection()

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

        t1 = ExampleSection()
        t2 = t1.derive()

        assert t2.parent() is t1
        assert t2 in t1.children()

    def test_inheritance_propagation(self):

        t1 = ExampleSection()
        t2 = t1.derive()

        assert t2.a.parent() is t1.a
        assert t2.subsection.parent() is t1.subsection
        assert t2.subsection.b.parent() is t1.subsection.b
        assert t2.list.parent() is t1.list

    def test_inheritance_values(self):

        t1 = ExampleSection()
        t2 = t1.derive()

        t1.a.set("test t1")
        assert t2.a.get() == "test t1"
        t2.a.set("test t2")
        assert t2.a.get() == "test t2"
        assert t1.a.get() == "test t1"

        t1.subsection.b.set(101)
        assert t2.subsection.b.get() == 101
        t2.subsection.b.set(37)
        assert t2.subsection.b.get() == 37
        assert t1.subsection.b.get() == 101

        t1.list.append(ExampleSection.Item())
        t1.list[0].c.set("test t1")
        assert [s.c.get() for s in t1.list.iterAll()] == ["test t1"]
        assert [s.c.get() for s in t2.list.iterAll()] == ["test t1"]
        t2.list.append(ExampleSection.Item())
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

        s = ExampleSection()
        assert list(s.dump()) == []

        s.a.set("test dump a")
        s.subsection.b.set(101)
        s.list.append(ExampleSection.Item())
        s.list[-1].c.set("test dump c 1")
        s.list.append(ExampleSection.Item())
        s.list[-1].c.set("test dump c 2")

        assert s.dump() == [
            ("a", "test dump a"),
            ("list.1.c", "test dump c 1"),
            ("list.2.c", "test dump c 2"),
            ("subsection.b", "101"),
        ]

    def test_dump_ignores_private_attributes(self):
        class ExampleSectionWithPrivateAttr(sunset.Section):
            _private: sunset.Setting[int] = sunset.NewSetting(default=0)
            public: sunset.Setting[int] = sunset.NewSetting(default=0)

        s = ExampleSectionWithPrivateAttr()
        s.public.set(56)
        # Ignore the private attribute access warning, it's the whole point.
        s._private.set(42)  # type:ignore

        assert s.dump() == [
            ("public", "56"),
        ]

    def test_restore(self):

        s = ExampleSection()
        s.restore(
            [
                ("a", "test a"),
                ("subsection.b", "999"),
                ("list.1.c", "test c 1"),
                ("list.2.c", "test c 2"),
            ]
        )

        assert s.a.get() == "test a"
        assert s.subsection.b.get() == 999
        assert len(s.list) == 2
        assert s.list[0].c.get() == "test c 1"
        assert s.list[1].c.get() == "test c 2"

    def test_persistence(self):

        # A Section does not keep a reference to its parent or children.

        section = ExampleSection()
        level1 = section.derive()
        level2 = level1.derive()

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del section
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 0

    def test_setting_modified_notification(self, mocker: MockerFixture):

        callback = mocker.stub()

        section = ExampleSection()
        section.onSettingModifiedCall(callback)

        child = section.derive()

        section.a.set("test 1")
        callback.assert_called_once_with(section)
        callback.reset_mock()

        section.subsection.b.set(123)
        callback.assert_called_once_with(section)
        callback.reset_mock()

        section.list.append(ExampleSection.Item())
        callback.assert_called_once_with(section)
        callback.reset_mock()

        section.list[0].c.set("test 2")
        callback.assert_called_once_with(section)
        callback.reset_mock()

        child.a.set("test 3")
        callback.assert_not_called()
        callback.reset_mock()

    def test_incorrect_usage_raises_exception(self):
        class TestSection1(sunset.Section):
            s: sunset.Setting[int] = sunset.Setting(default=0)

        with pytest.raises(ValueError):
            TestSection1()

        class TestSection2(sunset.Section):
            class Subsection(sunset.Section):
                pass

            subsection: Subsection = Subsection()

        with pytest.raises(ValueError):
            TestSection2()

        class TestSection3(sunset.Section):
            class Subsection(sunset.Section):
                pass

            subsections: sunset.List[Subsection] = sunset.List(Subsection)

        with pytest.raises(ValueError):
            TestSection3()
