from collections import defaultdict
from collections.abc import Callable, Iterable, MutableMapping
from typing import TypeVar

_T = TypeVar("_T")


def collate_by_prefix(
    fields: Iterable[tuple[str, _T]], splitter: Callable[[str], tuple[str, str]]
) -> MutableMapping[str, list[tuple[str, _T]]]:
    collated: dict[str, list[tuple[str, _T]]] = defaultdict(list)

    for path, value in fields:
        prefix, suffix = splitter(path)
        collated[prefix].append((suffix, value))

    return collated


def split_on(pivot: str) -> Callable[[str], tuple[str, str]]:
    def splitter(string: str) -> tuple[str, str]:
        before, after, *_ = [*string.split(pivot, maxsplit=1), ""]
        return before, after

    return splitter
