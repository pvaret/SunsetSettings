from typing import Sequence, TextIO


def normalize(input: str) -> str:

    ret = ""
    for c in input:
        if c.isalnum() or c in ("-", "_"):
            ret += c
    return ret.lower()


def maybeEscape(value: str) -> str:

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


def saveToFile(
    file: TextIO,
    data: Sequence[tuple[Sequence[str], Sequence[tuple[str, str]]]],
    main: str,
    *,
    blanklines: bool,
):

    need_space = False
    main = normalize(main)

    for hierarchy, dump in data:

        hierarchy = list(map(normalize, hierarchy))
        if len(hierarchy) > 1 and hierarchy[0] == main:
            hierarchy = hierarchy[1:]

        if need_space and blanklines:
            file.write("\n")

        assert all("/" not in elt for elt in hierarchy)

        if dump:
            need_space = True
            section = "/".join(hierarchy)
            file.write(f"[{section}]\n")

            for key, value in dump:
                key = key.strip()
                value = maybeEscape(value)
                if key:
                    file.write(f"{key} = {value}\n")


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
