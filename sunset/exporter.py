from collections.abc import Iterable
from typing import IO

_LAYER_SEPARATOR = "/"
_PATH_SEPARATOR = "."


def normalize(string: str, *, to_lower: bool = True) -> str:
    ret = ""
    for c in string:
        if c.isalnum() or c in ("-", "_"):
            ret += c
    return ret.lower() if to_lower else ret


def maybe_escape(value: str) -> str:
    if (
        # pylint: disable-next=too-many-boolean-expressions
        len(value) == 0
        or '"' in value
        or "\\" in value
        or "\n" in value
        or value[0].isspace()
        or value[-1].isspace()
    ):
        ret = ""
        for c in value:
            if c == '"':
                ret += r"\""
            elif c == "\n":
                ret += r"\n"
            elif c == "\\":
                ret += "\\\\"
            else:
                ret += c

        return '"' + ret + '"'

    return value


def unescape(value: str) -> str:
    if '"' not in value and "\\" not in value:
        return value

    if len(value) <= 1:
        return value

    if value[0] == '"':
        value = value[1:]

    if value[-1] == '"':
        value = value[:-1]

    ret = ""
    escaped = False

    for c in value:
        if not escaped:
            if c == "\\":
                escaped = True
                continue

            ret += c

        else:
            if c == "n":
                ret += "\n"
            else:
                ret += c
            escaped = False

    return ret


def cleanup_string(string: str, /, sep: str, *, to_lower: bool) -> str:
    replacements = (
        (f" {sep}", f"{sep}"),
        (f"{sep} ", f"{sep}"),
        (f"{sep}{sep}", f"{sep}"),
    )

    for from_, to in replacements:
        while from_ in string:
            string = string.replace(from_, to)

    string = sep.join(
        normalize(fragment.strip(), to_lower=to_lower) for fragment in string.split(sep)
    )

    return string.strip(sep)


def cleanup_layer(layer: str) -> str:
    return cleanup_string(layer, sep=_LAYER_SEPARATOR, to_lower=True)


def cleanup_path(path: str) -> str:
    return cleanup_string(path, sep=_PATH_SEPARATOR, to_lower=False)


def save_to_file(
    file: IO[str],
    data: Iterable[tuple[str, str | None]],
    *,
    blanklines: bool,
    main: str = "main",
) -> None:
    need_space = False
    current_layer = ""

    def extract_layer(path: str) -> tuple[str, str]:
        if _LAYER_SEPARATOR not in path:
            return main, path

        layer, path = path.rsplit(_LAYER_SEPARATOR, 1)
        return layer, path

    for full_path, dump in data:
        layer, path = extract_layer(full_path.strip())
        if not layer:
            continue

        if layer != current_layer:
            current_layer = layer

            if need_space and blanklines:
                file.write("\n")
            need_space = True

            file.write(f"[{current_layer}]\n")

        if path:
            file.write(f"{path} =")
            if dump is not None:
                file.write(f" {maybe_escape(dump)}")
            file.write("\n")


def load_from_file(file: IO[str], main: str) -> Iterable[tuple[str, str | None]]:
    main = normalize(main)

    current_layer = ""

    for full_line in file:
        line = full_line.strip()

        if not line:
            continue

        if line[0] == "[" and line[-1] == "]":
            current_layer = cleanup_layer(line[1:-1])
            if not current_layer:
                continue

            if current_layer == main:
                current_layer = ""

            if current_layer:
                yield current_layer + _LAYER_SEPARATOR, ""

        elif "=" in line:
            path, dump = line.split("=", 1)
            path = cleanup_path(path)
            dump = dump.strip()
            if path:
                payload = unescape(dump) if dump else None
                if current_layer:
                    path = _LAYER_SEPARATOR.join((current_layer, path))
                yield (path, payload)
