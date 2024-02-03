from pytest_mock import MockerFixture

from sunset.notifier import Notifier


class TestNotifier:
    def test_function_is_called(self, mocker: MockerFixture) -> None:
        callback = mocker.stub()

        notifier = Notifier()

        notifier.add(callback)

        callback.assert_not_called()
        notifier.trigger("test", 42)
        callback.assert_called_once_with("test", 42)

    def test_function_added_multiple_times_is_called_once(
        self, mocker: MockerFixture
    ) -> None:
        notifier = Notifier()

        callback = mocker.stub()

        notifier.add(callback)
        notifier.add(callback)
        notifier.add(callback)

        notifier.trigger("test")

        callback.assert_called_once_with("test")

    def test_all_added_functions_called(self, mocker: MockerFixture) -> None:
        notifier = Notifier()

        callbacks = [mocker.stub() for _ in range(10)]

        [notifier.add(callback) for callback in callbacks]

        notifier.trigger("test")

        [callback.assert_called_once_with("test") for callback in callbacks]

    def test_discarded_function_is_no_longer_called(
        self, mocker: MockerFixture
    ) -> None:
        notifier = Notifier()

        callback1 = mocker.stub()
        callback2 = mocker.stub()

        notifier.add(callback1)
        notifier.add(callback2)
        notifier.discard(callback1)

        notifier.trigger("test")

        callback1.assert_not_called()
        callback2.assert_called_once_with("test")

    def test_discarding_non_member_is_no_op(self) -> None:
        notifier = Notifier()

        notifier.discard(lambda: None)

    def test_notifier_doesnt_keep_reference_to_function(
        self, mocker: MockerFixture
    ) -> None:
        notifier = Notifier()

        test_list: list[str] = []

        def test(value: str) -> None:
            test_list.append(value)

        notifier.add(test)
        notifier.trigger("test")

        assert test_list == ["test"]

        test_list.clear()
        del test
        notifier.trigger("test")

        assert test_list == []

    def test_inhibit(self, mocker: MockerFixture) -> None:
        notifier = Notifier()

        callback = mocker.stub()

        notifier.add(callback)

        with notifier.inhibit():
            notifier.trigger("test")

        callback.assert_not_called()
