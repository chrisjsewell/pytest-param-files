"""Basic tests for the project."""
from pathlib import Path

from pytest_param_files import with_parameters


@with_parameters(Path(__file__).parent / "fixtures" / "basic.txt")
def test_basic(line, title, description, content, expected):
    """Basic parsing test."""
    assert isinstance(line, int)
    assert isinstance(title, str)
    assert isinstance(description, str)
    assert isinstance(content, str)
    assert isinstance(expected, str)
    assert title.startswith("name")
    assert description == "description"
    assert content.rstrip() == "Something"
    assert expected.rstrip() == "Other"
