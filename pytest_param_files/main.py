"""Main module"""
from dataclasses import dataclass
import difflib
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Tuple, Union, cast

if TYPE_CHECKING:
    from _pytest.python import Metafunc


def pytest_addoption(parser):
    """Register command line options to pytest."""
    group = parser.getgroup("pytest_param_files")
    group.addoption(
        "--regen-file-failure",
        action="store_true",
        dest="param_files_regen",
        default=False,
        help="Regenerate expected sections on test failure.",
    )


def pytest_configure(config):
    """Register markers to pytest."""
    config.addinivalue_line(
        "markers",
        "param_file(path, fmt=dot, encoding=utf8, **kwargs): "
        "call a test function multiple times, parametrized by a fixture file (Path|str).",
    )


def pytest_generate_tests(metafunc: "Metafunc") -> None:
    """Generate tests for a pytest param_file decorator."""
    for marker in metafunc.definition.iter_markers(name="param_file"):
        param_files_regen = metafunc.config.getoption("param_files_regen")
        fixture_name, file_params, ids = create_parameters(
            *marker.args, **marker.kwargs, regen_on_failure=param_files_regen
        )
        metafunc.parametrize(argnames=fixture_name, argvalues=file_params, ids=ids)


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
    index: int
    """The index of the test in the file."""
    fmt: "FormatAbstract"
    """The format of the source file."""

    def assert_expected(self, actual: Any, **kwargs: Any) -> None:
        """Assert the actual result of the test.

        :param actual: The actual result of the test.
        :param kwargs: Additional keyword arguments to parse to the format.
        """
        __tracebackhide__ = True
        error = self.fmt.assert_expected(actual, self, **kwargs)
        if error is None:
            return True
        if self.fmt.regen_on_failure:
            # TODO how to cache regeneration until all test parameters are run?
            try:
                self.fmt.regen_file(self, actual, **kwargs)
            except Exception as exc:
                error += f"\nRegeneration failed: {exc}"
            else:
                error += f"\nREGENERATED FILE: {self.fmt.path}"
        raise AssertionError(error)


def create_parameters(
    path: Union[str, Path],
    fmt: str = "dot",
    encoding="utf8",
    fixture_name: str = "file_params",
    regen_on_failure: bool = False,
) -> Tuple[str, List[ParamTestData], List[str]]:
    """Return a pytest parametrize decorator for a fixture file.

    :param path: Path to the fixture file.
    :param format: Format of the fixture file.
    :param encoding: Encoding of the fixture file.
    :param fixture_name: Name of the fixture parameter.

    :return: A tuple of the fixture name, a list of test data and a list of ids.
    """
    path = Path(path)
    # check if the file exists
    if not path.is_file():
        raise FileNotFoundError(f"File {path} not found.")

    # select read format
    if fmt != "dot":
        raise NotImplementedError("Currently only dot format is supported.")
    fmt_inst = DotFormat(path, encoding, regen_on_failure)

    # read fixture file
    file_params = list(fmt_inst.read())

    # create pytest parametrize ids
    ids = [f"{p.line}-{p.title}" for p in file_params]

    return fixture_name, file_params, ids


_TITLE_RE = re.compile(r"^\s*\[(?P<title>\S+)\]\s*(?P<description>.*)$")


class FormatAbstract:
    """Abstract class for a format."""

    def __init__(
        self, path: Path, encoding: str = "utf8", regen_on_failure: bool = False
    ) -> None:
        """Initialize the format.

        :param path: Path to the fixture file.
        :param encoding: Encoding of the fixture file.
        """
        self.path = path
        self.encoding = encoding
        self.regen_on_failure = regen_on_failure

    def read(self) -> Iterator[ParamTestData]:
        """Read the fixture file and return a list of test data.

        :return: List of test data.
        """
        raise NotImplementedError()

    def assert_expected(
        self, actual: Any, data: ParamTestData, **kwargs: Any
    ) -> Optional[str]:
        """Assert the actual result matches the expected.

        :param actual: Actual result.
        """
        raise NotImplementedError()

    def regen_file(data: ParamTestData, actual: Any, **kwargs: Any) -> None:
        """Regenerate the fixture file."""
        raise NotImplementedError()


class DotFormat(FormatAbstract):
    """Dot file format."""

    name = "dot"

    def read(self) -> Iterator[ParamTestData]:
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

        for index, test in enumerate(tests):
            yield ParamTestData(*test, fmt=self, index=index)

    def assert_expected(
        self,
        actual: str,
        data: ParamTestData,
        rstrip: bool = False,
        rstrip_lines: bool = False,
    ) -> Optional[str]:
        """Assert the actual result of the test.

        :param rstrip: Whether to apply `str.rstrip` to actual and expected before comparing.
        :param rstrip_lines: Whether to apply `str.rstrip`
            to each line of actual and expected before comparing.
        """
        expected = cast(str, data.expected)
        if rstrip:
            actual = actual.rstrip()
            expected = expected.rstrip()
        if rstrip_lines:
            actual = "\n".join(line.rstrip() for line in actual.splitlines())
            expected = "\n".join(line.rstrip() for line in expected.splitlines())

        if actual == expected:
            return None
        return self._diff(actual, expected, data)

    def regen_file(
        self,
        data: ParamTestData,
        actual: str,
        rstrip: bool = False,
        rstrip_lines: bool = False,
    ) -> None:
        if rstrip:
            actual = actual.rstrip()
        if rstrip_lines:
            actual = "\n".join(line.rstrip() for line in actual.splitlines())
        text = []
        for index, data in enumerate(self.read()):
            text.append(f"[{data.title}] {data.description}\n")
            text.append(".\n")
            text.append(data.content)
            text.append(".\n")
            if index == data.index:
                # TODO what if actual has '.' line in the middle?
                text.append(actual)
            else:
                text.append(data.expected)
            text.append("\n.\n\n")
        self.path.write_text("".join(text), encoding=self.encoding)

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
