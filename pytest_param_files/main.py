"""Main module"""
from pathlib import Path
import re
from typing import List, Tuple, Union

import pytest


def with_parameters(
    path: Union[str, Path], fmt: str = "dot", encoding="utf8"
) -> callable:
    """Return a pytest parametrize decorator for a fixture file.

    :param path: Path to the fixture file.
    :param format: Format of the fixture file.
    :param encoding: Encoding of the fixture file.
    """
    path = Path(path)
    # check if the file exists
    if not path.is_file():
        raise FileNotFoundError(f"File {path} not found.")

    # select read format
    if fmt != "dot":
        raise NotImplementedError("Currently only dot format is supported.")
    read_function = read_dot_file

    # read fixture file
    tests = read_function(path, encoding)

    # return the decorator
    return pytest.mark.parametrize(
        "line,title,description,content,expected",
        tests,
        ids=[f"{i[0]}-{i[1]}" for i in tests],
    )


_TITLE_RE = re.compile(r"^\s*\[(?P<title>\S+)\]\s*(?P<description>.*)$")


def read_dot_file(path: Path, encoding: str) -> List[Tuple[int, str, str, str, str]]:
    """Read a dot file and return a list of tuples.

    :param path: Path to the dot file.
    :param encoding: Encoding of the dot file.

    :return: List of tuples (line, title, description, content, expected).
    """
    text = path.read_text(encoding=encoding)
    tests = []
    section = 0
    last_pos = 0
    lines = text.splitlines(keepends=True)
    for i in range(len(lines)):
        if lines[i].rstrip() == ".":
            if section == 0:
                first_line = lines[i - 1].strip()
                match = _TITLE_RE.match(first_line)
                if match:
                    title = match.group("title")
                    description = match.group("description")
                else:
                    title = first_line
                    description = ""
                tests.append([i, title, description])
                section = 1
            elif section == 1:
                tests[-1].append("".join(lines[last_pos + 1 : i]))
                section = 2
            elif section == 2:
                tests[-1].append("".join(lines[last_pos + 1 : i]))
                section = 0

            last_pos = i
    return tests
