from typing import Iterator

from pytest_mock import MockerFixture

from sunset import Bundle, Key, List, protocols


class ExampleBundle(Bundle):

    test = Key("")


class TestList:
    def test_protocol_implementation(self):

        list_key: List[Key[int]] = List(Key(default=0))
        assert isinstance(list_key, protocols.Inheriter)
        assert isinstance(list_key, protocols.ItemTemplate)
        assert isinstance(list_key, protocols.Dumpable)
        assert isinstance(list_key, protocols.Restorable)

    def test_add_pop(self):

        list_key: List[Key[str]] = List(Key(default=""))
        list_key.appendOne()

        assert len(list_key) == 1

        list_key[0].set("test")
        assert list_key[0].get() == "test"

        list_key.pop()

        assert len(list_key) == 0

    def test_inheritance(self):

        parent_list: List[Key[int]] = List(Key(default=0))
        child_list: List[Key[int]] = List(Key(default=0))

        assert child_list not in parent_list.children()
        assert child_list.parent() is None

        child_list.setParent(parent_list)
        assert child_list in parent_list.children()
        assert child_list.parent() is parent_list

        child_list.setParent(None)
        assert child_list not in parent_list.children()
        assert child_list.parent() is None

    def test_reparenting(self):

        list1: List[Key[int]] = List(Key(default=0))
        list2: List[Key[int]] = List(Key(default=0))
        child_list: List[Key[int]] = List(Key(default=0))

        assert child_list not in list1.children()
        assert child_list not in list2.children()
        assert child_list.parent() is None

        child_list.setParent(list1)
        assert child_list in list1.children()
        assert child_list not in list2.children()
        assert child_list.parent() is list1

        child_list.setParent(list2)
        assert child_list not in list1.children()
        assert child_list in list2.children()
        assert child_list.parent() is list2

        child_list.setParent(None)
        assert child_list not in list1.children()
        assert child_list not in list2.children()
        assert child_list.parent() is None

    def test_iter_inheritance(self):
        def flatten(keys: Iterator[Key[str]]) -> list[str]:
            return [key.get() for key in keys]

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

        bundle_list: List[ExampleBundle] = List(ExampleBundle())

        assert bundle_list.dump() == []

        bundle_list.appendOne().test.set("test 1")
        bundle_list.appendOne().test.set("test 2")

        assert bundle_list.dump() == [
            ("1.test", "test 1"),
            ("2.test", "test 2"),
        ]

    def test_dump_keys(self):

        key_list: List[Key[str]] = List(Key(default=""))

        assert key_list.dump() == []

        key_list.appendOne().set("test 1")
        key_list.appendOne().set("test 2")

        assert key_list.dump() == [
            ("1", "test 1"),
            ("2", "test 2"),
        ]

    def test_restore_bundles(self, mocker: MockerFixture):

        bundle_list: List[ExampleBundle] = List(ExampleBundle())
        callback = mocker.stub()
        bundle_list.onUpdateCall(callback)

        bundle_list.restore(
            [
                ("1.test", "test 1"),
                ("2.test", "test 2"),
            ]
        )

        assert len(bundle_list) == 2
        assert bundle_list[0].test.get() == "test 1"
        assert bundle_list[1].test.get() == "test 2"

        # Ensure that a restore only triggers one update notification.

        callback.assert_called_once_with(bundle_list)

    def test_restore_keys(self, mocker: MockerFixture):

        key_list: List[Key[str]] = List(Key(default=""))
        callback = mocker.stub()
        key_list.onUpdateCall(callback)

        key_list.restore(
            [
                ("1", "test 1"),
                ("2", "test 2"),
            ]
        )

        assert len(key_list) == 2
        assert key_list[0].get() == "test 1"
        assert key_list[1].get() == "test 2"

        # Ensure that a restore only triggers one update notification.

        callback.assert_called_once_with(key_list)

    def test_restore_order(self):

        key_list: List[Key[str]] = List(Key(default=""))
        key_list.restore(
            [
                ("5", "five"),
                ("3", "three"),
                ("1", "one 1"),  # will be overridden
                ("1", "one 2"),  # will be overridden
                ("2", "two"),
                ("1", "one 3"),
            ]
        )

        assert len(key_list) == 4
        assert key_list[0].get() == "one 3"
        assert key_list[1].get() == "two"
        assert key_list[2].get() == "three"
        assert key_list[3].get() == "five"

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

        key = key_list[0]
        key_list.remove(key)
        assert key not in key_list
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

        bundle1 = ExampleBundle()
        bundle_list.append(bundle1)
        callback.reset_mock()
        bundle1.test.set("test")
        callback.assert_called_once_with(bundle_list)

        bundle2 = ExampleBundle()
        bundle_list.insert(0, bundle2)
        callback.reset_mock()
        bundle2.test.set("test")
        callback.assert_called_once_with(bundle_list)

        bundle3 = ExampleBundle()
        bundle_list[0] = bundle3
        callback.reset_mock()
        bundle3.test.set("test")
        callback.assert_called_once_with(bundle_list)

        bundle4 = ExampleBundle()
        bundle5 = ExampleBundle()
        bundle_list[1:2] = [bundle4, bundle5]
        callback.reset_mock()
        bundle4.test.set("test")
        callback.assert_called_once_with(bundle_list)
        callback.reset_mock()
        bundle5.test.set("test")
        callback.assert_called_once_with(bundle_list)

        bundle6 = ExampleBundle()
        bundle7 = ExampleBundle()
        bundle_list += [bundle6, bundle7]
        callback.reset_mock()
        bundle6.test.set("test")
        callback.assert_called_once_with(bundle_list)
        callback.reset_mock()
        bundle7.test.set("test")
        callback.assert_called_once_with(bundle_list)

        bundle8 = ExampleBundle()
        bundle9 = ExampleBundle()
        bundle_list.extend([bundle8, bundle9])
        callback.reset_mock()
        bundle8.test.set("test")
        callback.assert_called_once_with(bundle_list)
        callback.reset_mock()
        bundle9.test.set("test")
        callback.assert_called_once_with(bundle_list)

    def test_update_callback_not_called_for_removed_items(
        self, mocker: MockerFixture
    ):

        bundle_list: List[ExampleBundle] = List(ExampleBundle())

        bundle1 = ExampleBundle()
        bundle2 = ExampleBundle()

        callback = mocker.stub()
        bundle_list.onUpdateCall(callback)

        bundle1.test.clear()
        bundle_list[:] = [bundle1]
        del bundle_list[0]

        callback.reset_mock()
        bundle1.test.set("test")
        callback.assert_not_called()

        bundle1.test.clear()
        bundle2.test.clear()
        bundle_list[:] = [bundle1, bundle2]
        del bundle_list[0:2]

        callback.reset_mock()
        bundle1.test.set("test")
        bundle2.test.set("test")
        callback.assert_not_called()

        bundle1.test.clear()
        bundle2.test.clear()
        bundle_list[:] = [bundle1, bundle2]
        bundle_list.clear()

        callback.reset_mock()
        bundle1.test.set("test")
        bundle2.test.set("test")
        callback.assert_not_called()

        bundle1.test.clear()
        bundle_list[:] = [bundle1]
        bundle_list.pop()

        callback.reset_mock()
        bundle1.test.set("test")
        callback.assert_not_called()

        bundle1.test.clear()
        bundle_list[:] = [bundle1]
        bundle_list.remove(bundle1)
        assert bundle1 not in bundle_list

        callback.reset_mock()
        bundle1.test.set("test")
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
