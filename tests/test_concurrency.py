import threading
import time
import typing

# TODO: Remove when it's time to deprecate Python 3.9 support.
import typing_extensions

from sunset import Key, List, Settings

_P = typing_extensions.ParamSpec("_P")

_THREAD_COUNT = 16
_DURATION = 0.1  # seconds
_ATTEMPTS = 5


def run_threaded(
    func: typing.Callable[typing_extensions.Concatenate[int, _P], None],
    thread_count: int = _THREAD_COUNT,
    duration: float = _DURATION,
    *args: _P.args,
    **kwargs: _P.kwargs,
) -> None:
    exceptions: list[Exception] = []
    deadline: float = time.monotonic() + duration
    barrier = threading.Barrier(parties=thread_count)

    def executor(thread_id: int) -> None:
        barrier.wait()
        try:
            while time.monotonic() < deadline:
                func(thread_id, *args, **kwargs)
        except Exception as e:
            exceptions.append(e)

    threads = [
        threading.Thread(target=executor, args=[i]) for i in range(thread_count)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    if exceptions:
        raise exceptions[0]


class TestKeyConcurrency:
    def test_set_clear(self) -> None:
        str_key = Key("default value")

        def clear_and_set_key(thread_id: int) -> None:
            str_key.clear()
            str_key.set(str(thread_id))

        for _ in range(_ATTEMPTS):
            run_threaded(clear_and_set_key)

            assert str_key.isSet()
            assert str_key.get() != "default value"

        def set_and_clear_key(thread_id: int) -> None:
            str_key.set(str(thread_id))
            str_key.clear()

        for _ in range(_ATTEMPTS):
            run_threaded(set_and_clear_key)

            assert not str_key.isSet()
            assert str_key.get() == "default value"

    def test_update_value(self) -> None:
        count = [0]
        int_key = Key(0)
        count_lock = threading.Lock()

        def updater(value: int) -> int:
            return value + 1

        def update_key(_unused: int) -> None:
            int_key.updateValue(updater)
            with count_lock:
                count[0] += 1

        for _ in range(_ATTEMPTS):
            run_threaded(update_key)

        assert int_key.get() == count[0]

    def test_parenting(self) -> None:
        parent_key = Key("")
        parent_key.set("parent")
        str_key = Key("")

        def set_parent(thread_id: int) -> None:
            str_key.setParent(None)
            str_key.setParent(parent_key)

        for _ in range(_ATTEMPTS):
            run_threaded(set_parent)

            assert str_key.parent() is parent_key
            assert str_key.get() == "parent"


class TestListConcurrency:
    def test_append_pop(self) -> None:
        _start_items: int = 10

        key_list = List(Key(""))
        for i in range(_start_items):
            key_list.append(Key(f"default {i}"))

        def update_list(thread_id: int, key_list: List[Key[str]]) -> None:
            value = str(thread_id)
            if (fashion := thread_id % 4) == 0:
                key_list.append(Key(value))
            elif fashion == 1:
                key_list += [Key(value)]
            elif fashion == 2:
                key_list[0:0] = [Key(value)]
            elif fashion == 3:
                key_list.insert(0, Key(value))

            if (fashion := (thread_id << 2) % 2) == 0:
                key_list.pop()
            elif fashion == 1:
                del key_list[0]

            assert len(key_list) >= _start_items

        for _ in range(_ATTEMPTS):
            run_threaded(update_list, key_list=key_list)

            assert len(key_list) == _start_items
            for i, item in enumerate(key_list):
                assert item.container() is key_list
                expected_label = key_list._labelForIndex(i)  # type: ignore
                assert item.fieldLabel() == expected_label


class TestSettingsConcurrency:
    def test_settings_names(self) -> None:
        class TestSettings(Settings):
            pass

        settings = TestSettings()
        sections = [settings.newSection(str(i)) for i in range(16)]

        def rename_section(
            thread_id: int, sections: list[TestSettings]
        ) -> None:
            section = sections[thread_id % len(sections)]
            section.setSectionName("test")
            section.setSectionName("section")

        for _ in range(_ATTEMPTS):
            run_threaded(rename_section, sections=sections)

            assert len(list(settings.sections())) == len(sections)
            assert len(
                set(section.sectionName() for section in settings.sections())
            ) == len(sections)
