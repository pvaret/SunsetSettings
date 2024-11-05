from sunset import Bunch, Key, List, Settings


class ExampleBunch(Bunch):
    bunch_key = Key(default=0)


class ExampleSettings(Settings):
    inner_bunch = ExampleBunch()
    bunch_list = List(ExampleBunch())
    key_list = List(Key(default=""))
    key = Key(default="")


class TestMetadata:
    def test_key_label(self) -> None:
        class TestBunch(Bunch):
            key1 = Key("test")
            key2 = Key("test")

        bunch = TestBunch()
        assert bunch.key1.meta().label == "key1"
        assert bunch.key2.meta().label == "key2"

        key = Key("test")
        assert key.meta().label == ""

    def test_bunch_field_label(self) -> None:
        bunch = ExampleBunch()

        assert bunch.meta().label == ""
        assert bunch.bunch_key.meta().label == "bunch_key"

        settings = ExampleSettings()

        assert settings.meta().label == ""
        assert settings.inner_bunch.meta().label == "inner_bunch"
        assert settings.inner_bunch.bunch_key.meta().label == "bunch_key"

    def test_label_set_on_contained_list_items(self) -> None:
        # Testing List.appendOne()

        key_list = List(Key(""))
        key = key_list.appendOne()
        assert key.meta().label == "1"

        # Testing List.insertOne()

        other_key = key_list.insertOne(0)
        assert other_key.meta().label == "1"
        assert key.meta().label == "2"

        # Testing List.append()

        key = Key("")
        assert key.meta().label == ""
        key_list.append(key)
        assert key.meta().label == "3"

        # Testing List.extend()

        key = Key("")
        last_key = Key("")
        key_list.extend((key, last_key))
        assert key.meta().label == "4"
        assert last_key.meta().label == "5"

        # Testing List.insert()

        key = Key("")
        key_list.insert(3, key)
        assert key.meta().label == "4"
        assert last_key.meta().label == "6"

        # Testing List.__setitem__(index)

        key = Key("")
        key_list[2] = key
        assert key.meta().label == "3"
        assert last_key.meta().label == "6"

        # Testing List.__setitem__(slice)

        key = Key("")
        other_key = Key("")
        key_list[1:4] = [key, other_key]
        assert key.meta().label == "2"
        assert other_key.meta().label == "3"
        assert last_key.meta().label == "5"

        # Testing List.__iadd__()

        key = Key("")
        other_key = Key("")
        key_list += [key, other_key]
        assert key.meta().label == "6"
        assert other_key.meta().label == "7"

        # Testing assignment order

        key_list[2], key_list[4] = key_list[4], key_list[2]
        assert key_list[2].meta().label == "3"
        assert key_list[4].meta().label == "5"

    def test_label_unset_on_removed_list_items(self) -> None:
        key_list = List(Key(""))
        for _ in range(15):
            key_list.appendOne()

        # Test List.__delitem__(index)

        key = key_list[3]
        assert key.meta().label == "4"
        del key_list[3]
        assert key.meta().label == ""

        # Test List.__delitem__(slice)

        keys = key_list[2:5]
        assert [key.meta().label for key in keys] == ["3", "4", "5"]
        del key_list[2:5]
        assert [key.meta().label for key in keys] == ["", "", ""]

        # Test List.__setitem__(index)

        key = key_list[5]
        assert key.meta().label == "6"
        key_list[5] = Key("")
        assert key.meta().label == ""

        # Test List.__setitem__(slice)

        keys = key_list[4:7]
        assert [key.meta().label for key in keys] == ["5", "6", "7"]
        key_list[4:7] = [Key(""), Key("")]
        assert [key.meta().label for key in keys] == ["", "", ""]

        # Test List.pop()

        last_key = key_list[9]
        assert last_key.meta().label == "10"
        key_list.pop()
        assert last_key.meta().label == ""

        # Test List.clear()

        keys = key_list[:]
        key_list.clear()
        assert all(key.meta().label == "" for key in keys)

    def test_paths(self) -> None:
        settings = ExampleSettings()

        assert settings.meta().path() == ""
        assert settings.inner_bunch.meta().path() == "inner_bunch"
        assert settings.inner_bunch.bunch_key.meta().path() == "inner_bunch.bunch_key"

        settings.bunch_list.appendOne()  # 1
        settings.bunch_list.appendOne()  # 2
        bunch = settings.bunch_list.appendOne()  # 3

        assert bunch.meta().path() == "bunch_list.3"
