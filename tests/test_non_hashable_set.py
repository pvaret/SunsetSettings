from collections.abc import MutableSet
from typing import Any

from sunset import sets


class Dummy:
    pass


class TestNonHashableSet:
    def test_mutableset(self) -> None:
        s: MutableSet[Any] = sets.NonHashableSet()
        item = Dummy()

        assert item not in s
        assert len(s) == 0
        assert list(s) == []

        s.add(item)
        s.add(item)
        assert item in s
        assert len(s) == 1
        assert list(s) == [item]

        s.discard(item)
        assert item not in s
        assert len(s) == 0
        assert list(s) == []

    def test_persistence(self) -> None:
        s: MutableSet[Any] = sets.NonHashableSet()
        item = Dummy()

        s.add(item)
        assert len(s) == 1

        del item
        assert len(s) == 1


class TestWeakNonHashableSet:
    def test_mutableset(self) -> None:
        s: MutableSet[Any] = sets.WeakNonHashableSet()
        item = Dummy()

        assert item not in s
        assert len(s) == 0
        assert list(s) == []

        s.add(item)
        s.add(item)
        assert item in s
        assert len(s) == 1
        assert list(s) == [item]

        s.discard(item)
        assert item not in s
        assert len(s) == 0
        assert list(s) == []

    def test_persistence(self) -> None:
        s: MutableSet[Any] = sets.WeakNonHashableSet()
        item = Dummy()

        s.add(item)
        assert len(s) == 1

        del item
        assert len(s) == 0
