import io

from sunset import exporter


def test_escape():

    assert exporter.maybeEscape("") == '""'
    assert exporter.maybeEscape("123") == "123"
    assert exporter.maybeEscape("test test") == "test test"
    assert exporter.maybeEscape("   ") == '"   "'
    assert exporter.maybeEscape(" a") == '" a"'
    assert exporter.maybeEscape("a ") == '"a "'
    assert exporter.maybeEscape('"') == r'"\""'
    assert exporter.maybeEscape("test\ntest") == r'"test\ntest"'
    assert exporter.maybeEscape(r"test\test") == r'"test\\test"'


def test_unescape():

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
        assert exporter.unescape(exporter.maybeEscape(string)) == string


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

    exporter.saveToFile(file, input, MAIN, blanklines=True)
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

    assert exporter.loadFromFile(input, MAIN) == [
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
