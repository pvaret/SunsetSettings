import io

from sunset import exporter


def test_escape() -> None:
    assert exporter.maybe_escape("") == '""'
    assert exporter.maybe_escape("123") == "123"
    assert exporter.maybe_escape("test test") == "test test"
    assert exporter.maybe_escape("   ") == '"   "'
    assert exporter.maybe_escape(" a") == '" a"'
    assert exporter.maybe_escape("a ") == '"a "'
    assert exporter.maybe_escape('"') == r'"\""'
    assert exporter.maybe_escape("test\ntest") == r'"test\ntest"'
    assert exporter.maybe_escape(r"test\test") == r'"test\\test"'


def test_unescape() -> None:
    assert exporter.unescape("") == ""
    assert exporter.unescape('""') == ""
    assert exporter.unescape('"') == '"'
    assert exporter.unescape('"test') == "test"
    assert exporter.unescape('test"') == "test"
    assert exporter.unescape("123") == "123"
    assert exporter.unescape("test \ttest") == "test \ttest"
    assert exporter.unescape('"   "') == "   "
    assert exporter.unescape('" a"') == " a"
    assert exporter.unescape('"a "') == "a "
    assert exporter.unescape(r'"\""') == '"'
    assert exporter.unescape(r'"test\ntest"') == "test\ntest"
    assert exporter.unescape(r'"test\\test"') == r"test\test"


def test_escape_reversible() -> None:
    for string in (
        "",
        "123",
        "test test",
        "   ",
        " a",
        "a ",
        '"',
        "test\ntest",
        r"test\test",
    ):
        assert exporter.unescape(exporter.maybe_escape(string)) == string


def test_save() -> None:
    input = [
        ("main/a", "1"),
        ("main/b.c", "test"),
        ("main/d.1.e", "test 2\ntest 2"),
        ("main/d.2.e", "  "),
        ("main/level1/b.c", "sub test"),
        ("main/level1/level2/a", "sub sub test"),
    ]

    file = io.StringIO()

    exporter.save_to_file(file, input, blanklines=True)
    assert (
        file.getvalue()
        == """\
[main]
a = 1
b.c = test
d.1.e = "test 2\\ntest 2"
d.2.e = "  "

[level1]
b.c = sub test

[level1/level2]
a = sub sub test
"""
    )


def test_load() -> None:
    _main = "main"

    input = io.StringIO(
        """\
[main]
a = 1
b.c = test
d.1.e = "test 2\\ntest 2"
d.2.e = "  "

[level1]
b.c = sub test

[level1/level2]
a = sub sub test

[empty]
"""
    )

    assert list(exporter.load_from_file(input, _main)) == [
        ("main/", ""),
        ("main/a", "1"),
        ("main/b.c", "test"),
        ("main/d.1.e", "test 2\ntest 2"),
        ("main/d.2.e", "  "),
        ("main/level1/", ""),
        ("main/level1/b.c", "sub test"),
        ("main/level1/level2/", ""),
        ("main/level1/level2/a", "sub sub test"),
        ("main/empty/", ""),
    ]


def test_section_cleanup() -> None:
    for input, expected in (
        ("", ""),
        (" // / ", ""),
        (" test 1 / test 2 ", "test1/test2"),
        ("test1///test2", "test1/test2"),
        ("/test", "test"),
        ("test/", "test"),
        ("  //   / I'snt This a Test? / // Yes! / // / ", "isntthisatest/yes"),
    ):
        assert exporter.cleanup_section(input) == expected


def test_path_cleanup() -> None:
    for input, expected in (
        ("", ""),
        (" .. . ", ""),
        (" test 1 . test 2 ", "test1.test2"),
        ("test1...test2", "test1.test2"),
        (".test", "test"),
        ("test.", "test"),
        ("  ..   . I'snt This a Test? . .. Yes! . .. . ", "IsntThisaTest.Yes"),
    ):
        assert exporter.cleanup_path(input) == expected
