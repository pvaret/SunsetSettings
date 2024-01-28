import io

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
    def test_new_section(self) -> None:
        settings = ExampleSettings()
        assert settings.fieldPath() == "main/"

        section1 = settings.newSection(name="One level down")
        assert section1.fieldPath() == "main/oneleveldown/"

        section2 = settings.newSection(name="One level down too")
        assert section2.fieldPath() == "main/oneleveldowntoo/"

        subsection1 = section1.newSection(name="Two levels down")
        assert subsection1.fieldPath() == "main/oneleveldown/twolevelsdown/"

        anonymous = settings.newSection()
        assert anonymous.fieldPath() == "main/?/"

        anonymous2 = anonymous.newSection(
            name="Not anonymous itself but in a anonymous hierachy"
        )
        assert (
            anonymous2.fieldPath()
            == "main/?/notanonymousitselfbutinaanonymoushierachy/"
        )

    def test_new_named_section(self) -> None:
        settings = ExampleSettings()

        assert len(list(settings.sections())) == 0

        section = settings.newSection(name="same name")
        assert len(list(settings.sections())) == 1

        othersection = settings.getOrCreateSection(name="same name")
        assert len(list(settings.sections())) == 1

        assert othersection is section

    def test_field_path(self) -> None:
        settings = ExampleSettings()

        assert settings.fieldPath() == "main/"
        assert settings.a.fieldPath() == "main/a"
        assert settings.inner_bunch.fieldPath() == "main/inner_bunch."
        assert settings.inner_bunch.c.fieldPath() == "main/inner_bunch.c"
        settings.bunch_list.appendOne()
        settings.bunch_list.appendOne()
        assert settings.bunch_list.fieldPath() == "main/bunch_list."
        assert settings.bunch_list[1].fieldPath() == "main/bunch_list.2."
        assert settings.bunch_list[1].d.fieldPath() == "main/bunch_list.2.d"
        settings.key_list.appendOne()
        settings.key_list.appendOne()
        assert settings.key_list.fieldPath() == "main/key_list."
        assert settings.key_list[1].fieldPath() == "main/key_list.2"

        section = settings.newSection("section")
        assert section.fieldPath() == "main/section/"
        assert section.a.fieldPath() == "main/section/a"
        assert section.inner_bunch.fieldPath() == "main/section/inner_bunch."
        assert section.inner_bunch.c.fieldPath() == "main/section/inner_bunch.c"
        section.bunch_list.appendOne()
        section.bunch_list.appendOne()
        assert section.bunch_list.fieldPath() == "main/section/bunch_list."
        assert section.bunch_list[1].fieldPath() == "main/section/bunch_list.2."
        assert (
            section.bunch_list[1].d.fieldPath() == "main/section/bunch_list.2.d"
        )
        section.key_list.appendOne()
        section.key_list.appendOne()
        assert section.key_list.fieldPath() == "main/section/key_list."
        assert section.key_list[1].fieldPath() == "main/section/key_list.2"

        anonymous = settings.newSection()
        assert anonymous.fieldPath() == "main/?/"
        assert anonymous.a.fieldPath() == "main/?/a"
        assert anonymous.inner_bunch.fieldPath() == "main/?/inner_bunch."
        assert anonymous.inner_bunch.c.fieldPath() == "main/?/inner_bunch.c"
        anonymous.bunch_list.appendOne()
        anonymous.bunch_list.appendOne()
        assert anonymous.bunch_list.fieldPath() == "main/?/bunch_list."
        assert anonymous.bunch_list[1].fieldPath() == "main/?/bunch_list.2."
        assert anonymous.bunch_list[1].d.fieldPath() == "main/?/bunch_list.2.d"
        anonymous.key_list.appendOne()
        anonymous.key_list.appendOne()
        assert anonymous.key_list.fieldPath() == "main/?/key_list."
        assert anonymous.key_list[1].fieldPath() == "main/?/key_list.2"

        settings.setSectionName("renamed")
        assert settings.fieldPath() == "renamed/"
        assert settings.a.fieldPath() == "renamed/a"

        settings.setSectionName("")
        assert settings.fieldPath() == "main/"
        assert settings.a.fieldPath() == "main/a"

    def test_dump_fields(self) -> None:
        # When no field is set, the name of the section should still be dumped.

        settings = ExampleSettings()
        assert list(settings.dumpFields()) == [
            ("main/", None),
        ]

        # This applies to subsections too.

        settings.newSection("empty")
        assert list(settings.dumpFields()) == [
            ("main/", None),
            ("main/empty/", None),
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
            ("main/a", "new a"),
            ("main/b", "new b"),
            ("main/bunch_list.1.c", "100"),
            ("main/bunch_list.2.d", "true"),
            ("main/inner_bunch.c", "40"),
            ("main/inner_bunch.d", "true"),
            ("main/key_list.1", "one"),
            ("main/key_list.2", None),
            ("main/key_list.3", "three"),
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
            ("main/a", "a"),
            ("main/bunch_list.1.c", "100"),
            ("main/section1/a", "sub a"),
            ("main/section1/b", "sub b"),
            ("main/section1/bunch_list.1.c", "1000"),
            ("main/section1/subsection/inner_bunch.c", "200"),
            ("main/section2/inner_bunch.d", "false"),
        ]

        # Settings with a custom section name should use that name in dumps.

        settings.setSectionName("new")
        assert list(settings.dumpFields()) == [
            ("new/a", "a"),
            ("new/bunch_list.1.c", "100"),
            ("new/section1/a", "sub a"),
            ("new/section1/b", "sub b"),
            ("new/section1/bunch_list.1.c", "1000"),
            ("new/section1/subsection/inner_bunch.c", "200"),
            ("new/section2/inner_bunch.d", "false"),
        ]

        # Section should be dumped in alphabetic order.

        settings = ExampleSettings()
        settings.newSection("z")
        settings.newSection("mm")
        settings.newSection("aaa")
        assert list(settings.dumpFields()) == [
            ("main/", None),
            ("main/aaa/", None),
            ("main/mm/", None),
            ("main/z/", None),
        ]

    def test_restore_field(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        # Test restorting a field. As well, restoring a field should not trigger
        # a callback.

        settings = ExampleSettings()
        settings.onUpdateCall(callback)
        assert settings.a.get() == ""
        assert settings.restoreField("main/a", "test main a")
        assert settings.a.get() == "test main a"
        callback.assert_not_called()

        # Test restoring a field on an inner Bunch.

        assert settings.inner_bunch.c.get() == 0
        assert settings.restoreField("main/inner_bunch.c", "123")
        assert settings.inner_bunch.c.get() == 123
        callback.assert_not_called()

        # Test restoring a field on a subsection.

        assert settings.getSection("section1") is None
        assert settings.restoreField("main/section1/a", "test section1 a")
        section1 = settings.getSection("section1")
        assert section1 is not None
        assert section1.a.get() == "test section1 a"
        callback.assert_not_called()

        assert settings.restoreField(
            "main/section2/subsection/a", "test subsection a"
        )
        section2 = settings.getSection("section2")
        assert section2 is not None
        subsection = section2.getSection("subsection")
        assert subsection is not None
        assert subsection.a.get() == "test subsection a"
        callback.assert_not_called()

        # Test restoring fields on a renamed Settings.

        renamed_settings = ExampleSettings()
        renamed_settings.setSectionName("renamed")
        renamed_settings.onUpdateCall(callback)
        assert renamed_settings.restoreField("renamed/a", "test renamed a")
        assert renamed_settings.a.get() == "test renamed a"
        callback.assert_not_called()

        assert renamed_settings.b.get() == ""
        assert not renamed_settings.restoreField("main/b", "test invalid b")
        assert renamed_settings.b.get() == ""
        callback.assert_not_called()

        # Test restorting with an invalid path.

        other_settings = ExampleSettings()
        other_settings.onUpdateCall(callback)
        assert not other_settings.isSet()
        assert not other_settings.restoreField("invalid/a", "test invalid a")
        assert not other_settings.isSet()
        callback.assert_not_called()

        assert not other_settings.restoreField("main/invalid", "test invalid a")
        assert not other_settings.isSet()
        callback.assert_not_called()

        assert not other_settings.restoreField("invalid", "test invalid a")
        assert not other_settings.isSet()
        callback.assert_not_called()

        assert not other_settings.restoreField("/a", "test invalid a")
        assert not other_settings.isSet()
        callback.assert_not_called()

        assert not other_settings.restoreField("a/invalid", "test invalid a")
        assert not other_settings.isSet()
        callback.assert_not_called()

        assert not other_settings.restoreField("a", "test invalid a")
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

        assert (
            file.getvalue()
            == """\
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

    def test_load_invalid_no_section(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
a = no bunch header
"""
            )
        )

        assert settings.a.get() == ""

    def test_load_invalid_repeated_key(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
a = repeated key
a = last value should be used
"""
            )
        )

        assert settings.a.get() == "last value should be used"

    def test_load_invalid_repeated_section(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
a = repeated bunch

[main]
a = bunch values will be merged, last takes precedence
"""
            )
        )

        assert (
            settings.a.get()
            == "bunch values will be merged, last takes precedence"
        )

    def test_load_invalid_missing_main(self) -> None:
        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[level1]
a = main bunch is implicitly created if needed
"""
            )
        )

        sections = list(settings.sections())
        assert len(sections) == 1
        assert (
            sections[0].a.get() == "main bunch is implicitly created if needed"
        )

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
a = merged
"""
            )
        )

        sections = list(settings.sections())
        assert len(sections) == 0
        assert settings.a.get() == "merged"

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
        stub = mocker.Mock(return_value=sentinel)

        settings = ExampleSettings()
        settings.setAutosaverClass(stub)
        ret = settings.autosave(
            "/tmp/test",
            save_delay=12,
        )

        assert ret is sentinel

        stub.assert_called_once_with(
            settings,
            "/tmp/test",
            save_delay=12,
            save_on_update=True,
            logger=None,
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

        section = settings.newSection(name="section")
        callback.assert_called_once_with(section)
        callback.reset_mock()

        section.a.set("test 2")
        callback.assert_called_once_with(section.a)
        callback.reset_mock()

        anonymous = settings.newSection()
        callback.assert_not_called()
        callback.reset_mock()

        anonymous.a.set("test 3")
        callback.assert_not_called()
        callback.reset_mock()

        anonymoussection = anonymous.newSection(name="other section")
        callback.assert_not_called()
        callback.reset_mock()

        anonymoussection.a.set("test 4")
        callback.assert_not_called()
        callback.reset_mock()

        anonymous.setSectionName("no longer anonymous")
        callback.assert_called_once_with(anonymous)
        callback.reset_mock()

        anonymoussection.a.set("test 5")
        callback.assert_called_once_with(anonymoussection.a)
        callback.reset_mock()

    def test_name_unicity(self) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        sections = [parent.newSection() for _ in range(10)]
        for section in sections:
            section.setSectionName("test")

        assert len(list(parent.children())) == len(
            set(child.sectionName() for child in parent.children())
        )

    def test_anonymous_name_not_unique(self) -> None:
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        sections = [parent.newSection() for _ in range(10)]
        for section in sections:
            section.setSectionName("")

        assert all(section.sectionName() == "" for section in sections)
