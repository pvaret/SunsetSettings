from typing import Any

import pytest

from sunset.stringutils import collate_by_prefix, split_on


@pytest.mark.parametrize(
    "string, expected",
    [
        ("", ("", "")),
        ("a", ("a", "")),
        ("a.b", ("a", "b")),
        ("a.b.c", ("a", "b.c")),
        (".a", ("", "a")),
        ("..a", ("", ".a")),
        ("a.", ("a", "")),
        (".a.", ("", "a.")),
    ],
)
def test_split_on(string: str, expected: tuple[str, str]) -> None:
    assert split_on(".")(string) == expected


_SENTINEL = "test"


@pytest.mark.parametrize(
    "inputs, expected",
    [
        ([], {}),
        ([("", _SENTINEL), ("", _SENTINEL)], {"": [("", _SENTINEL), ("", _SENTINEL)]}),
        (
            [("a", _SENTINEL), ("b", _SENTINEL)],
            {"a": [("", _SENTINEL)], "b": [("", _SENTINEL)]},
        ),
        (
            [("a.b", _SENTINEL), ("a.c", _SENTINEL)],
            {"a": [("b", _SENTINEL), ("c", _SENTINEL)]},
        ),
        (
            [("a.b.c", _SENTINEL), ("a.b.d", _SENTINEL), ("x.b.c", _SENTINEL)],
            {
                "a": [("b.c", _SENTINEL), ("b.d", _SENTINEL)],
                "x": [("b.c", _SENTINEL)],
            },
        ),
        (
            [
                ("a", _SENTINEL),
                ("a.b", _SENTINEL),
                ("a.b.c", _SENTINEL),
                ("b.c", _SENTINEL),
            ],
            {
                "a": [("", _SENTINEL), ("b", _SENTINEL), ("b.c", _SENTINEL)],
                "b": [("c", _SENTINEL)],
            },
        ),
    ],
)
def test_collate_by_prefix(
    inputs: list[tuple[str, Any]], expected: dict[str, list[tuple[str, Any]]]
) -> None:
    splitter = split_on(".")

    assert collate_by_prefix(inputs, splitter=splitter) == expected
