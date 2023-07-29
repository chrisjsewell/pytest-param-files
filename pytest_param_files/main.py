"""Main module"""
from __future__ import annotations

from dataclasses import dataclass, field
import difflib
from pathlib import Path
import re
import traceback
from typing import TYPE_CHECKING, Any, ClassVar, Iterator, Literal, cast

from ruamel.yaml import YAML, MappingNode, Node

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


def pytest_generate_tests(metafunc: Metafunc) -> None:
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
    description: str | None
    """The description of the test."""
    content: Any
    """The input content of the test."""
    expected: Any
    """The expected result of the test."""
    index: int
    """The index of the test in the file."""
    fmt: FormatAbstract
    """The format of the source file."""
    extra: dict[str, Any] = field(default_factory=dict)
    """Additional data for the test."""

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
            except Exception:
                error += f"\nRegeneration failed:\n{traceback.format_exc()}"

            else:
                error += f"\nREGENERATED FILE: {self.fmt.path}"
        raise AssertionError(error)


def create_parameters(
    path: str | Path,
    fmt: Literal["dot", "yaml"] = "dot",
    encoding="utf8",
    fixture_name: str = "file_params",
    regen_on_failure: bool = False,
) -> tuple[str, list[ParamTestData], list[str]]:
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
    if fmt == "dot":
        fmt_inst = DotFormat(path, encoding, regen_on_failure)
    elif fmt == "yaml":
        fmt_inst = YamlFormat(path, encoding, regen_on_failure)
    else:
        raise NotImplementedError(f"Unknown format {fmt!r}, set to 'dot' or 'yaml'")

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
    ) -> str | None:
        """Assert the actual result matches the expected.

        :param actual: Actual result.
        """
        raise NotImplementedError()

    def regen_file(self, data: ParamTestData, actual: Any, **kwargs: Any) -> None:
        """Regenerate the fixture file."""
        raise NotImplementedError("not implemented")


class DotFormat(FormatAbstract):
    """Dot file format."""

    name: ClassVar[str] = "dot"

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
                        description = None
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
    ) -> str | None:
        """Assert the actual result of the test.

        :param rstrip: Whether to apply `str.rstrip` to actual and expected before comparing.
        :param rstrip_lines: Whether to apply `str.rstrip`
            to each line of actual and expected before comparing.

        :return: An error message if the actual result does not match the expected result.
        """
        return assert_expected_strings(
            actual, cast(str, data.expected), self.path, data.line, rstrip, rstrip_lines
        )

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
            actual = "\n".join(line.rstrip() for line in actual.splitlines()).rstrip()
        text = []
        for index, current in enumerate(self.read()):
            if current.description is not None:
                text.append(f"[{current.title}] {current.description}\n")
            else:
                text.append(f"{current.title}\n")
            text.append(".\n")
            text.append(current.content)
            text.append(".\n")
            if index == data.index:
                # TODO what if actual has '.' line in the middle?
                expected = actual
            else:
                expected = current.expected
            text.append(expected)
            if not expected.endswith("\n"):
                text.append("\n")
            text.append(".\n")
            text.append("\n")
        if text:
            text = text[:-1]
        self.path.write_text("".join(text), encoding=self.encoding)


class YamlFormat(FormatAbstract):
    """YAML file format."""

    name: ClassVar[str] = "yaml"

    def read(self) -> Iterator[ParamTestData]:
        """Read the fixture file and return a list of test data.

        :return: List of test data.
        """
        text = self.path.read_text(encoding=self.encoding)
        yaml = YAML(typ="safe")
        node = yaml.compose(text)
        if not isinstance(node, MappingNode):
            raise TypeError(f"Expected sequence, got {type(node)}")
        data: dict = YAML(typ="safe").load(text)
        assert len(node.value) == len(data), "YAML node count mismatch"
        title_node: Node
        for index, ((title_node, _), (title, item)) in enumerate(
            zip(node.value, data.items())
        ):
            line = title_node.start_mark.line + 1
            if not isinstance(item, dict):
                raise TypeError(
                    f"Expected mapping value at line {line}, got {type(item)}"
                )
            for key in ("content", "expected"):
                if key not in item:
                    raise KeyError(f"Missing '{key}' key for item at line {line}")
            yield ParamTestData(
                line,
                title,
                item.get("description"),
                item["content"],
                item["expected"],
                fmt=self,
                index=index,
                extra=item,
            )

    def assert_expected(
        self,
        actual: Any,
        data: ParamTestData,
        rstrip: bool = False,
        rstrip_lines: bool = False,
    ) -> str | None:
        """Assert the actual result of the test.

        :param rstrip: Whether to apply `str.rstrip` to actual and expected,
            before comparing (strings only).
        :param rstrip_lines: Whether to apply `str.rstrip`
            to each line of actual and expected before comparing (strings only).
        """
        expected = data.expected

        if type(actual) != type(expected):
            return f"actual type {type(actual)} != expected type {type(expected)}"

        if isinstance(actual, str) and isinstance(expected, str):
            return assert_expected_strings(
                actual, expected, self.path, data.line, rstrip, rstrip_lines
            )

        if actual == expected:
            return None

        return (
            f"actual != expected (use --regen-file-failure)\n"
            f"actual: {actual}\nexpected: {expected}"
        )

    def regen_file(self, data: ParamTestData, actual: Any, **kwargs: Any) -> None:
        """Regenerate the fixture file."""
        new = YAML(typ="rt").load(self.path.read_text(encoding=self.encoding))
        new[data.title]["expected"] = actual
        with self.path.open("w", encoding=self.encoding) as handle:
            YAML(typ="rt").dump(new, handle)


def assert_expected_strings(
    actual: str,
    expected: str,
    path: Path,
    line: int,
    rstrip: bool = False,
    rstrip_lines: bool = False,
) -> str | None:
    """Assert the actual result of the test.

    :param rstrip: Whether to apply `str.rstrip` to actual and expected before comparing.
    :param rstrip_lines: Whether to apply `str.rstrip`
        to each line of actual and expected before comparing.

    :return: An error message if the actual result does not match the expected result.
    """
    if rstrip:
        actual = actual.rstrip()
        expected = expected.rstrip()
    if rstrip_lines:
        actual = "\n".join(line.rstrip() for line in actual.splitlines()).rstrip()
        expected = "\n".join(line.rstrip() for line in expected.splitlines()).rstrip()

    if actual == expected:
        return None
    return diff_strings(actual, expected, path, line)


def diff_strings(actual: str, expected: str, path: Path, line: int) -> str:
    """Return a diff string between actual and expected."""
    diff_lines = list(
        difflib.unified_diff(
            (expected + "\n").splitlines(keepends=True),
            (actual + "\n").splitlines(keepends=True),
            fromfile=f"{path}:{line}",
            tofile="(actual)",
            lineterm="\n",
        )
    )
    if len(diff_lines) <= 500:
        return "actual != expected (use --regen-file-failure)\n" + "".join(diff_lines)
    else:
        return (
            "actual != expected (use --regen-file-failure)\n"
            f"diff too big to show ({len(diff_lines)}): "
            f"{path}:{line}"
        )


# class CustomDumper(yaml.SafeDumper):
#     """Custom YAML dumper."""

#     def represent_scalar(self, tag, value, style=None):
#         if style is None:
#             # be a bit more clever about the string style,
#             # to get a more readable output
#             if "\n" in value:
#                 style = "|"
#             elif len(value) > 80:
#                 style = ">"
#         node = yaml.ScalarNode(tag, value, style=style)
#         if self.alias_key is not None:
#             self.represented_objects[self.alias_key] = node
#         return node
