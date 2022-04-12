import pytest

import sunset


class TestCallbackRegistry:
    def test_function(self):

        call_args: list[str] = []

        def test(value: str) -> None:
            call_args.append(value)

        reg: sunset.CallbackRegistry[str] = sunset.CallbackRegistry()

        assert len(reg) == 0
        reg.callAll("not added")
        assert call_args == []

        reg.add(test)
        assert len(reg) == 1
        assert test in reg
        reg.callAll("added")
        assert call_args == ["added"]

        del test
        assert len(reg) == 0
        reg.callAll("not added either")
        assert call_args == ["added"]

    def test_method(self):

        call_args: list[str] = []

        class Test:
            def test(self, value: str) -> None:
                call_args.append(value)

        reg: sunset.CallbackRegistry[str] = sunset.CallbackRegistry()

        t = Test()

        assert len(reg) == 0
        assert t.test not in reg

        reg.add(t.test)
        assert len(reg) == 1
        assert t.test in reg
        reg.callAll("added")
        assert call_args == ["added"]

        del t
        assert len(reg) == 0
        reg.callAll("not added")
        assert call_args == ["added"]

    def test_discard_function(self):
        def test(_: int) -> None:
            pass

        reg: sunset.CallbackRegistry[int] = sunset.CallbackRegistry()

        reg.add(test)
        assert test in reg
        reg.discard(test)
        assert test not in reg

    def test_discard_method(self):
        class Test:
            def test(self, _: int) -> None:
                pass

        t = Test()

        reg: sunset.CallbackRegistry[int] = sunset.CallbackRegistry()

        reg.add(t.test)
        assert t.test in reg
        reg.discard(t.test)
        assert t.test not in reg

    def test_pop(self):
        def test(_: bool):
            pass

        reg: sunset.CallbackRegistry[bool] = sunset.CallbackRegistry()

        reg.add(test)
        assert test in reg
        other = reg.pop()
        assert test not in reg
        assert other is test

    def test_function_added_once(self):

        call_args: list[str] = []

        def test(value: str) -> None:
            call_args.append(value)

        reg: sunset.CallbackRegistry[str] = sunset.CallbackRegistry()

        reg.add(test)
        assert len(reg) == 1
        reg.add(test)
        assert len(reg) == 1

        reg.callAll("once")
        assert call_args == ["once"]

    def test_same_method_added_once(self):

        call_args: list[str] = []

        class Test:
            def test(self, value: str) -> None:
                call_args.append(value)

        reg: sunset.CallbackRegistry[str] = sunset.CallbackRegistry()

        t = Test()

        reg.add(t.test)
        assert len(reg) == 1
        reg.add(t.test)
        assert len(reg) == 1

        reg.callAll("once")
        assert call_args == ["once"]

    def test_non_hashable_element(self):
        class Test(list[int]):
            def __init__(self) -> None:

                super().__init__()

                self.value = 0

            def test(self, value: int) -> None:
                self.value = value

        t = Test()

        with pytest.raises(TypeError):

            # Prove that type Test is not hashable.

            hash(t)

        reg: sunset.CallbackRegistry[int] = sunset.CallbackRegistry()

        reg.add(t.test)
        reg.callAll(42)

        assert t.value == 42

    def test_different_method_added_twice(self):

        call_args: list[str] = []

        class Test:
            def test(self, value: str) -> None:
                call_args.append(value)

        reg: sunset.CallbackRegistry[str] = sunset.CallbackRegistry()

        t1 = Test()
        t2 = Test()

        reg.add(t1.test)
        assert len(reg) == 1
        reg.add(t2.test)
        assert len(reg) == 2

        reg.callAll("twice")
        assert call_args == ["twice", "twice"]
