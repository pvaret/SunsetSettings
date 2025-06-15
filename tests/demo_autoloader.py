import tempfile
import time

from sunset import Key, Settings, AutoLoader


class DemoSettings(Settings):
    a: Key[int] = Key(default=-1)


if __name__ == "__main__":

    def report_value_changed(value: int) -> None:
        print(f"    -> Setting value changed: a={value}")
        print()

    settings = DemoSettings()
    settings.a.onValueChangeCall(report_value_changed)

    with tempfile.NamedTemporaryFile(delete=False, mode="w+", encoding="utf-8") as file:
        with AutoLoader(settings, file.name) as loader:
            for i in range(1, 11):
                time.sleep(0.5)

                contents = f"[main]\na = {i}\n"
                print("Writing new settings file:")
                print()
                print(contents)

                file.seek(0)
                file.write(contents)
                file.truncate()
                file.flush()

                # The autoloader should detect that the file was modified, and trigger a
                # load in the background. When it does, the value of settings.a will be
                # updated, and the callback triggered.

                time.sleep(2.5)
