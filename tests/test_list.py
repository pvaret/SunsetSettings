from typing import Iterator

from pytest_mock import MockerFixture

import sunset


class ExampleSection(sunset.Section):

    test: sunset.Key[str] = sunset.NewKey("")


class TestList:
    def test_protocol_implementation(self):

        r: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())
        assert isinstance(r, sunset.protocols.Inheriter)
        assert isinstance(r, sunset.protocols.Dumpable)

    def test_add_pop(self):

        r: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())
        r.append(ExampleSection())

        assert len(r) == 1

        r[0].test.set("test")
        assert r[0].test.get() == "test"

        r.pop()

        assert len(r) == 0

    def test_inheritance(self):

        r1: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())
        r2: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())

        assert r2 not in r1.children()
        assert r2.parent() is None

        r2.setParent(r1)
        assert r2 in r1.children()
        assert r2.parent() is r1

        r2.setParent(None)
        assert r2 not in r1.children()
        assert r2.parent() is None

    def test_reparenting(self):

        r1: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())
        r2: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())
        r3: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())

        assert r3 not in r1.children()
        assert r3 not in r2.children()
        assert r3.parent() is None

        r3.setParent(r1)
        assert r3 in r1.children()
        assert r3 not in r2.children()
        assert r3.parent() is r1

        r3.setParent(r2)
        assert r3 not in r1.children()
        assert r3 in r2.children()
        assert r3.parent() is r2

        r3.setParent(None)
        assert r3 not in r1.children()
        assert r3 not in r2.children()
        assert r3.parent() is None

    def test_iter_inheritance(self):
        def flatten(fixtures: Iterator[ExampleSection]) -> list[str]:
            return [f.test.get() for f in fixtures]

        r1: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())
        r2: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())

        r1.append(ExampleSection())
        r1[0].test.set("test r1")
        r2.append(ExampleSection())
        r2[0].test.set("test r2")

        assert flatten(r2.iterAll()) == ["test r2"]

        r2.setParent(r1)

        assert flatten(r2.iterAll()) == ["test r2", "test r1"]

    def test_dump(self):

        r: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())

        assert r.dump() == []

        t = ExampleSection()
        r.append(t)
        t.test.set("test 1")

        t = ExampleSection()
        r.append(t)
        t.test.set("test 2")

        assert r.dump() == [
            ("1.test", "test 1"),
            ("2.test", "test 2"),
        ]

    def test_restore(self, mocker: MockerFixture):

        r: sunset.List[ExampleSection] = sunset.List(lambda: ExampleSection())
        callback = mocker.stub()
        r.onKeyModifiedCall(callback)

        r.restore(
            [
                ("1.test", "test 1"),
                ("2.test", "test 2"),
            ]
        )

        assert len(r) == 2
        assert r[0].test.get() == "test 1"
        assert r[1].test.get() == "test 2"

        # Ensure that a restore only triggers one modification notification.

        callback.assert_called_once_with(r)

    def test_persistence(self):

        # A List does not keep a reference to its parent or children.

        section_list: sunset.List[ExampleSection] = sunset.List(
            lambda: ExampleSection()
        )
        level1: sunset.List[ExampleSection] = sunset.List(
            lambda: ExampleSection()
        )
        level1.setParent(section_list)
        level2: sunset.List[ExampleSection] = sunset.List(
            lambda: ExampleSection()
        )
        level2.setParent(level1)

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del section_list
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 0

    def test_modification_callback_called_on_list_contents_changed(
        self, mocker: MockerFixture
    ):

        callback = mocker.stub()

        section_list: sunset.List[ExampleSection] = sunset.List(
            lambda: ExampleSection()
        )

        section_list.onKeyModifiedCall(callback)

        section_list.append(ExampleSection())
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        section_list.insert(0, ExampleSection())
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        section_list[0] = ExampleSection()
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        section_list += [ExampleSection(), ExampleSection(), ExampleSection()]
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        section_list.extend(
            [ExampleSection(), ExampleSection(), ExampleSection()]
        )
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        section_list[2:4] = [
            ExampleSection(),
            ExampleSection(),
            ExampleSection(),
        ]
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        section_list.pop()
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        s1 = section_list[0]
        section_list.remove(s1)
        assert s1 not in section_list
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        del section_list[0]
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        assert len(section_list[1:3]) == 2
        del section_list[1:3]
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

        assert len(section_list) > 1
        section_list.clear()
        callback.assert_called_once_with(section_list)
        callback.reset_mock()

    def test_modification_callback_called_on_contained_item_modification(
        self, mocker: MockerFixture
    ):

        callback = mocker.stub()

        section_list: sunset.List[ExampleSection] = sunset.List(
            lambda: ExampleSection()
        )
        section_list.onKeyModifiedCall(callback)

        s1 = ExampleSection()
        section_list.append(s1)
        callback.reset_mock()
        s1.test.set("test")
        callback.assert_called_once_with(section_list)

        s2 = ExampleSection()
        section_list.insert(0, s2)
        callback.reset_mock()
        s2.test.set("test")
        callback.assert_called_once_with(section_list)

        s3 = ExampleSection()
        section_list[0] = s3
        callback.reset_mock()
        s3.test.set("test")
        callback.assert_called_once_with(section_list)

        s4 = ExampleSection()
        s5 = ExampleSection()
        section_list[1:2] = [s4, s5]
        callback.reset_mock()
        s4.test.set("test")
        callback.assert_called_once_with(section_list)
        callback.reset_mock()
        s5.test.set("test")
        callback.assert_called_once_with(section_list)

        s6 = ExampleSection()
        s7 = ExampleSection()
        section_list += [s6, s7]
        callback.reset_mock()
        s6.test.set("test")
        callback.assert_called_once_with(section_list)
        callback.reset_mock()
        s7.test.set("test")
        callback.assert_called_once_with(section_list)

        s8 = ExampleSection()
        s9 = ExampleSection()
        section_list.extend([s8, s9])
        callback.reset_mock()
        s8.test.set("test")
        callback.assert_called_once_with(section_list)
        callback.reset_mock()
        s9.test.set("test")
        callback.assert_called_once_with(section_list)

    def test_modification_callback_not_called_for_removed_items(
        self, mocker: MockerFixture
    ):

        section_list: sunset.List[ExampleSection] = sunset.List(
            lambda: ExampleSection()
        )

        s1 = ExampleSection()
        s2 = ExampleSection()

        callback = mocker.stub()
        section_list.onKeyModifiedCall(callback)

        s1.test.clear()
        section_list[:] = [s1]
        del section_list[0]

        callback.reset_mock()
        s1.test.set("test")
        callback.assert_not_called()

        s1.test.clear()
        s2.test.clear()
        section_list[:] = [s1, s2]
        del section_list[0:2]

        callback.reset_mock()
        s1.test.set("test")
        s2.test.set("test")
        callback.assert_not_called()

        s1.test.clear()
        s2.test.clear()
        section_list[:] = [s1, s2]
        section_list.clear()

        callback.reset_mock()
        s1.test.set("test")
        s2.test.set("test")
        callback.assert_not_called()

        s1.test.clear()
        section_list[:] = [s1]
        section_list.pop()

        callback.reset_mock()
        s1.test.set("test")
        callback.assert_not_called()

        s1.test.clear()
        section_list[:] = [s1]
        section_list.remove(s1)
        assert s1 not in section_list

        callback.reset_mock()
        s1.test.set("test")
        callback.assert_not_called()
