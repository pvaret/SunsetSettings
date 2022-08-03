import io

import sunset


def test_escape():

    assert sunset.exporter.maybeEscape("") == '""'
    assert sunset.exporter.maybeEscape("123") == "123"
    assert sunset.exporter.maybeEscape("test test") == "test test"
    assert sunset.exporter.maybeEscape("   ") == '"   "'
    assert sunset.exporter.maybeEscape(" a") == '" a"'
    assert sunset.exporter.maybeEscape("a ") == '"a "'
    assert sunset.exporter.maybeEscape('"') == r'"\""'
    assert sunset.exporter.maybeEscape("test\ntest") == r'"test\ntest"'
    assert sunset.exporter.maybeEscape(r"test\test") == r'"test\\test"'


def test_unescape():

    assert sunset.exporter.unescape("") == ""
    assert sunset.exporter.unescape('""') == ""
    assert sunset.exporter.unescape('"') == '"'
    assert sunset.exporter.unescape('"test') == "test"
    assert sunset.exporter.unescape('test"') == "test"
    assert sunset.exporter.unescape("123") == "123"
    assert sunset.exporter.unescape("test \ttest") == "test \ttest"
    assert sunset.exporter.unescape('"   "') == "   "
    assert sunset.exporter.unescape('" a"') == " a"
    assert sunset.exporter.unescape('"a "') == "a "
    assert sunset.exporter.unescape(r'"\""') == '"'
    assert sunset.exporter.unescape(r'"test\ntest"') == "test\ntest"
    assert sunset.exporter.unescape(r'"test\\test"') == r"test\test"


def test_escape_reversible():

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
        assert (
            sunset.exporter.unescape(sunset.exporter.maybeEscape(string))
            == string
        )


def test_save():

    MAIN = "main"

    input = [
        (
            [MAIN],
            [
                ("a", "1"),
                ("b.c", "test"),
                ("d.1.e", "test 2\ntest 2"),
                ("d.2.e", "  "),
            ],
        ),
        (
            [MAIN, "level1"],
            [
                ("b.c", "sub test"),
            ],
        ),
        (
            [MAIN, "level1", "level2"],
            [
                ("a", "sub sub test"),
            ],
        ),
    ]

    file = io.StringIO()

    sunset.exporter.saveToFile(file, input, MAIN, blanklines=True)
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


def test_load():

    MAIN = "main"

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
"""
    )

    assert sunset.exporter.loadFromFile(input, MAIN) == [
        (
            [MAIN],
            [
                ("a", "1"),
                ("b.c", "test"),
                ("d.1.e", "test 2\ntest 2"),
                ("d.2.e", "  "),
            ],
        ),
        (
            [MAIN, "level1"],
            [
                ("b.c", "sub test"),
            ],
        ),
        (
            [MAIN, "level1", "level2"],
            [
                ("a", "sub sub test"),
            ],
        ),
    ]
