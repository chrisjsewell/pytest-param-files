from pathlib import Path

import pytest


@pytest.mark.param_file(Path(__file__).parent / "fixtures" / "basic.txt", fmt="dot")
def test_basic_dot(file_params):
    """Basic parsing test."""
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


@pytest.mark.param_file(Path(__file__).parent / "fixtures" / "basic.yaml", fmt="yaml")
def test_basic_yaml(file_params):
    """Basic parsing test."""
    assert isinstance(file_params.line, int)
    assert isinstance(file_params.title, str)
    assert isinstance(file_params.description, str)
    assert isinstance(file_params.content, str)
    assert isinstance(file_params.expected, str)
    assert file_params.title.startswith("name")
    assert file_params.description == "description"
    assert file_params.content.rstrip() == "Something"
    # assert file_params.expected.rstrip() == "Other"
    file_params.assert_expected("Other", rstrip=True)
    # with pytest.raises(AssertionError, match="basic.yaml"):
    #     file_params.assert_expected("Otherx", rstrip=True)
