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
    def test_new_named_section(self) -> None:
        settings = ExampleSettings()

        assert len(list(settings.sections())) == 0

        section = settings.newSection(name="same name")
        assert len(list(settings.sections())) == 1

        othersection = settings.getOrCreateSection(name="same name")
        assert len(list(settings.sections())) == 1

        assert othersection is section

    def test_dump_fields(self) -> None:
        # When no field is set, the section should still be dumped.

        settings = ExampleSettings()
        assert list(settings.dumpFields()) == [
            ("", None),
        ]

        # This applies to subsections too.

        settings.newSection("empty")
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

        # Anonymous sections, and subsections of anonymous sections, should not
        # be dumped.

        settings = ExampleSettings()
        settings.a.set("a")
        settings.bunch_list.appendOne().c.set(100)

        section1 = settings.newSection(name="Section 1")
        section1.a.set("sub a")
        section1.b.set("sub b")
        section1.bunch_list.appendOne().c.set(1000)

        section2 = settings.newSection(name="Section 2")
        section2.inner_bunch.d.set(False)

        anonymous = settings.newSection()
        anonymous.a.set("anonymous")

        subanonymous = anonymous.newSection(name="Should be ignored too")
        subanonymous.b.set("anonymous 2")

        subsection = section1.newSection(name="Subsection")
        subsection.inner_bunch.c.set(200)

        assert list(settings.dumpFields()) == [
            ("a", "a"),
            ("bunch_list.1.c", "100"),
            ("section1/a", "sub a"),
            ("section1/b", "sub b"),
            ("section1/bunch_list.1.c", "1000"),
            ("section1/subsection/inner_bunch.c", "200"),
            ("section2/inner_bunch.d", "false"),
        ]

        # Section should be dumped in alphabetic order.

        settings = ExampleSettings()
        settings.newSection("z")
        settings.newSection("mm")
        settings.newSection("aaa")
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

        # Test restoring a field on a subsection.

        assert settings.getSection("section1") is None
        assert settings.restoreFields([("section1/a", "test section1 a")])
        section1 = settings.getSection("section1")
        assert section1 is not None
        assert section1.a.get() == "test section1 a"
        callback.assert_not_called()

        assert settings.restoreFields([("section2/subsection/a", "test subsection a")])
        section2 = settings.getSection("section2")
        assert section2 is not None
        subsection = section2.getSection("subsection")
        assert subsection is not None
        assert subsection.a.get() == "test subsection a"
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
        # Settings keep a reference to their sections, but not to their parent.

        settings = ExampleSettings()
        level1 = settings.newSection(name="level 1")
        level2 = level1.newSection(name="level 2")

        assert level1.parent() is not None
        assert len(list(level1.sections())) == 1

        del settings
        del level2
        assert level1.parent() is None
        assert len(list(level1.sections())) == 1

    def test_save(self) -> None:
        settings = ExampleSettings()
        settings.a.set("a")
        settings.bunch_list.appendOne().c.set(100)

        section1 = settings.newSection(name="Level 1")
        section1.a.set("sub a")
        section1.b.set("sub b")
        section1.bunch_list.appendOne().c.set(1000)
        section1.key_list.appendOne().set("one")
        section1.key_list.appendOne()
        section1.key_list.appendOne().set("")

        section2 = settings.newSection(name="Other level 1")
        section2.inner_bunch.d.set(False)

        anonymous = settings.newSection()
        anonymous.a.set("anonymous")

        subanonymous = anonymous.newSection(name="Should be ignored too")
        subanonymous.b.set("anonymous 2")

        subsection1 = section1.newSection(name="Level 2")
        subsection1.inner_bunch.c.set(200)

        settings.newSection("empty")

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

        section1 = settings.newSection(name="Level 1")
        section1.a.set("sub a")
        section1.b.set("sub b")
        section1.bunch_list.appendOne().c.set(1000)
        section1.key_list.appendOne().set("one")
        section1.key_list.appendOne()
        section1.key_list.appendOne().set("")

        section2 = settings.newSection(name="Other level 1")
        section2.inner_bunch.d.set(False)

        subsection1 = section1.newSection(name="Level 2")
        subsection1.inner_bunch.c.set(200)

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

    def test_save_non_default_toplevel_section_name(self) -> None:
        settings = ExampleSettings()
        settings.setSectionName("renamed")
        settings.a.set("a")
        settings.bunch_list.appendOne().c.set(100)

        section1 = settings.newSection(name="Level 1")
        section1.b.set("sub b")
        section1.newSection("Level 2")

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

        settings_sections = {s.sectionName(): s for s in settings.sections()}
        assert len(settings_sections) == 2
        assert "level1" in settings_sections
        level1 = settings_sections["level1"]
        assert "otherlevel1" in settings_sections
        otherlevel1 = settings_sections["otherlevel1"]

        assert level1.a.get() == "sub a"
        assert level1.b.get() == "sub b"
        assert len(level1.bunch_list) == 1
        assert level1.bunch_list[0].c.get() == 1000
        assert len(level1.key_list) == 3
        assert level1.key_list[0].get() == "one"
        assert not level1.key_list[1].isSet()
        assert level1.key_list[2].isSet() and level1.key_list[2].get() == ""

        assert not otherlevel1.inner_bunch.d.get()

        level1_sections = {s.sectionName(): s for s in level1.sections()}
        assert len(level1_sections) == 1
        assert "level2" in level1_sections
        level2 = level1_sections["level2"]

        assert level2.inner_bunch.c.get() == 200

    def test_load_no_section_means_main(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                a = no main section
                """
            )
        )

        assert settings.a.get() == "no main section"

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

    def test_load_repeated_sections_are_merged(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [main]
                a = repeated section

                [main]
                a = section values will be merged, first takes precedence
                b = merged value
                """
            )
        )

        assert settings.a.get() == "repeated section"
        assert settings.b.get() == "merged value"

    def test_load_sections_valid_when_missing_main(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [level1]
                a = main section is implicitly created if needed
                """
            )
        )

        sections = list(settings.sections())
        assert len(sections) == 1
        assert sections[0].a.get() == "main section is implicitly created if needed"

    def test_load_invalid_extra_section_separators(self) -> None:
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

        sections = list(settings.sections())
        assert len(sections) == 1
        subsections = list(sections[0].sections())
        assert len(subsections) == 1
        assert subsections[0].a.get() == "extra separators should be skipped"

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

        sections = list(settings.sections())
        assert len(sections) == 1
        assert sections[0].a.get() == "extra separators should be skipped"

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

        sections = list(settings.sections())
        assert len(sections) == 1
        assert sections[0].a.get() == "extra separators should be skipped"

    def test_load_invalid_bad_section_is_skipped(self) -> None:
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

        sections = list(settings.sections())
        assert len(sections) == 0
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

        sections = list(settings.sections())
        assert len(sections) == 0
        assert settings.a.get() == "main"
        assert settings.b.get() == "merged"

    def test_load_invalid_empty_section_is_skipped(self) -> None:
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

        sections = list(settings.sections())
        assert len(sections) == 0
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

    def test_load_sections_created_even_if_empty(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
                [shouldexist]
                """
            )
        )
        assert settings.getSection("shouldexist") is not None

    def test_load_renamed_settings(self) -> None:
        settings = ExampleSettings()
        settings.setSectionName("renamed")

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

        def callback(_: ExampleSettings) -> Dummy: ...

        settings.onUpdateCall(callback)

    def test_key_updated_notification(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        settings = ExampleSettings()
        settings.onUpdateCall(callback)

        settings.a.set("test 1")
        callback.assert_called_once_with(settings.a)
        callback.reset_mock()

        section = settings.newSection(name="section")
        callback.assert_called_once_with(settings)
        callback.reset_mock()

        section.a.set("test 2")
        callback.assert_called_once_with(section.a)
        callback.reset_mock()

        anonymous = settings.newSection()
        callback.assert_called_once_with(settings)
        callback.reset_mock()

        anonymous.a.set("test 3")
        callback.assert_called_once_with(anonymous.a)
        callback.reset_mock()

        anonymoussection = anonymous.newSection(name="other section")
        callback.assert_called_once_with(anonymous)
        callback.reset_mock()

        anonymoussection.a.set("test 4")
        callback.assert_called_once_with(anonymoussection.a)
        callback.reset_mock()

        anonymous.setSectionName("no longer anonymous")
        callback.assert_called_once_with(anonymous)
        callback.reset_mock()

    def test_setting_same_section_name_doesnt_notify(
        self, mocker: MockerFixture
    ) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()

        section = parent.newSection("test")

        section.onUpdateCall(callback := mocker.stub())

        section.setSectionName("test")
        callback.assert_not_called()

        section.setSectionName("")
        callback.assert_called_once_with(section)
        callback.reset_mock()

        section.setSectionName("")
        callback.assert_not_called()

    def test_reparenting_notifications(self, mocker: MockerFixture) -> None:
        class TestSettings(Settings):
            pass

        parent1 = TestSettings()
        parent2 = TestSettings()

        parent1.onUpdateCall(callback1 := mocker.stub())
        parent2.onUpdateCall(callback2 := mocker.stub())

        section = TestSettings()

        section.setParent(parent1)
        callback1.assert_called_once_with(parent1)
        callback2.assert_not_called()

        callback1.reset_mock()
        callback2.reset_mock()

        section.setParent(parent2)
        callback1.assert_called_once_with(parent1)
        callback2.assert_called_once_with(parent2)

        callback1.reset_mock()
        callback2.reset_mock()

        # When there is no change, no notification should fire.

        section.setParent(parent2)
        callback1.assert_not_called()
        callback2.assert_not_called()

        callback1.reset_mock()
        callback2.reset_mock()

        section.setParent(None)
        callback1.assert_not_called()
        callback2.assert_called_once_with(parent2)

        callback1.reset_mock()
        callback2.reset_mock()

        # The section is now detached and its update should no longer trigger
        # callbacks on the previous parents.

        section.setSectionName("dummy")
        callback1.assert_not_called()
        callback2.assert_not_called()

    def test_reparenting_renaming_notifications(self, mocker: MockerFixture) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        parent.newSection("test")
        parent.onUpdateCall(parent_callback := mocker.stub())

        section = TestSettings()
        section.onUpdateCall(section_callback := mocker.stub())

        section.setSectionName("test")
        parent_callback.assert_not_called()
        section_callback.assert_called_once_with(section)

        parent_callback.reset_mock()
        section_callback.reset_mock()

        # This call adds the section to the parent AND renames the section.
        # Therefore both callbacks should be invoked.

        section.setParent(parent)
        parent_callback.assert_called_once_with(parent)
        section_callback.assert_called_once_with(section)

    def test_section_name_unicity(self) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        sections = [parent.newSection() for _ in range(10)]
        for section in sections:
            section.setSectionName("test")

        assert len(list(parent.children())) == len(
            set(child.sectionName() for child in parent.children())
        )

    def test_get_invalid_section_string_returns_none(self) -> None:
        class TestSettings(Settings):
            pass

        settings = TestSettings()
        assert settings.newSection("") is not None
        assert settings.getSection("") is None
        assert settings.getSection("?!*") is None

    def test_section_name_made_unique_when_changing_parent(self) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        parent.newSection("test")

        section = TestSettings()
        section.setSectionName("test")

        assert section.sectionName() == "test"

        section.setParent(parent)

        assert section.sectionName() != "test"

    def test_anonymous_name_not_unique(self) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        sections = [parent.newSection() for _ in range(10)]
        for section in sections:
            section.setSectionName("")

        assert all(section.sectionName() == "" for section in sections)
