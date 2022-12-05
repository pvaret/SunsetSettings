import io

from sunset import exporter


def test_escape():

    assert exporter.maybe_escape("") == '""'
    assert exporter.maybe_escape("123") == "123"
    assert exporter.maybe_escape("test test") == "test test"
    assert exporter.maybe_escape("   ") == '"   "'
    assert exporter.maybe_escape(" a") == '" a"'
    assert exporter.maybe_escape("a ") == '"a "'
    assert exporter.maybe_escape('"') == r'"\""'
    assert exporter.maybe_escape("test\ntest") == r'"test\ntest"'
    assert exporter.maybe_escape(r"test\test") == r'"test\\test"'


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
        assert exporter.unescape(exporter.maybe_escape(string)) == string


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
