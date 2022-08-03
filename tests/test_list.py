from typing import Iterator

from pytest_mock import MockerFixture

import sunset


class ExampleSection(sunset.Section):

    test: sunset.Setting[str] = sunset.NewSetting("")


class TestList:
    def test_protocol_implementation(self):

        r: sunset.List[ExampleSection] = sunset.List(ExampleSection)
        assert isinstance(r, sunset.protocols.Inheriter)
        assert isinstance(r, sunset.protocols.Dumpable)

    def test_add_pop(self):

        r: sunset.List[ExampleSection] = sunset.List(ExampleSection)
        r.append(ExampleSection())

        assert len(r) == 1

        r[0].test.set("test")
        assert r[0].test.get() == "test"

        r.pop()

        assert len(r) == 0

    def test_inheritance(self):

        r1: sunset.List[ExampleSection] = sunset.List(ExampleSection)
        r2: sunset.List[ExampleSection] = sunset.List(ExampleSection)

        assert r2 not in r1.children()
        assert r2.parent() is None

        r2.setParent(r1)
        assert r2 in r1.children()
        assert r2.parent() is r1

        r2.setParent(None)
        assert r2 not in r1.children()
        assert r2.parent() is None

    def test_reparenting(self):

        r1: sunset.List[ExampleSection] = sunset.List(ExampleSection)
        r2: sunset.List[ExampleSection] = sunset.List(ExampleSection)
        r3: sunset.List[ExampleSection] = sunset.List(ExampleSection)

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

        r1: sunset.List[ExampleSection] = sunset.List(ExampleSection)
        r2: sunset.List[ExampleSection] = sunset.List(ExampleSection)

        r1.append(ExampleSection())
        r1[0].test.set("test r1")
        r2.append(ExampleSection())
        r2[0].test.set("test r2")

        assert flatten(r2.iterAll()) == ["test r2"]

        r2.setParent(r1)

        assert flatten(r2.iterAll()) == ["test r2", "test r1"]

    def test_dump(self):

        r: sunset.List[ExampleSection] = sunset.List(ExampleSection)

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

    def test_restore(self):

        r: sunset.List[ExampleSection] = sunset.List(ExampleSection)

        r.restore(
            [
                ("1.test", "test 1"),
                ("2.test", "test 2"),
            ]
        )

        assert len(r) == 2
        assert r[0].test.get() == "test 1"
        assert r[1].test.get() == "test 2"

    def test_persistence(self):

        # A List does not keep a reference to its parent or children.

        setting: sunset.List[ExampleSection] = sunset.List(ExampleSection)
        level1: sunset.List[ExampleSection] = sunset.List(ExampleSection)
        level1.setParent(setting)
        level2: sunset.List[ExampleSection] = sunset.List(ExampleSection)
        level2.setParent(level1)

        assert level1.parent() is not None
        assert len(list(level1.children())) == 1

        del setting
        del level2
        assert level1.parent() is None
        assert len(list(level1.children())) == 0

    def test_setting_modification_callback(self, mocker: MockerFixture):

        callback = mocker.stub()

        setting: sunset.List[ExampleSection] = sunset.List(ExampleSection)

        s1 = ExampleSection()
        s2 = ExampleSection()
        s3 = ExampleSection()

        setting.onSettingModifiedCall(callback)

        setting.append(s1)
        callback.assert_called_once_with(setting)
        callback.reset_mock()

        setting.insert(0, s2)
        callback.assert_called_once_with(setting)
        callback.reset_mock()

        setting[0] = s3
        callback.assert_called_once_with(setting)
        callback.reset_mock()

        assert s1 in setting
        s1.test.set("test 1")
        callback.assert_called_once_with(setting)
        callback.reset_mock()

        assert s2 not in setting
        s2.test.set("test 2")
        callback.assert_not_called()
        callback.reset_mock()

        assert s3 in setting
        s3.test.set("test 3")
        callback.assert_called_once_with(setting)
        callback.reset_mock()

        del setting[1]
        callback.assert_called_once_with(setting)
        callback.reset_mock()
