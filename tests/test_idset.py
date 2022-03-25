from typing import Any, MutableSet

import sunset


class Dummy:
    pass


class TestIdSet:
    def test_mutableset(self):

        s: MutableSet[Any] = sunset.idset.IdSet()
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

    def test_persistence(self):

        s: MutableSet[Any] = sunset.idset.IdSet()
        item = Dummy()

        s.add(item)
        assert len(s) == 1

        del item
        assert len(s) == 1


class TestWeakIdSet:
    def test_mutableset(self):
        s: MutableSet[Any] = sunset.idset.WeakIdSet()
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

    def test_persistence(self):

        s: MutableSet[Any] = sunset.idset.WeakIdSet()
        item = Dummy()

        s.add(item)
        assert len(s) == 1

        del item
        assert len(s) == 0
