"""Basic tests for the project."""
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.pytester import Pytester


pytest_plugins = ["pytester"]


@pytest.mark.parametrize("fmt,fname", [("dot", "basic.txt"), ("yaml", "basic.yaml")])
def test_basic_pass(pytester: "Pytester", fmt: str, fname: str):
    """Basic parsing test."""
    pytester.copy_example(Path("tests", "fixtures", fname))
    pytester.makepyfile(
        f"""
        from pathlib import Path
        import pytest
        @pytest.mark.param_file(Path(__file__).parent / "{fname}", fmt="{fmt}")
        def test_basic(file_params):
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
            with pytest.raises(AssertionError, match="{fname}"):
                file_params.assert_expected("Otherx", rstrip=True)
    """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=2)


@pytest.mark.parametrize("fmt,fname", [("dot", "basic.txt"), ("yaml", "basic.yaml")])
def test_regen(pytester: "Pytester", fmt: str, fname: str):
    """Basic re-genning failed test."""
    pytester.copy_example(Path("tests", "fixtures", fname))
    pytester.makepyfile(
        f"""
        from pathlib import Path
        import pytest
        @pytest.mark.param_file(Path(__file__).parent / "{fname}", fmt="{fmt}")
        def test_basic(file_params):
            file_params.assert_expected("Wrong", rstrip=True)
    """
    )
    result = pytester.runpytest("--regen-file-failure")
    result.assert_outcomes(failed=2)
    assert "REGENERATED FILE" in result.stdout.str()
    result = pytester.runpytest()
    result.assert_outcomes(passed=2)
