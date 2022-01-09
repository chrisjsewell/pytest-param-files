"""Main module"""
from dataclasses import dataclass
import difflib
from pathlib import Path
import re
from typing import Any, List, Tuple, Union, cast

import pytest


@dataclass
class ParamTestData:
    """Data class for a single test."""

    line: int
    """The line number in the source file."""
    title: str
    """The title of the test."""
    description: str
    """The description of the test."""
    content: Any
    """The input content of the test."""
    expected: Any
    """The expected result of the test."""
    fmt: "FormatAbstract"
    """The format of the source file."""

    def assert_expected(self, actual: Any, **kwargs: Any) -> None:
        """Assert the actual result of the test.

        :param actual: The actual result of the test.
        :param kwargs: Additional keyword arguments to parse to the format.
        """
        __tracebackhide__ = True
        self.fmt.assert_expected(actual, self, **kwargs)


def with_parameters(
    path: Union[str, Path],
    fmt: str = "dot",
    encoding="utf8",
    fixture_name: str = "file_params",
) -> callable:
    """Return a pytest parametrize decorator for a fixture file.

    :param path: Path to the fixture file.
    :param format: Format of the fixture file.
    :param encoding: Encoding of the fixture file.
    :param fixture_name: Name of the fixture parameter.
    """
    path = Path(path)
    # check if the file exists
    if not path.is_file():
        raise FileNotFoundError(f"File {path} not found.")

    # select read format
    if fmt != "dot":
        raise NotImplementedError("Currently only dot format is supported.")
    fmt_inst = DotFormat(path, encoding)

    # read fixture file
    tests = fmt_inst.read()

    # create the objects to return
    file_params = [ParamTestData(*test, fmt=fmt_inst) for test in tests]

    # create pytest parametrize ids
    ids = [f"{p.line}-{p.title}" for p in file_params]

    # return the decorator
    return pytest.mark.parametrize(
        fixture_name,
        file_params,
        ids=ids,
    )


_TITLE_RE = re.compile(r"^\s*\[(?P<title>\S+)\]\s*(?P<description>.*)$")


class FormatAbstract:
    """Abstract class for a format."""

    def __init__(self, path: Path, encoding: str = "utf8") -> None:
        """Initialize the format.

        :param path: Path to the fixture file.
        :param encoding: Encoding of the fixture file.
        """
        self.path = path
        self.encoding = encoding

    def read(self) -> List[Tuple[int, str, str, str, str]]:
        """Read the fixture file and return a list of test data.

        :return: List of test data.
        """
        raise NotImplementedError()

    def assert_expected(self, actual: Any, data: ParamTestData, **kwargs) -> None:
        """Assert the actual result matches the expected.

        :param actual: Actual result.
        """
        raise NotImplementedError()


class DotFormat(FormatAbstract):
    """Dot file format."""

    name = "dot"

    def read(self) -> List[Tuple[int, str, str, str, str]]:
        text = self.path.read_text(encoding=self.encoding)
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

    def assert_expected(
        self,
        actual: str,
        data: ParamTestData,
        rstrip: bool = False,
        rstrip_lines: bool = False,
    ) -> None:
        """Assert the actual result of the test.

        :param rstrip: Whether to apply `str.rstrip` to actual and expected before comparing.
        :param rstrip_lines: Whether to apply `str.rstrip`
            to each line of actual and expected before comparing.
        """
        __tracebackhide__ = True
        expected = cast(str, data.expected)
        if rstrip:
            actual = actual.rstrip()
            expected = expected.rstrip()
        if rstrip_lines:
            actual = "\n".join(line.rstrip() for line in actual.splitlines())
            expected = "\n".join(line.rstrip() for line in expected.splitlines())

        try:
            assert actual == expected
        except AssertionError:
            raise AssertionError(self._diff(actual, expected, data))

    def _diff(self, actual: str, expected: str, data: ParamTestData) -> str:
        """Return a diff string between actual and expected."""
        diff_lines = list(
            difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile=f"{self.path}:{data.line}",
                tofile="(actual)",
                lineterm="",
            )
        )
        if len(diff_lines) <= 500:
            return "Actual does not match expected\n" + "\n".join(diff_lines)
        else:
            return (
                f"Diff too big to show ({len(diff_lines)}):" f"{self.path}:{data.line}"
            )
