import warnings
import io
import logging
import textwrap

from pytest_mock import MockerFixture

from sunset import Bunch, Key, List, Settings, normalize


def test_normalize() -> None:
    assert normalize("") == ""
    assert normalize("     ") == ""
    assert normalize("  A  B  ") == "ab"
    assert normalize("(a):?/b") == "ab"
    assert normalize("a-b_c") == "a-b_c"


class ExampleSettings(Settings):
    class ExampleBunch(Bunch):
        c = Key(default=0)
        d = Key(default=False)

    inner_bunch = ExampleBunch()
    bunch_list = List(ExampleBunch())
    key_list = List(Key(default=""))

    a = Key(default="")
    b = Key(default="")


class TestSettings:
    def test_new_named_layer(self) -> None:
        settings = ExampleSettings()

        assert len(list(settings.layers())) == 0

        layer = settings.addLayer(name="same name")
        assert len(list(settings.layers())) == 1

        otherlayer = settings.getOrAddLayer(name="same name")
        assert len(list(settings.layers())) == 1

        assert otherlayer is layer

    def test_dump_fields(self) -> None:
        # When no field is set, the layer should still be dumped.

        settings = ExampleSettings()
        assert list(settings.dumpFields()) == [
            ("", None),
        ]

        # This applies to layers too.

        settings.addLayer("empty")
        assert list(settings.dumpFields()) == [
            ("", None),
            ("empty/", None),
        ]

        # Set fields should be dumped, in alphabetic order.

        settings = ExampleSettings()
        settings.b.set("new b")
        settings.a.set("new a")
        settings.inner_bunch.c.set(40)
        settings.inner_bunch.d.set(True)
        settings.bunch_list.appendOne().c.set(100)
        settings.bunch_list.appendOne().d.set(True)
        settings.key_list.appendOne().set("one")
        settings.key_list.appendOne()
        settings.key_list.appendOne().set("three")
        assert list(settings.dumpFields()) == [
            ("a", "new a"),
            ("b", "new b"),
            ("bunch_list.1.c", "100"),
            ("bunch_list.2.d", "true"),
            ("inner_bunch.c", "40"),
            ("inner_bunch.d", "true"),
            ("key_list.1", "one"),
            ("key_list.2", None),
            ("key_list.3", "three"),
        ]

        # Anonymous layers, and layers of anonymous layers, should not
        # be dumped.

        settings = ExampleSettings()
        settings.a.set("a")
        settings.bunch_list.appendOne().c.set(100)

        layer1 = settings.addLayer(name="Layer 1")
        layer1.a.set("sub a")
        layer1.b.set("sub b")
        layer1.bunch_list.appendOne().c.set(1000)

        layer2 = settings.addLayer(name="Layer 2")
        layer2.inner_bunch.d.set(False)

        anonymous = settings.addLayer()
        anonymous.a.set("anonymous")

        subanonymous = anonymous.addLayer(name="Should be ignored too")
        subanonymous.b.set("anonymous 2")

        layer = layer1.addLayer(name="layer")
        layer.inner_bunch.c.set(200)

        assert list(settings.dumpFields()) == [
            ("a", "a"),
            ("bunch_list.1.c", "100"),
            ("layer1/a", "sub a"),
            ("layer1/b", "sub b"),
            ("layer1/bunch_list.1.c", "1000"),
            ("layer1/layer/inner_bunch.c", "200"),
            ("layer2/inner_bunch.d", "false"),
        ]

        # Layer should be dumped in alphabetic order.

        settings = ExampleSettings()
        settings.addLayer("z")
        settings.addLayer("mm")
        settings.addLayer("aaa")
        assert list(settings.dumpFields()) == [
            ("", None),
            ("aaa/", None),
            ("mm/", None),
            ("z/", None),
        ]

    def test_restore_field(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        # Test restorting a field. As well, restoring a field should not trigger
        # a callback.

        settings = ExampleSettings()
        settings.onUpdateCall(callback)
        assert settings.a.get() == ""
        assert settings.restoreFields([("a", "test main a")])
        assert settings.a.get() == "test main a"
        callback.assert_not_called()

        # Test restoring a field on an inner Bunch.

        assert settings.inner_bunch.c.get() == 0
        assert settings.restoreFields([("inner_bunch.c", "123")])
        assert settings.inner_bunch.c.get() == 123
        callback.assert_not_called()

        # Test restoring a field on a layer.

        assert settings.getLayer("layer1") is None
        assert settings.restoreFields([("layer1/a", "test layer1 a")])
        layer1 = settings.getLayer("layer1")
        assert layer1 is not None
        assert layer1.a.get() == "test layer1 a"
        callback.assert_not_called()

        assert settings.restoreFields([("layer2/layer/a", "test layer a")])
        layer2 = settings.getLayer("layer2")
        assert layer2 is not None
        layer = layer2.getLayer("layer")
        assert layer is not None
        assert layer.a.get() == "test layer a"
        callback.assert_not_called()

        # Test restorting with an invalid path.

        other_settings = ExampleSettings()
        other_settings.onUpdateCall(callback)
        assert not other_settings.isSet()
        assert not other_settings.restoreFields([("/a", "test invalid a")])
        assert not other_settings.isSet()
        callback.assert_not_called()

        assert not other_settings.restoreFields([("/invalid/a", "test invalid a")])
        assert not other_settings.isSet()
        callback.assert_not_called()

        assert not other_settings.restoreFields([("/", "test invalid a")])
        assert not other_settings.isSet()
        callback.assert_not_called()

        assert not other_settings.restoreFields([("", "test invalid a")])
        assert not other_settings.isSet()
        callback.assert_not_called()

    def test_persistence(self) -> None:
        # Settings keep a reference to their layers, but not to their parent.

        settings = ExampleSettings()
        level1 = settings.addLayer(name="level 1")
        level2 = level1.addLayer(name="level 2")

        assert level1.parent() is not None
        assert len(list(level1.layers())) == 1

        del settings
        del level2
        assert level1.parent() is None
        assert len(list(level1.layers())) == 1

    def test_save(self) -> None:
        settings = ExampleSettings()
        settings.a.set("a")
        settings.bunch_list.appendOne().c.set(100)

        layer1 = settings.addLayer(name="Level 1")
        layer1.a.set("sub a")
        layer1.b.set("sub b")
        layer1.bunch_list.appendOne().c.set(1000)
        layer1.key_list.appendOne().set("one")
        layer1.key_list.appendOne()
        layer1.key_list.appendOne().set("")

        layer2 = settings.addLayer(name="Other level 1")
        layer2.inner_bunch.d.set(False)

        anonymous = settings.addLayer()
        anonymous.a.set("anonymous")

        subanonymous = anonymous.addLayer(name="Should be ignored too")
        subanonymous.b.set("anonymous 2")

        layer1 = layer1.addLayer(name="Level 2")
        layer1.inner_bunch.c.set(200)

        settings.addLayer("empty")

        file = io.StringIO()
        settings.save(file, blanklines=True)

        assert file.getvalue() == textwrap.dedent(
            """\
            [main]
            a = a
            bunch_list.1.c = 100

            [empty]

            [level1]
            a = sub a
            b = sub b
            bunch_list.1.c = 1000
            key_list.1 = one
            key_list.2 =
            key_list.3 = ""

            [level1/level2]
            inner_bunch.c = 200

            [otherlevel1]
            inner_bunch.d = false
            """
        )

    def test_load_to_save_idempotency(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                a = a
                bunch_list.1.c = 100

                [level1]
                a = sub a
                b = sub b
                bunch_list.1.c = 1000
                key_list.1 = one
                key_list.2 =
                key_list.3 = ""

                [level1/level2]
                inner_bunch.c = 200

                [otherlevel1]
                inner_bunch.d = false
                """
            )
        )

        file = io.StringIO()
        settings.save(file, blanklines=True)

        assert file.getvalue() == textwrap.dedent(
            """\
            [main]
            a = a
            bunch_list.1.c = 100

            [level1]
            a = sub a
            b = sub b
            bunch_list.1.c = 1000
            key_list.1 = one
            key_list.2 =
            key_list.3 = ""

            [level1/level2]
            inner_bunch.c = 200

            [otherlevel1]
            inner_bunch.d = false
            """
        )

    def test_dump_to_restore_idempotency(self) -> None:
        settings = ExampleSettings()
        settings.a.set("a")
        settings.bunch_list.appendOne().c.set(100)

        layer1 = settings.addLayer(name="Level 1")
        layer1.a.set("sub a")
        layer1.b.set("sub b")
        layer1.bunch_list.appendOne().c.set(1000)
        layer1.key_list.appendOne().set("one")
        layer1.key_list.appendOne()
        layer1.key_list.appendOne().set("")

        layer2 = settings.addLayer(name="Other level 1")
        layer2.inner_bunch.d.set(False)

        layer1 = layer1.addLayer(name="Level 2")
        layer1.inner_bunch.c.set(200)

        expected_fields: list[tuple[str, str | None]] = [
            ("a", "a"),
            ("bunch_list.1.c", "100"),
            ("level1/a", "sub a"),
            ("level1/b", "sub b"),
            ("level1/bunch_list.1.c", "1000"),
            ("level1/key_list.1", "one"),
            ("level1/key_list.2", None),
            ("level1/key_list.3", ""),
            ("level1/level2/inner_bunch.c", "200"),
            ("otherlevel1/inner_bunch.d", "false"),
        ]
        assert list(settings.dumpFields()) == expected_fields

        restored = ExampleSettings()
        restored.restoreFields(expected_fields)
        assert list(restored.dumpFields()) == expected_fields

        restored.restoreFields(expected_fields)
        assert list(restored.dumpFields()) == expected_fields

    def test_save_non_default_toplevel_layer_name(self) -> None:
        settings = ExampleSettings()
        settings.setLayerName("renamed")
        settings.a.set("a")
        settings.bunch_list.appendOne().c.set(100)

        layer1 = settings.addLayer(name="Level 1")
        layer1.b.set("sub b")
        layer1.addLayer("Level 2")

        file = io.StringIO()
        settings.save(file, blanklines=True)

        assert file.getvalue() == textwrap.dedent(
            """\
            [renamed]
            a = a
            bunch_list.1.c = 100

            [level1]
            b = sub b

            [level1/level2]
            """
        )

    def test_deprecated_section_methods(self) -> None:
        settings = ExampleSettings()

        with warnings.catch_warnings(record=True) as w:
            layer = settings.newSection()
            assert len(w) == 1
            assert settings.sections() == [layer]
            assert len(w) == 2
            layer.setSectionName("test")
            assert len(w) == 3
            assert layer.sectionName() == "test"
            assert len(w) == 4
            assert settings.getOrCreateSection("test") is layer
            assert len(w) == 5
            assert settings.getSection("test") is layer
            assert len(w) == 6
            assert all(warning.category is DeprecationWarning for warning in w)

    def test_load(self, mocker: MockerFixture) -> None:
        settings = ExampleSettings()
        callback = mocker.stub()
        settings.onUpdateCall(callback)
        settings.load(
            io.StringIO(
                """\
                [main]
                a = a
                bunch_list.1.c = 100

                [level1]
                a = sub a
                b = sub b
                key_list.1 = one
                key_list.2 =
                key_list.3 = ""
                bunch_list.1.c = 1000

                [level1/level2]
                inner_bunch.c = 200

                [otherlevel1]
                inner_bunch.d = false
                """
            )
        )

        callback.assert_not_called()

        assert settings.a.get() == "a"
        assert len(settings.bunch_list) == 1
        assert settings.bunch_list[0].c.get() == 100

        settings_layers = {s.layerName(): s for s in settings.layers()}
        assert len(settings_layers) == 2
        assert "level1" in settings_layers
        level1 = settings_layers["level1"]
        assert "otherlevel1" in settings_layers
        otherlevel1 = settings_layers["otherlevel1"]

        assert level1.a.get() == "sub a"
        assert level1.b.get() == "sub b"
        assert len(level1.bunch_list) == 1
        assert level1.bunch_list[0].c.get() == 1000
        assert len(level1.key_list) == 3
        assert level1.key_list[0].get() == "one"
        assert not level1.key_list[1].isSet()
        assert level1.key_list[2].isSet() and level1.key_list[2].get() == ""

        assert not otherlevel1.inner_bunch.d.get()

        level1_layers = {s.layerName(): s for s in level1.layers()}
        assert len(level1_layers) == 1
        assert "level2" in level1_layers
        level2 = level1_layers["level2"]

        assert level2.inner_bunch.c.get() == 200

    def test_load_no_layer_means_main(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                a = no main layer
                """
            )
        )

        assert settings.a.get() == "no main layer"

    def test_load_invalid_repeated_key(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                a = repeated key
                a = first value should be used
                """
            )
        )

        assert settings.a.get() == "repeated key"

    def test_load_repeated_layers_are_merged(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                a = repeated layer

                [main]
                a = layer values will be merged, first takes precedence
                b = merged value
                """
            )
        )

        assert settings.a.get() == "repeated layer"
        assert settings.b.get() == "merged value"

    def test_load_layers_valid_when_missing_main(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [level1]
                a = main layer is implicitly created if needed
                """
            )
        )

        layers = list(settings.layers())
        assert len(layers) == 1
        assert layers[0].a.get() == "main layer is implicitly created if needed"

    def test_load_invalid_extra_layer_separators(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                [level1///level2]
                a = extra separators should be skipped
                """
            )
        )

        layers = list(settings.layers())
        assert len(layers) == 1
        layers = list(layers[0].layers())
        assert len(layers) == 1
        assert layers[0].a.get() == "extra separators should be skipped"

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                [/level1]
                a = extra separators should be skipped
                """
            )
        )

        layers = list(settings.layers())
        assert len(layers) == 1
        assert layers[0].a.get() == "extra separators should be skipped"

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                [level1/]
                a = extra separators should be skipped
                """
            )
        )

        layers = list(settings.layers())
        assert len(layers) == 1
        assert layers[0].a.get() == "extra separators should be skipped"

    def test_load_invalid_bad_layer_is_skipped(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                a = main

                [!%$?]
                a = bad bunch
                """
            )
        )

        layers = list(settings.layers())
        assert len(layers) == 0
        assert settings.a.get() == "main"

    def test_load_invalid_similar_are_merged(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                a = main

                [ M? a*i*n ]
                a = first entry still prevails
                b = merged
                """
            )
        )

        layers = list(settings.layers())
        assert len(layers) == 0
        assert settings.a.get() == "main"
        assert settings.b.get() == "merged"

    def test_load_invalid_empty_layer_is_skipped(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                a = main

                []
                a = skipped
                """
            )
        )

        layers = list(settings.layers())
        assert len(layers) == 0
        assert settings.a.get() == "main"

    def test_load_bad_key(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                = should be skipped
                """
            )
        )

        assert not settings.isSet()

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                ??a = should be loaded
                """
            )
        )

        assert settings.a.get() == "should be loaded"

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                [a] = should be loaded
                """
            )
        )

        assert settings.a.get() == "should be loaded"

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                doesnotexist = should be skipped
                """
            )
        )

        assert not settings.isSet()

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                . = should be skipped
                """
            )
        )

        assert not settings.isSet()

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                .a = should be loaded
                """
            )
        )

        assert settings.a.get() == "should be loaded"

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                a.. = should be loaded
                """
            )
        )

        assert settings.a.get() == "should be loaded"

    def test_load_layers_created_even_if_empty(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [shouldexist]
                """
            )
        )
        assert settings.getLayer("shouldexist") is not None

    def test_load_renamed_settings(self) -> None:
        settings = ExampleSettings()
        settings.setLayerName("renamed")

        settings.load(
            io.StringIO(
                """\
                [renamed]
                a = value
                """
            )
        )

        assert settings.a.get() == "value"

    def test_autosave(self, mocker: MockerFixture) -> None:
        sentinel = object()
        autosaver_stub = mocker.Mock(return_value=sentinel)
        logger_stub = mocker.Mock(logging.Logger)

        settings = ExampleSettings()
        settings._autosaver_class = autosaver_stub
        ret = settings.autosave(
            "/tmp/test",
            save_delay=12,
            raise_on_error=True,
            logger=logger_stub,
        )

        assert ret is sentinel

        autosaver_stub.assert_called_once_with(
            settings,
            "/tmp/test",
            save_delay=12,
            save_on_update=True,
            raise_on_error=True,
            logger=logger_stub,
        )

    def test_callback_type_is_flexible(self) -> None:
        settings = ExampleSettings()

        class Dummy:
            pass

        def callback(_: ExampleSettings) -> Dummy:
            return Dummy()

        settings.onUpdateCall(callback)

    def test_key_updated_notification(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        settings = ExampleSettings()
        settings.onUpdateCall(callback)

        settings.a.set("test 1")
        callback.assert_called_once_with(settings.a)
        callback.reset_mock()

        layer = settings.addLayer(name="layer")
        callback.assert_called_once_with(settings)
        callback.reset_mock()

        layer.a.set("test 2")
        callback.assert_called_once_with(layer.a)
        callback.reset_mock()

        anonymous = settings.addLayer()
        callback.assert_called_once_with(settings)
        callback.reset_mock()

        anonymous.a.set("test 3")
        callback.assert_called_once_with(anonymous.a)
        callback.reset_mock()

        anonymouslayer = anonymous.addLayer(name="other layer")
        callback.assert_called_once_with(anonymous)
        callback.reset_mock()

        anonymouslayer.a.set("test 4")
        callback.assert_called_once_with(anonymouslayer.a)
        callback.reset_mock()

        anonymous.setLayerName("no longer anonymous")
        callback.assert_called_once_with(anonymous)
        callback.reset_mock()

    def test_setting_same_layer_name_doesnt_notify(self, mocker: MockerFixture) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()

        layer = parent.addLayer("test")

        layer.onUpdateCall(callback := mocker.stub())

        layer.setLayerName("test")
        callback.assert_not_called()

        layer.setLayerName("")
        callback.assert_called_once_with(layer)
        callback.reset_mock()

        layer.setLayerName("")
        callback.assert_not_called()

    def test_reparenting_notifications(self, mocker: MockerFixture) -> None:
        class TestSettings(Settings):
            pass

        parent1 = TestSettings()
        parent2 = TestSettings()

        parent1.onUpdateCall(callback1 := mocker.stub())
        parent2.onUpdateCall(callback2 := mocker.stub())

        layer = TestSettings()

        layer.setParent(parent1)
        callback1.assert_called_once_with(parent1)
        callback2.assert_not_called()

        callback1.reset_mock()
        callback2.reset_mock()

        layer.setParent(parent2)
        callback1.assert_called_once_with(parent1)
        callback2.assert_called_once_with(parent2)

        callback1.reset_mock()
        callback2.reset_mock()

        # When there is no change, no notification should fire.

        layer.setParent(parent2)
        callback1.assert_not_called()
        callback2.assert_not_called()

        callback1.reset_mock()
        callback2.reset_mock()

        layer.setParent(None)
        callback1.assert_not_called()
        callback2.assert_called_once_with(parent2)

        callback1.reset_mock()
        callback2.reset_mock()

        # The layer is now detached and its update should no longer trigger
        # callbacks on the previous parents.

        layer.setLayerName("dummy")
        callback1.assert_not_called()
        callback2.assert_not_called()

    def test_reparenting_renaming_notifications(self, mocker: MockerFixture) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        parent.addLayer("test")
        parent.onUpdateCall(parent_callback := mocker.stub())

        layer = TestSettings()
        layer.onUpdateCall(layer_callback := mocker.stub())

        layer.setLayerName("test")
        parent_callback.assert_not_called()
        layer_callback.assert_called_once_with(layer)

        parent_callback.reset_mock()
        layer_callback.reset_mock()

        # This call adds the layer to the parent AND renames the layer.
        # Therefore both callbacks should be invoked.

        layer.setParent(parent)
        parent_callback.assert_called_once_with(parent)
        layer_callback.assert_called_once_with(layer)

    def test_layer_name_unicity(self) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        layers = [parent.addLayer() for _ in range(10)]
        for layer in layers:
            layer.setLayerName("test")

        assert len(list(parent.children())) == len(
            set(child.layerName() for child in parent.children())
        )

    def test_get_invalid_layer_string_returns_none(self) -> None:
        class TestSettings(Settings):
            pass

        settings = TestSettings()
        assert settings.addLayer("") is not None
        assert settings.getLayer("") is None
        assert settings.getLayer("?!*") is None

    def test_layer_name_made_unique_when_changing_parent(self) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        parent.addLayer("test")

        layer = TestSettings()
        layer.setLayerName("test")

        assert layer.layerName() == "test"

        layer.setParent(parent)

        assert layer.layerName() != "test"

    def test_anonymous_name_not_unique(self) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        layers = [parent.addLayer() for _ in range(10)]
        for layer in layers:
            layer.setLayerName("")

        assert all(layer.layerName() == "" for layer in layers)
