from typing import Iterator

from pytest_mock import MockerFixture

from sunset import Bundle, Key, List, protocols


class ExampleBundle(Bundle):

    test = Key("")


class TestList:
    def test_protocol_implementation(self):

        r: List[Key[int]] = List(Key(default=0))
        assert isinstance(r, protocols.Inheriter)
        assert isinstance(r, protocols.ItemTemplate)
        assert isinstance(r, protocols.Dumpable)
        assert isinstance(r, protocols.Restorable)

    def test_add_pop(self):

        r: List[Key[str]] = List(Key(default=""))
        r.appendOne()

        assert len(r) == 1

        r[0].set("test")
        assert r[0].get() == "test"

        r.pop()

        assert len(r) == 0

    def test_inheritance(self):

        r1: List[Key[int]] = List(Key(default=0))
        r2: List[Key[int]] = List(Key(default=0))

        assert r2 not in r1.children()
        assert r2.parent() is None

        r2.setParent(r1)
        assert r2 in r1.children()
        assert r2.parent() is r1

        r2.setParent(None)
        assert r2 not in r1.children()
        assert r2.parent() is None

    def test_reparenting(self):

        r1: List[Key[int]] = List(Key(default=0))
        r2: List[Key[int]] = List(Key(default=0))
        r3: List[Key[int]] = List(Key(default=0))

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
        def flatten(fixtures: Iterator[Key[str]]) -> list[str]:
            return [f.get() for f in fixtures]

        parent: List[Key[str]] = List(Key(default=""))
        child_default: List[Key[str]] = List(Key(default=""))
        child_iter_no_parent: List[Key[str]] = List(
            Key(default=""), order=List.NO_PARENT
        )
        child_iter_parent_first: List[Key[str]] = List(
            Key(default=""), order=List.PARENT_FIRST
        )
        child_iter_parent_last: List[Key[str]] = List(
            Key(default=""), order=List.PARENT_LAST
        )

        parent.appendOne().set("parent")
        child_default.appendOne().set("child")
        child_iter_no_parent.appendOne().set("child")
        child_iter_parent_first.appendOne().set("child")
        child_iter_parent_last.appendOne().set("child")

        assert flatten(child_default.iter()) == ["child"]

        child_default.setParent(parent)
        child_iter_no_parent.setParent(parent)
        child_iter_parent_first.setParent(parent)
        child_iter_parent_last.setParent(parent)

        assert flatten(child_default.iter()) == ["child"]
        assert flatten(child_iter_no_parent.iter()) == ["child"]
        assert flatten(child_iter_parent_first.iter()) == ["parent", "child"]
        assert flatten(child_iter_parent_last.iter()) == ["child", "parent"]
        assert flatten(child_default.iter(order=List.NO_PARENT)) == ["child"]
        assert flatten(child_default.iter(order=List.PARENT_FIRST)) == [
            "parent",
            "child",
        ]
        assert flatten(child_default.iter(order=List.PARENT_LAST)) == [
            "child",
            "parent",
        ]

    def test_dump_bundles(self):

        r: List[ExampleBundle] = List(ExampleBundle())

        assert r.dump() == []

        r.appendOne().test.set("test 1")
        r.appendOne().test.set("test 2")

        assert r.dump() == [
            ("1.test", "test 1"),
            ("2.test", "test 2"),
        ]

    def test_dump_keys(self):

        r: List[Key[str]] = List(Key(default=""))

        assert r.dump() == []

        r.appendOne().set("test 1")
        r.appendOne().set("test 2")

        assert r.dump() == [
            ("1", "test 1"),
            ("2", "test 2"),
        ]

    def test_restore_bundles(self, mocker: MockerFixture):

        r: List[ExampleBundle] = List(ExampleBundle())
        callback = mocker.stub()
        r.onUpdateCall(callback)

        r.restore(
            [
                ("1.test", "test 1"),
                ("2.test", "test 2"),
            ]
        )

        assert len(r) == 2
        assert r[0].test.get() == "test 1"
        assert r[1].test.get() == "test 2"

        # Ensure that a restore only triggers one update notification.

        callback.assert_called_once_with(r)

    def test_restore_keys(self, mocker: MockerFixture):

        r: List[Key[str]] = List(Key(default=""))
        callback = mocker.stub()
        r.onUpdateCall(callback)

        r.restore(
            [
                ("1", "test 1"),
                ("2", "test 2"),
            ]
        )

        assert len(r) == 2
        assert r[0].get() == "test 1"
        assert r[1].get() == "test 2"

        # Ensure that a restore only triggers one update notification.

        callback.assert_called_once_with(r)

    def test_restore_order(self):

        r: List[Key[str]] = List(Key(default=""))
        r.restore(
            [
                ("5", "five"),
                ("3", "three"),
                ("1", "one 1"),  # will be overridden
                ("1", "one 2"),  # will be overridden
                ("2", "two"),
                ("1", "one 3"),
            ]
        )

        assert len(r) == 4
        assert r[0].get() == "one 3"
        assert r[1].get() == "two"
        assert r[2].get() == "three"
        assert r[3].get() == "five"

    def test_persistence(self):

        # A List does not keep a reference to its parent or children.

        bundle_list: List[Key[int]] = List(Key(default=0))
        level1: List[Key[int]] = List(Key(default=0))
        level1.setParent(bundle_list)
        level2: List[Key[int]] = List(Key(default=0))
        level2.setParent(level1)

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del bundle_list
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 0

    def test_update_callback_called_on_list_contents_changed(
        self, mocker: MockerFixture
    ):

        callback = mocker.stub()

        key_list: List[Key[int]] = List(Key(default=0))

        key_list.onUpdateCall(callback)

        key_list.appendOne()
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        key_list.append(Key(default=0))
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        key_list.insert(0, Key(default=0))
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        key_list[0] = Key(default=0)
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        key_list += [Key(default=0), Key(default=0), Key(default=0)]
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        key_list.extend([Key(default=0), Key(default=0), Key(default=0)])
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        key_list[2:4] = [
            Key(default=0),
            Key(default=0),
            Key(default=0),
        ]
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        key_list.pop()
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        s1 = key_list[0]
        key_list.remove(s1)
        assert s1 not in key_list
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        del key_list[0]
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        assert len(key_list[1:3]) == 2
        del key_list[1:3]
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

        assert len(key_list) > 1
        key_list.clear()
        callback.assert_called_once_with(key_list)
        callback.reset_mock()

    def test_update_callback_called_on_contained_item_update(
        self, mocker: MockerFixture
    ):

        callback = mocker.stub()

        bundle_list: List[ExampleBundle] = List(ExampleBundle())
        bundle_list.onUpdateCall(callback)

        s1 = ExampleBundle()
        bundle_list.append(s1)
        callback.reset_mock()
        s1.test.set("test")
        callback.assert_called_once_with(bundle_list)

        s2 = ExampleBundle()
        bundle_list.insert(0, s2)
        callback.reset_mock()
        s2.test.set("test")
        callback.assert_called_once_with(bundle_list)

        s3 = ExampleBundle()
        bundle_list[0] = s3
        callback.reset_mock()
        s3.test.set("test")
        callback.assert_called_once_with(bundle_list)

        s4 = ExampleBundle()
        s5 = ExampleBundle()
        bundle_list[1:2] = [s4, s5]
        callback.reset_mock()
        s4.test.set("test")
        callback.assert_called_once_with(bundle_list)
        callback.reset_mock()
        s5.test.set("test")
        callback.assert_called_once_with(bundle_list)

        s6 = ExampleBundle()
        s7 = ExampleBundle()
        bundle_list += [s6, s7]
        callback.reset_mock()
        s6.test.set("test")
        callback.assert_called_once_with(bundle_list)
        callback.reset_mock()
        s7.test.set("test")
        callback.assert_called_once_with(bundle_list)

        s8 = ExampleBundle()
        s9 = ExampleBundle()
        bundle_list.extend([s8, s9])
        callback.reset_mock()
        s8.test.set("test")
        callback.assert_called_once_with(bundle_list)
        callback.reset_mock()
        s9.test.set("test")
        callback.assert_called_once_with(bundle_list)

    def test_update_callback_not_called_for_removed_items(
        self, mocker: MockerFixture
    ):

        bundle_list: List[ExampleBundle] = List(ExampleBundle())

        s1 = ExampleBundle()
        s2 = ExampleBundle()

        callback = mocker.stub()
        bundle_list.onUpdateCall(callback)

        s1.test.clear()
        bundle_list[:] = [s1]
        del bundle_list[0]

        callback.reset_mock()
        s1.test.set("test")
        callback.assert_not_called()

        s1.test.clear()
        s2.test.clear()
        bundle_list[:] = [s1, s2]
        del bundle_list[0:2]

        callback.reset_mock()
        s1.test.set("test")
        s2.test.set("test")
        callback.assert_not_called()

        s1.test.clear()
        s2.test.clear()
        bundle_list[:] = [s1, s2]
        bundle_list.clear()

        callback.reset_mock()
        s1.test.set("test")
        s2.test.set("test")
        callback.assert_not_called()

        s1.test.clear()
        bundle_list[:] = [s1]
        bundle_list.pop()

        callback.reset_mock()
        s1.test.set("test")
        callback.assert_not_called()

        s1.test.clear()
        bundle_list[:] = [s1]
        bundle_list.remove(s1)
        assert s1 not in bundle_list

        callback.reset_mock()
        s1.test.set("test")
        callback.assert_not_called()

    def test_repr(self):

        parent = List(Key(default=0))
        list_iter_no_parent = List(Key(default=0), order=List.NO_PARENT)
        list_iter_parent_first = List(Key(default=0), order=List.PARENT_FIRST)
        list_iter_parent_last = List(Key(default=0), order=List.PARENT_LAST)

        list_iter_no_parent.setParent(parent)
        list_iter_parent_first.setParent(parent)
        list_iter_parent_last.setParent(parent)

        list_iter_no_parent.appendOne().set(1)
        list_iter_parent_first.appendOne().set(1)
        list_iter_parent_last.appendOne().set(1)

        assert repr(list_iter_no_parent) == "[<Key[int]:1>]"
        assert repr(list_iter_parent_first) == "[<parent>,<Key[int]:1>]"
        assert repr(list_iter_parent_last) == "[<Key[int]:1>,<parent>]"
