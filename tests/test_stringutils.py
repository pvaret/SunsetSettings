# pyright: reportMissingTypeStubs=false

from typing import Any
from pytest_case import case

from sunset.stringutils import collate_by_prefix, split_on


@case("empty input", string="", expected=("", ""))
@case("no split point", string="a", expected=("a", ""))
@case("one split point", string="a.b", expected=("a", "b"))
@case("two split points", string="a.b.c", expected=("a", "b.c"))
@case("split point before", string=".a", expected=("", "a"))
@case("two split points before", string="..a", expected=("", ".a"))
@case("split point after", string="a.", expected=("a", ""))
@case("split points before and after", string=".a.", expected=("", "a."))
def test_split_on(string: str, expected: tuple[str, str]) -> None:
    assert split_on(".")(string) == expected


_SENTINEL = "test"


@case("empty inputs", inputs=[], expected={})
@case(
    "empty prefixes",
    inputs=[
        ("", _SENTINEL),
        ("", _SENTINEL),
    ],
    expected={
        "": [
            ("", _SENTINEL),
            ("", _SENTINEL),
        ],
    },
)
@case(
    "no split point",
    inputs=[
        ("a", _SENTINEL),
        ("b", _SENTINEL),
    ],
    expected={
        "a": [("", _SENTINEL)],
        "b": [("", _SENTINEL)],
    },
)
@case(
    "one split point",
    inputs=[
        ("a.b", _SENTINEL),
        ("a.c", _SENTINEL),
    ],
    expected={
        "a": [
            ("b", _SENTINEL),
            ("c", _SENTINEL),
        ],
    },
)
@case(
    "two split points",
    inputs=[
        ("a.b.c", _SENTINEL),
        ("a.b.d", _SENTINEL),
        ("x.b.c", _SENTINEL),
    ],
    expected={
        "a": [
            ("b.c", _SENTINEL),
            ("b.d", _SENTINEL),
        ],
        "x": [
            ("b.c", _SENTINEL),
        ],
    },
)
@case(
    "variable split points",
    inputs=[
        ("a", _SENTINEL),
        ("a.b", _SENTINEL),
        ("a.b.c", _SENTINEL),
        ("b.c", _SENTINEL),
    ],
    expected={
        "a": [
            ("", _SENTINEL),
            ("b", _SENTINEL),
            ("b.c", _SENTINEL),
        ],
        "b": [
            ("c", _SENTINEL),
        ],
    },
)
def test_collate_by_prefix(
    inputs: list[tuple[str, Any]], expected: dict[str, list[tuple[str, Any]]]
) -> None:
    splitter = split_on(".")

    assert collate_by_prefix(inputs, splitter=splitter) == expected
