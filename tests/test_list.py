from collections.abc import Iterable

from pytest_mock import MockerFixture

from sunset import Bunch, Key, List, protocols


class ExampleBunch(Bunch):
    test = Key("")


class TestList:
    def test_protocol_implementation(self) -> None:
        list_key: List[Key[int]] = List(Key(default=0))
        assert isinstance(list_key, protocols.Field)

    def test_add_pop(self) -> None:
        list_key: List[Key[str]] = List(Key(default=""))
        list_key.appendOne()

        assert len(list_key) == 1

        list_key[0].set("test")
        assert list_key[0].get() == "test"

        list_key.pop()

        assert len(list_key) == 0

    def test_inheritance(self) -> None:
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

    def test_reparenting(self) -> None:
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

    def test_iter_inheritance(self) -> None:
        def flatten(keys: Iterable[Key[str]]) -> list[str]:
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

    def test_dump_fields(self) -> None:
        key_list = List(Key(""))
        key_list.appendOne().set("test 1")
        key_list.appendOne()
        key_list.appendOne().set("test 3")
        assert list(key_list.dumpFields()) == [
            ("1", "test 1"),
            ("2", None),
            ("3", "test 3"),
        ]

        bunch_list = List(ExampleBunch())
        bunch_list.appendOne().test.set("test 1")
        bunch_list.appendOne()
        bunch_list.appendOne().test.set("test 3")
        bunch_list.appendOne()
        assert list(bunch_list.dumpFields()) == [
            ("1.test", "test 1"),
            ("2", None),
            ("3.test", "test 3"),
            ("4", None),
        ]

        key_list = List(Key(""))
        key_list.appendOne()
        key_list.appendOne().set("")
        key_list.appendOne()
        assert list(key_list.dumpFields()) == [
            ("1", None),
            ("2", ""),
            ("3", None),
        ]

        class TestBunch(Bunch):
            key_list = List(Key(""))
            _private = List(Key(""))

        bunch = TestBunch()
        bunch.key_list.appendOne().set("test public")
        bunch._private.appendOne().set("test private")
        assert list(bunch.dumpFields()) == [
            ("key_list.1", "test public"),
        ]

    def test_restore_field_with_valid_inputs(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()
        test_list = List(Key("default"))
        test_list.onUpdateCall(callback)

        # Test restoring one value. Also, restoring a field should not trigger a
        # callback.

        assert test_list.restoreFields([("1", "test")])
        assert len(test_list) == 1
        assert test_list[0].get() == "test"
        callback.assert_not_called()

        # Test overwriting a restored value.

        assert test_list.restoreFields([("1", "other test")])
        assert len(test_list) == 1
        assert test_list[0].get() == "other test"
        callback.assert_not_called()

        # Test restoring a value that requires extending the List.

        assert test_list.restoreFields([("5", "extension test")])
        assert len(test_list) == 5
        assert test_list[4].get() == "extension test"
        callback.assert_not_called()

        # Test indirect restore path.

        class TestBunch(Bunch):
            str_list = List(Key("default"))

        bunch = TestBunch()
        bunch.str_list.onUpdateCall(callback)
        assert bunch.restoreFields([("str_list.1", "test")])
        assert len(bunch.str_list) == 1
        assert bunch.str_list[0].get() == "test"
        callback.assert_not_called()

        # Test restoring a List with empty items.

        assert test_list.restoreFields([("2", ""), ("3", None)])
        assert len(test_list) == 3
        assert not test_list[0].isSet()
        assert test_list[1].isSet() and test_list[1].get() == ""
        assert not test_list[2].isSet()
        callback.assert_not_called()

        # Test overwriting a List with empty items.

        assert test_list.restoreFields(
            [("1", "test"), ("2", "test"), ("3", "test"), ("4", "test")]
        )
        assert len(test_list) == 4
        assert test_list[0].get() == "test"
        assert test_list[1].get() == "test"
        assert test_list[2].get() == "test"
        assert test_list[3].get() == "test"

        assert test_list.restoreFields([("2", ""), ("3", None)])
        assert len(test_list) == 3
        assert not test_list[0].isSet()
        assert test_list[1].isSet() and test_list[1].get() == ""
        assert not test_list[2].isSet()
        callback.assert_not_called()

    def test_restore_field_with_invalid_inputs(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()
        test_list = List(Key("default"))
        test_list.onUpdateCall(callback)

        # Test different kinds of invalid restore paths.

        assert not test_list.restoreFields([("", "test")])
        assert len(test_list) == 0
        callback.assert_not_called()

        assert not test_list.restoreFields([("invalid", "test")])
        assert len(test_list) == 0
        callback.assert_not_called()

        assert not test_list.restoreFields([("invalid.1", "test")])
        assert len(test_list) == 0
        callback.assert_not_called()

        assert not test_list.restoreFields([(".", "test")])
        assert len(test_list) == 0
        callback.assert_not_called()

        assert not test_list.restoreFields([("0", "test")])
        assert len(test_list) == 0
        callback.assert_not_called()

    def test_persistence(self) -> None:
        # A List does not keep a reference to its parent or children.

        bunch_list: List[Key[int]] = List(Key(default=0))
        level1: List[Key[int]] = List(Key(default=0))
        level1.setParent(bunch_list)
        level2: List[Key[int]] = List(Key(default=0))
        level2.setParent(level1)

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del bunch_list
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 0

    def test_callback_type_is_flexible(self) -> None:
        key_list = List(Key(""))

        class Dummy:
            pass

        def callback(_: List[Key[str]]) -> Dummy: ...

        key_list.onUpdateCall(callback)

    def test_update_callback_called_on_list_contents_changed(
        self, mocker: MockerFixture
    ) -> None:
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
    ) -> None:
        callback = mocker.stub()

        bunch_list: List[ExampleBunch] = List(ExampleBunch())
        bunch_list.onUpdateCall(callback)

        bunch1 = ExampleBunch()
        bunch_list.append(bunch1)
        callback.reset_mock()
        bunch1.test.set("test")
        callback.assert_called_once_with(bunch1.test)

        bunch2 = ExampleBunch()
        bunch_list.insert(0, bunch2)
        callback.reset_mock()
        bunch2.test.set("test")
        callback.assert_called_once_with(bunch2.test)

        bunch3 = ExampleBunch()
        bunch_list[0] = bunch3
        callback.reset_mock()
        bunch3.test.set("test")
        callback.assert_called_once_with(bunch3.test)

        bunch4 = ExampleBunch()
        bunch5 = ExampleBunch()
        bunch_list[1:2] = [bunch4, bunch5]
        callback.reset_mock()
        bunch4.test.set("test")
        callback.assert_called_once_with(bunch4.test)
        callback.reset_mock()
        bunch5.test.set("test")
        callback.assert_called_once_with(bunch5.test)

        bunch6 = ExampleBunch()
        bunch7 = ExampleBunch()
        bunch_list += [bunch6, bunch7]
        callback.reset_mock()
        bunch6.test.set("test")
        callback.assert_called_once_with(bunch6.test)
        callback.reset_mock()
        bunch7.test.set("test")
        callback.assert_called_once_with(bunch7.test)

        bunch8 = ExampleBunch()
        bunch9 = ExampleBunch()
        bunch_list.extend([bunch8, bunch9])
        callback.reset_mock()
        bunch8.test.set("test")
        callback.assert_called_once_with(bunch8.test)
        callback.reset_mock()
        bunch9.test.set("test")
        callback.assert_called_once_with(bunch9.test)

    def test_update_callback_not_called_for_removed_items(
        self, mocker: MockerFixture
    ) -> None:
        bunch_list: List[ExampleBunch] = List(ExampleBunch())

        bunch1 = ExampleBunch()
        bunch2 = ExampleBunch()

        callback = mocker.stub()
        bunch_list.onUpdateCall(callback)

        bunch1.test.clear()
        bunch_list[:] = [bunch1]
        del bunch_list[0]

        callback.reset_mock()
        bunch1.test.set("test")
        callback.assert_not_called()

        bunch1.test.clear()
        bunch2.test.clear()
        bunch_list[:] = [bunch1, bunch2]
        del bunch_list[0:2]

        callback.reset_mock()
        bunch1.test.set("test")
        bunch2.test.set("test")
        callback.assert_not_called()

        bunch1.test.clear()
        bunch2.test.clear()
        bunch_list[:] = [bunch1, bunch2]
        bunch_list.clear()

        callback.reset_mock()
        bunch1.test.set("test")
        bunch2.test.set("test")
        callback.assert_not_called()

        bunch1.test.clear()
        bunch_list[:] = [bunch1]
        bunch_list.pop()

        callback.reset_mock()
        bunch1.test.set("test")
        callback.assert_not_called()

        bunch1.test.clear()
        bunch_list[:] = [bunch1]
        bunch_list.remove(bunch1)
        assert bunch1 not in bunch_list

        callback.reset_mock()
        bunch1.test.set("test")
        callback.assert_not_called()

    def test_repr(self) -> None:
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
