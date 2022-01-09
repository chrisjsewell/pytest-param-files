"""Basic tests for the project."""
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.pytester import Pytester


pytest_plugins = ["pytester"]


def test_basic_dot(pytester: "Pytester"):
    """Basic parsing test."""
    pytester.copy_example(Path("tests", "fixtures", "basic.txt"))
    pytester.makepyfile(
        """
        from pathlib import Path
        import pytest
        @pytest.mark.param_file(Path(__file__).parent / "basic.txt", fmt="dot")
        def test_basic_dot(file_params):
            assert isinstance(file_params.line, int)
            assert isinstance(file_params.title, str)
            assert isinstance(file_params.description, str)
            assert isinstance(file_params.content, str)
            assert isinstance(file_params.expected, str)
            assert file_params.title.startswith("name")
            assert file_params.description == "description"
            assert file_params.content.rstrip() == "Something"
            assert file_params.expected.rstrip() == "Other"
            file_params.assert_expected("Other", rstrip=True)
            with pytest.raises(AssertionError, match="basic.txt"):
                file_params.assert_expected("Otherx", rstrip=True)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=2)
