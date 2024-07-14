import io

from pytest_mock import MockerFixture

from sunset import Bunch, Key, List, Settings


class ExampleSettings(Settings):
    class ExampleBunch(Bunch):
        c = Key(default=0)
        d = Key(default=False)

    inner_bunch = ExampleBunch()
    bunch_list = List(ExampleBunch())
    key_list = List(Key(default=""))

    a = Key(default="")
    b = Key(default="")


def test_loaded_notification(mocker: MockerFixture) -> None:
    settings = ExampleSettings()
    settings.key_list.appendOne()

    settings.onLoadedCall(callback_settings := mocker.stub())
    settings.a.onLoadedCall(callback_a := mocker.stub())
    settings.key_list.onLoadedCall(callback_key_list := mocker.stub())
    settings.key_list[0].onLoadedCall(callback_key_list_0 := mocker.stub())
    settings.inner_bunch.onLoadedCall(callback_inner_bunch := mocker.stub())
    settings.inner_bunch.c.onLoadedCall(callback_inner_bunch_c := mocker.stub())

    callback_settings.assert_not_called()
    callback_a.assert_not_called()
    callback_key_list.assert_not_called()
    callback_key_list_0.assert_not_called()
    callback_inner_bunch.assert_not_called()
    callback_inner_bunch_c.assert_not_called()

    settings.load(io.StringIO())

    callback_settings.assert_called_once()
    callback_a.assert_called_once()
    callback_key_list.assert_called_once()
    callback_key_list_0.assert_called_once()
    callback_inner_bunch.assert_called_once()
    callback_inner_bunch_c.assert_called_once()
