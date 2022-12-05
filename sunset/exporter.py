from typing import Iterable, Sequence, TextIO


_SECTION_SEPARATOR = "/"


def normalize(input: str) -> str:

    ret = ""
    for c in input:
        if c.isalnum() or c in ("-", "_"):
            ret += c
    return ret.lower()


def maybe_escape(value: str) -> str:

    if (
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


def unescape(value: str):

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
            else:
                ret += c

        else:
            if c == "n":
                ret += "\n"
            else:
                ret += c
            escaped = False

    return ret


# TODO: turn into a function (like dump_to_ini maybe) that takes the data and
# yields lines of text, and then use file.writelines.
def save_to_file(
    file: TextIO,
    data: Iterable[tuple[str, str]],
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
        if not path or not section:
            continue

        if section != current_section:

            current_section = section

            if need_space and blanklines:
                file.write("\n")
            need_space = True

            file.write(f"[{current_section}]\n")

        file.write(f"{path} = {maybe_escape(dump)}\n")


def loadFromFile(
    file: TextIO, main: str
) -> Sequence[tuple[Sequence[str], Sequence[tuple[str, str]]]]:

    ret: list[tuple[Sequence[str], Sequence[tuple[str, str]]]] = []

    hierarchy: list[str] = []
    keyvalues: list[tuple[str, str]] = []
    main = normalize(main)

    for line in file:
        line = line.strip()

        if not line:
            continue

        if line[0] == "[" and line[-1] == "]":

            line = line[1:-1]
            if not line:
                keyvalues = []
                continue

            hierarchy = [
                name
                for item in line.split("/")
                if (name := normalize(item.strip()))
            ]

            if not hierarchy:
                keyvalues = []
                continue

            if hierarchy[0] != main:
                hierarchy = [main] + hierarchy

            keyvalues = []
            ret.append((hierarchy, keyvalues))

        elif "=" in line:

            k, v = line.split("=", 1)
            k = k.strip()
            v = unescape(v.strip())
            if k:
                keyvalues.append((k, v))

    return ret
