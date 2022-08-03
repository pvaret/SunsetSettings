import io

from pytest_mock import MockerFixture

import sunset


def test_normalize():

    assert sunset.normalize("") == ""
    assert sunset.normalize("     ") == ""
    assert sunset.normalize("  A  B  ") == "ab"
    assert sunset.normalize("(a):?/b") == "ab"
    assert sunset.normalize("a-b_c") == "a-b_c"


class ExampleSettings(sunset.Settings):
    class ExampleSection(sunset.Section):
        c: sunset.Setting[int] = sunset.NewSetting(default=0)
        d: sunset.Setting[bool] = sunset.NewSetting(default=False)

    subsection: ExampleSection = sunset.NewSection(ExampleSection)
    list: sunset.List[ExampleSection] = sunset.NewList(ExampleSection)

    a: sunset.Setting[str] = sunset.NewSetting(default="")
    b: sunset.Setting[str] = sunset.NewSetting(default="")


class TestSettings:
    def test_derive(self):

        s = ExampleSettings()
        assert s.hierarchy() == ["main"]

        s1 = s.deriveAs("One level down")
        assert s1.hierarchy() == ["main", "oneleveldown"]

        s2 = s.deriveAs("One level down too")
        assert s2.hierarchy() == ["main", "oneleveldowntoo"]

        ss1 = s1.deriveAs("Two levels down")
        assert ss1.hierarchy() == ["main", "oneleveldown", "twolevelsdown"]

        anonymous = s.derive()
        assert anonymous.hierarchy() == []

        anonymous2 = anonymous.deriveAs(
            "No anonymous itself but in a anonymous hierachy"
        )
        assert anonymous2.hierarchy() == []

    def test_deriveas(self):

        s = ExampleSettings()

        assert len(list(s.children())) == 0

        child = s.deriveAs("same name")
        assert len(list(s.children())) == 1

        otherchild = s.deriveAs("same name")
        assert len(list(s.children())) == 1

        assert otherchild is child

    def test_dumpall(self):

        settings = ExampleSettings()
        assert settings.dumpAll() == [(["main"], [])]

        settings.a.set("new a")
        settings.b.set("new b")
        settings.subsection.c.set(40)
        settings.subsection.d.set(True)
        settings.list.append(ExampleSettings.ExampleSection())
        settings.list[0].c.set(100)
        settings.list.append(ExampleSettings.ExampleSection())
        settings.list[1].d.set(True)
        assert settings.dumpAll() == [
            (
                ["main"],
                [
                    ("a", "new a"),
                    ("b", "new b"),
                    ("list.1.c", "100"),
                    ("list.2.d", "true"),
                    ("subsection.c", "40"),
                    ("subsection.d", "true"),
                ],
            )
        ]

        settings = ExampleSettings()
        settings.a.set("a")
        settings.list.append(ExampleSettings.ExampleSection())
        settings.list[0].c.set(100)

        s1 = settings.deriveAs("Level 1")
        s1.a.set("sub a")
        s1.b.set("sub b")
        s1.list.append(ExampleSettings.ExampleSection())
        s1.list[0].c.set(1000)

        s2 = settings.deriveAs("Other level 1")
        s2.subsection.d.set(False)

        anonymous = settings.derive()
        anonymous.a.set("anonymous")

        subanonymous = anonymous.deriveAs("Should be ignored too")
        subanonymous.b.set("anonymous 2")

        ss1 = s1.deriveAs("Level 2")
        ss1.subsection.c.set(200)

        assert settings.dumpAll() == [
            (
                ["main"],
                [
                    ("a", "a"),
                    ("list.1.c", "100"),
                ],
            ),
            (
                ["main", "level1"],
                [
                    ("a", "sub a"),
                    ("b", "sub b"),
                    ("list.1.c", "1000"),
                ],
            ),
            (
                ["main", "level1", "level2"],
                [
                    ("subsection.c", "200"),
                ],
            ),
            (
                ["main", "otherlevel1"],
                [
                    ("subsection.d", "false"),
                ],
            ),
        ]

    def test_restoreall(self):

        data = [
            (
                ["main"],
                [
                    ("a", "a"),
                    ("list.1.c", "100"),
                ],
            ),
            (
                ["main", "level1"],
                [
                    ("a", "sub a"),
                    ("b", "sub b"),
                    ("list.1.c", "1000"),
                ],
            ),
            (
                ["main", "level1", "level2"],
                [
                    ("subsection.c", "200"),
                ],
            ),
            (
                ["main", "otherlevel1"],
                [
                    ("subsection.d", "false"),
                ],
            ),
        ]

        settings = ExampleSettings()
        settings.restoreAll(data)

        assert settings.a.get() == "a"
        assert len(settings.list) == 1
        assert settings.list[0].c.get() == 100

        settings_children = {c.name(): c for c in settings.children()}
        assert len(settings_children) == 2
        assert "level1" in settings_children
        level1 = settings_children["level1"]
        assert "otherlevel1" in settings_children
        otherlevel1 = settings_children["otherlevel1"]

        assert level1.a.get() == "sub a"
        assert level1.b.get() == "sub b"
        assert len(level1.list) == 1
        assert level1.list[0].c.get() == 1000

        assert not otherlevel1.subsection.d.get()

        level1_children = {c.name(): c for c in level1.children()}
        assert len(level1_children) == 1
        assert "level2" in level1_children
        level2 = level1_children["level2"]

        assert level2.subsection.c.get() == 200

    def test_persistence(self):

        # Settings keep a reference to their children, but not to their parent.

        settings = ExampleSettings()
        level1 = settings.deriveAs("level 1")
        level2 = level1.deriveAs("level 2")

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del settings
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 1

    def test_save(self):

        settings = ExampleSettings()
        settings.a.set("a")
        settings.list.append(ExampleSettings.ExampleSection())
        settings.list[0].c.set(100)

        s1 = settings.deriveAs("Level 1")
        s1.a.set("sub a")
        s1.b.set("sub b")
        s1.list.append(ExampleSettings.ExampleSection())
        s1.list[0].c.set(1000)

        s2 = settings.deriveAs("Other level 1")
        s2.subsection.d.set(False)

        anonymous = settings.derive()
        anonymous.a.set("anonymous")

        subanonymous = anonymous.deriveAs("Should be ignored too")
        subanonymous.b.set("anonymous 2")

        ss1 = s1.deriveAs("Level 2")
        ss1.subsection.c.set(200)

        file = io.StringIO()
        settings.save(file, blanklines=True)

        assert (
            file.getvalue()
            == """\
[main]
a = a
list.1.c = 100

[level1]
a = sub a
b = sub b
list.1.c = 1000

[level1/level2]
subsection.c = 200

[otherlevel1]
subsection.d = false
"""
        )

    def test_load(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
a = a
list.1.c = 100

[level1]
a = sub a
b = sub b
list.1.c = 1000

[level1/level2]
subsection.c = 200

[otherlevel1]
subsection.d = false
"""
            )
        )
        assert settings.a.get() == "a"
        assert len(settings.list) == 1
        assert settings.list[0].c.get() == 100

        settings_children = {c.name(): c for c in settings.children()}
        assert len(settings_children) == 2
        assert "level1" in settings_children
        level1 = settings_children["level1"]
        assert "otherlevel1" in settings_children
        otherlevel1 = settings_children["otherlevel1"]

        assert level1.a.get() == "sub a"
        assert level1.b.get() == "sub b"
        assert len(level1.list) == 1
        assert level1.list[0].c.get() == 1000

        assert not otherlevel1.subsection.d.get()

        level1_children = {c.name(): c for c in level1.children()}
        assert len(level1_children) == 1
        assert "level2" in level1_children
        level2 = level1_children["level2"]

        assert level2.subsection.c.get() == 200

    def test_load_invalid_no_section(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
a = no section header
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

    def test_load_invalid_repeated_section(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
a = repeated section

[main]
a = section values will be merged, last takes precedence
"""
            )
        )

        assert (
            settings.a.get()
            == "section values will be merged, last takes precedence"
        )

    def test_load_invalid_missing_main(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[level1]
a = main section is implicitly created if needed
"""
            )
        )

        children = list(settings.children())
        assert len(children) == 1
        assert (
            children[0].a.get()
            == "main section is implicitly created if needed"
        )

    def test_load_invalid_extra_section_separators(self):

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

        children = list(settings.children())
        assert len(children) == 1
        subchildren = list(children[0].children())
        assert len(subchildren) == 1
        assert subchildren[0].a.get() == "extra separators should be skipped"

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

        children = list(settings.children())
        assert len(children) == 1
        assert children[0].a.get() == "extra separators should be skipped"

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

        children = list(settings.children())
        assert len(children) == 1
        assert children[0].a.get() == "extra separators should be skipped"

    def test_load_invalid_bad_section_is_skipped(self):

        settings = ExampleSettings()
        settings.load(
            io.StringIO(
                """\
[main]
a = main

[!%$?]
a = bad section
"""
            )
        )

        children = list(settings.children())
        assert len(children) == 0
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

        children = list(settings.children())
        assert len(children) == 0
        assert settings.a.get() == "merged"

    def test_load_invalid_empty_section_is_skipped(self):

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

        children = list(settings.children())
        assert len(children) == 0
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

    def test_setting_modified_notification(self, mocker: MockerFixture):

        callback = mocker.stub()

        settings = ExampleSettings()
        settings.onSettingModifiedCall(callback)

        settings.a.set("test 1")
        callback.assert_called_once_with(settings)
        callback.reset_mock()

        child = settings.deriveAs("child")
        callback.assert_called_once_with(settings)
        callback.reset_mock()

        child.a.set("test 2")
        callback.assert_called_once_with(settings)
        callback.reset_mock()

        anonymous = settings.derive()
        callback.assert_not_called()
        callback.reset_mock()

        anonymous.a.set("test 3")
        callback.assert_not_called()
        callback.reset_mock()

        anonymousChild = anonymous.deriveAs("other child")
        callback.assert_not_called()
        callback.reset_mock()

        anonymousChild.a.set("test 4")
        callback.assert_not_called()
        callback.reset_mock()

        anonymous.setName("no longer anonymous")
        callback.assert_called_once_with(settings)
        callback.reset_mock()

        anonymousChild.a.set("test 5")
        callback.assert_called_once_with(settings)
        callback.reset_mock()
