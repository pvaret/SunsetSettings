from collections.abc import Callable

import pytest

from sunset import sets


class TestWeakCallableSet:
    def test_function(self) -> None:
        def test(_: str) -> None:
            pass

        reg: sets.WeakCallableSet[Callable[[str], None]] = sets.WeakCallableSet()

        assert len(reg) == 0

        reg.add(test)
        assert len(reg) == 1
        assert test in reg

        del test
        assert len(reg) == 0

    def test_method(self) -> None:
        class Test:
            def test(self, _: str) -> None:
                pass

        reg: sets.WeakCallableSet[Callable[[str], None]] = sets.WeakCallableSet()

        t = Test()

        assert len(reg) == 0
        assert t.test not in reg

        reg.add(t.test)
        assert len(reg) == 1
        assert t.test in reg

        del t
        assert len(reg) == 0

    def test_discard_function(self) -> None:
        def test(_: int) -> None:
            pass

        reg: sets.WeakCallableSet[Callable[[int], None]] = sets.WeakCallableSet()

        reg.add(test)
        assert test in reg
        reg.discard(test)
        assert test not in reg

    def test_discard_method(self) -> None:
        class Test:
            def test(self, _: int) -> None:
                pass

        t = Test()

        reg: sets.WeakCallableSet[Callable[[int], None]] = sets.WeakCallableSet()

        reg.add(t.test)
        assert t.test in reg
        reg.discard(t.test)
        assert t.test not in reg

    def test_pop(self) -> None:
        def test(_: bool) -> None:
            pass

        reg: sets.WeakCallableSet[Callable[[bool], None]] = sets.WeakCallableSet()

        reg.add(test)
        assert test in reg
        other = reg.pop()
        assert test not in reg
        assert other is test

    def test_function_added_once(self) -> None:
        def test(_: str) -> None:
            pass

        reg: sets.WeakCallableSet[Callable[[str], None]] = sets.WeakCallableSet()

        reg.add(test)
        assert len(reg) == 1
        reg.add(test)
        assert len(reg) == 1

    def test_same_method_added_once(self) -> None:
        class Test:
            def test(self, _: str) -> None:
                pass

        reg: sets.WeakCallableSet[Callable[[str], None]] = sets.WeakCallableSet()

        t = Test()

        reg.add(t.test)
        assert len(reg) == 1
        reg.add(t.test)
        assert len(reg) == 1

    def test_non_hashable_element(self) -> None:
        class Test(list[int]):
            def test(self, _: int) -> None:
                pass

        t = Test()

        with pytest.raises(TypeError):
            # Prove that type Test is not hashable.

            hash(t)

        reg: sets.WeakCallableSet[Callable[[int], None]] = sets.WeakCallableSet()

        reg.add(t.test)
        assert t.test in reg

    def test_different_method_added_twice(self) -> None:
        class Test:
            def test(self, _: str) -> None:
                pass

        reg: sets.WeakCallableSet[Callable[[str], None]] = sets.WeakCallableSet()

        t1 = Test()
        t2 = Test()

        reg.add(t1.test)
        assert len(reg) == 1
        reg.add(t2.test)
        assert len(reg) == 2
