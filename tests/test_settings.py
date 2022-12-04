import io

from pytest_mock import MockerFixture

from sunset import Bundle, Key, List, Settings, normalize


def test_normalize():

    assert normalize("") == ""
    assert normalize("     ") == ""
    assert normalize("  A  B  ") == "ab"
    assert normalize("(a):?/b") == "ab"
    assert normalize("a-b_c") == "a-b_c"


class ExampleSettings(Settings):
    class ExampleBundle(Bundle):
        c = Key(default=0)
        d = Key(default=False)

    inner_bundle = ExampleBundle()
    bundle_list = List(ExampleBundle())
    key_list = List(Key(default=""))

    a = Key(default="")
    b = Key(default="")


class TestSettings:
    def test_new_section(self):

        s = ExampleSettings()
        assert s.hierarchy() == ["main"]

        s1 = s.newSection(name="One level down")
        assert s1.hierarchy() == ["main", "oneleveldown"]

        s2 = s.newSection(name="One level down too")
        assert s2.hierarchy() == ["main", "oneleveldowntoo"]

        ss1 = s1.newSection(name="Two levels down")
        assert ss1.hierarchy() == ["main", "oneleveldown", "twolevelsdown"]

        anonymous = s.newSection()
        assert anonymous.hierarchy() == []

        anonymous2 = anonymous.newSection(
            name="Not anonymous itself but in a anonymous hierachy"
        )
        assert anonymous2.hierarchy() == []

    def test_new_named_section(self):

        s = ExampleSettings()

        assert len(list(s.sections())) == 0

        section = s.newSection(name="same name")
        assert len(list(s.sections())) == 1

        othersection = s.getOrCreateSection(name="same name")
        assert len(list(s.sections())) == 1

        assert othersection is section

    def test_dumpall(self):

        settings = ExampleSettings()
        assert settings.dumpAll() == [(["main"], [])]

        settings.a.set("new a")
        settings.b.set("new b")
        settings.inner_bundle.c.set(40)
        settings.inner_bundle.d.set(True)
        settings.bundle_list.appendOne().c.set(100)
        settings.bundle_list.appendOne().d.set(True)
        settings.key_list.appendOne().set("one")
        settings.key_list.appendOne().set("two")
        assert settings.dumpAll() == [
            (
                ["main"],
                [
                    ("a", "new a"),
                    ("b", "new b"),
                    ("bundle_list.1.c", "100"),
                    ("bundle_list.2.d", "true"),
                    ("inner_bundle.c", "40"),
                    ("inner_bundle.d", "true"),
                    ("key_list.1", "one"),
                    ("key_list.2", "two"),
                ],
            )
        ]

        settings = ExampleSettings()
        settings.a.set("a")
        settings.bundle_list.appendOne().c.set(100)

        s1 = settings.newSection(name="Level 1")
        s1.a.set("sub a")
        s1.b.set("sub b")
        s1.bundle_list.appendOne().c.set(1000)

        s2 = settings.newSection(name="Other level 1")
        s2.inner_bundle.d.set(False)

        anonymous = settings.newSection()
        anonymous.a.set("anonymous")

        subanonymous = anonymous.newSection(name="Should be ignored too")
        subanonymous.b.set("anonymous 2")

        ss1 = s1.newSection(name="Level 2")
        ss1.inner_bundle.c.set(200)

        assert settings.dumpAll() == [
            (
                ["main"],
                [
                    ("a", "a"),
                    ("bundle_list.1.c", "100"),
                ],
            ),
            (
                ["main", "level1"],
                [
                    ("a", "sub a"),
                    ("b", "sub b"),
                    ("bundle_list.1.c", "1000"),
                ],
            ),
            (
                ["main", "level1", "level2"],
                [
                    ("inner_bundle.c", "200"),
                ],
            ),
            (
                ["main", "otherlevel1"],
                [
                    ("inner_bundle.d", "false"),
                ],
            ),
        ]

    def test_restoreall(self):

        data = [
            (
                ["main"],
                [
                    ("a", "a"),
                    ("key_list.1", "one"),
                    ("key_list.2", "two"),
                    ("bundle_list.1.c", "100"),
                ],
            ),
            (
                ["main", "level1"],
                [
                    ("a", "sub a"),
                    ("b", "sub b"),
                    ("key_list.1", "one"),
                    ("key_list.2", "two"),
                    ("bundle_list.1.c", "1000"),
                ],
            ),
            (
                ["main", "level1", "level2"],
                [
                    ("inner_bundle.c", "200"),
                ],
            ),
            (
                ["main", "otherlevel1"],
                [
                    ("inner_bundle.d", "false"),
                ],
            ),
        ]

        settings = ExampleSettings()
        settings.restoreAll(data)

        assert settings.a.get() == "a"
        assert len(settings.bundle_list) == 1
        assert settings.bundle_list[0].c.get() == 100
        assert len(settings.key_list) == 2
        assert settings.key_list[0].get() == "one"
        assert settings.key_list[1].get() == "two"

        settings_sections = {s.sectionName(): s for s in settings.sections()}
        assert len(settings_sections) == 2
        assert "level1" in settings_sections
        level1 = settings_sections["level1"]
        assert "otherlevel1" in settings_sections
        otherlevel1 = settings_sections["otherlevel1"]

        assert level1.a.get() == "sub a"
        assert level1.b.get() == "sub b"
        assert len(level1.bundle_list) == 1
        assert level1.bundle_list[0].c.get() == 1000
        assert len(level1.key_list) == 2
        assert level1.key_list[0].get() == "one"
        assert level1.key_list[1].get() == "two"

        assert not otherlevel1.inner_bundle.d.get()

        level1_sections = {s.sectionName(): s for s in level1.sections()}
        assert len(level1_sections) == 1
        assert "level2" in level1_sections
        level2 = level1_sections["level2"]

        assert level2.inner_bundle.c.get() == 200

    def test_persistence(self):

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

    def test_save(self):

        settings = ExampleSettings()
        settings.a.set("a")
        settings.bundle_list.appendOne().c.set(100)

        s1 = settings.newSection(name="Level 1")
        s1.a.set("sub a")
        s1.b.set("sub b")
        s1.bundle_list.appendOne().c.set(1000)
        s1.key_list.appendOne().set("one")
        s1.key_list.appendOne().set("two")

        s2 = settings.newSection(name="Other level 1")
        s2.inner_bundle.d.set(False)

        anonymous = settings.newSection()
        anonymous.a.set("anonymous")

        subanonymous = anonymous.newSection(name="Should be ignored too")
        subanonymous.b.set("anonymous 2")

        ss1 = s1.newSection(name="Level 2")
        ss1.inner_bundle.c.set(200)

        file = io.StringIO()
        settings.save(file, blanklines=True)

        assert (
            file.getvalue()
            == """\
[main]
a = a
bundle_list.1.c = 100

[level1]
a = sub a
b = sub b
bundle_list.1.c = 1000
key_list.1 = one
key_list.2 = two

[level1/level2]
inner_bundle.c = 200

[otherlevel1]
inner_bundle.d = false
"""
        )

    def test_load(self, mocker: MockerFixture):

        settings = ExampleSettings()
        callback = mocker.stub()
        settings.onUpdateCall(callback)
        settings.load(
            io.StringIO(
                """\
[main]
a = a
bundle_list.1.c = 100

[level1]
a = sub a
b = sub b
key_list.1 = one
bundle_list.1.c = 1000

[level1/level2]
inner_bundle.c = 200

[otherlevel1]
inner_bundle.d = false
"""
            )
        )

        callback.assert_not_called()

        assert settings.a.get() == "a"
        assert len(settings.bundle_list) == 1
        assert settings.bundle_list[0].c.get() == 100

        settings_sections = {s.sectionName(): s for s in settings.sections()}
        assert len(settings_sections) == 2
        assert "level1" in settings_sections
        level1 = settings_sections["level1"]
        assert "otherlevel1" in settings_sections
        otherlevel1 = settings_sections["otherlevel1"]

        assert level1.a.get() == "sub a"
        assert level1.b.get() == "sub b"
        assert len(level1.bundle_list) == 1
        assert level1.bundle_list[0].c.get() == 1000
        assert len(level1.key_list) == 1
        assert level1.key_list[0].get() == "one"

        assert not otherlevel1.inner_bundle.d.get()

        level1_sections = {s.sectionName(): s for s in level1.sections()}
        assert len(level1_sections) == 1
        assert "level2" in level1_sections
        level2 = level1_sections["level2"]

        assert level2.inner_bundle.c.get() == 200

    def test_load_invalid_no_bundle(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
a = no bundle header
"""
            )
        )

        assert settings.a.get() == ""

    def test_load_invalid_repeated_key(self):

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

    def test_load_invalid_repeated_bundle(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
a = repeated bundle

[main]
a = bundle values will be merged, last takes precedence
"""
            )
        )

        assert (
            settings.a.get()
            == "bundle values will be merged, last takes precedence"
        )

    def test_load_invalid_missing_main(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[level1]
a = main bundle is implicitly created if needed
"""
            )
        )

        sections = list(settings.sections())
        assert len(sections) == 1
        assert (
            sections[0].a.get() == "main bundle is implicitly created if needed"
        )

    def test_load_invalid_extra_bundle_separators(self):

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

    def test_load_invalid_bad_bundle_is_skipped(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
a = main

[!%$?]
a = bad bundle
"""
            )
        )

        sections = list(settings.sections())
        assert len(sections) == 0
        assert settings.a.get() == "main"

    def test_load_invalid_similar_are_merged(self):

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

    def test_load_invalid_empty_bundle_is_skipped(self):

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

    def test_load_invalid_bad_key(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
= a
"""
            )
        )

        assert settings.a.get() == ""

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
??a = should be skipped
"""
            )
        )

        assert settings.a.get() == ""

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
[a] = should be skipped
"""
            )
        )

        assert settings.a.get() == ""

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
doesnotexist = should be skipped
"""
            )
        )

        assert settings.a.get() == ""

    def test_load_list_order(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
key_list.5 = five
key_list.3 = three
key_list.1 = dropped
key_list.1 = one
key_list.2 = two
bundle_list.5.c = 5
bundle_list.1.c = 0
bundle_list.2.c = 2
bundle_list.1.c = 1
bundle_list.4.c = 4
"""
            )
        )

        assert len(settings.key_list) == 4
        assert settings.key_list[0].get() == "one"
        assert settings.key_list[1].get() == "two"
        assert settings.key_list[2].get() == "three"
        assert settings.key_list[3].get() == "five"

        assert len(settings.bundle_list) == 4
        assert settings.bundle_list[0].c.get() == 1
        assert settings.bundle_list[1].c.get() == 2
        assert settings.bundle_list[2].c.get() == 4
        assert settings.bundle_list[3].c.get() == 5

    def test_key_updated_notification(self, mocker: MockerFixture):

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

    def test_name_unicity(self):
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        sections = [parent.newSection() for _ in range(10)]
        for section in sections:
            section.setSectionName("test")

        assert all(
            section.sectionName()
            not in {sibling.sectionName() for sibling in section.siblings()}
            for section in sections
        )

    def test_anonymous_name_not_unique(self):
        class TestSettings(Settings):
            pass

        parent = TestSettings()
        sections = [parent.newSection() for _ in range(10)]
        for section in sections:
            section.setSectionName("")

        assert all(section.sectionName() == "" for section in sections)
