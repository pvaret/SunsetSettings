from typing import Iterable, Optional, IO


_SECTION_SEPARATOR = "/"
_PATH_SEPARATOR = "."


def normalize(string: str, to_lower: bool = True) -> str:
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

    if len(value) < 2:
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


def cleanup_string(string: str, /, sep: str, to_lower: bool) -> str:
    replacements = (
        (f" {sep}", f"{sep}"),
        (f"{sep} ", f"{sep}"),
        (f"{sep}{sep}", f"{sep}"),
    )

    for from_, to in replacements:
        while from_ in string:
            string = string.replace(from_, to)

    string = sep.join(
        normalize(fragment.strip(), to_lower) for fragment in string.split(sep)
    )

    return string.strip(sep)


def cleanup_section(section: str) -> str:
    return cleanup_string(section, sep=_SECTION_SEPARATOR, to_lower=True)


def cleanup_path(path: str) -> str:
    return cleanup_string(path, sep=_PATH_SEPARATOR, to_lower=False)


# TODO: turn into a function (like dump_to_ini maybe) that takes the data and
# yields lines of text, and then use file.writelines.
def save_to_file(
    file: IO[str],
    data: Iterable[tuple[str, Optional[str]]],
    *,
    blanklines: bool,
):
    need_space = False
    current_section = ""

    def extract_section(path: str) -> tuple[str, str]:
        if _SECTION_SEPARATOR not in path:
            return "", ""

        section, path = path.rsplit(_SECTION_SEPARATOR, 1)
        if _SECTION_SEPARATOR in section:
            _, section = section.split(_SECTION_SEPARATOR, 1)

        return section, path

    for path, dump in data:
        section, path = extract_section(path.strip())
        if not section:
            continue

        if section != current_section:
            current_section = section

            if need_space and blanklines:
                file.write("\n")
            need_space = True

            file.write(f"[{current_section}]\n")

        if path:
            file.write(f"{path} =")
            if dump is not None:
                file.write(f" {maybe_escape(dump)}")
            file.write("\n")


def load_from_file(
    file: IO[str], main: str
) -> Iterable[tuple[str, Optional[str]]]:
    main = normalize(main)

    current_section = ""

    for line in file:
        line = line.strip()

        if not line:
            continue

        if line[0] == "[" and line[-1] == "]":
            current_section = cleanup_section(line[1:-1])
            if not current_section:
                continue

            if current_section != main:
                current_section = main + _SECTION_SEPARATOR + current_section

            yield current_section + _SECTION_SEPARATOR, ""

        elif "=" in line:
            path, dump = line.split("=", 1)
            path = cleanup_path(path)
            dump = dump.strip()
            if path and current_section:
                payload = unescape(dump) if dump else None
                yield (current_section + _SECTION_SEPARATOR + path, payload)
