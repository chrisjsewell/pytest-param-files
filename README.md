# pytest-param-files

[![PyPI][pypi-badge]][pypi-link]

A [pytest](https://docs.pytest.org) plugin to generate parametrized tests from external files,
with (optional) automated regeneration of expected output on failures.

Simply create a text file with an available format:

`yaml` format:
```yaml
name1:
  description: optional description
  input: |-
    input content
  expected: |-
    expected output content
name2:
  description: optional description
  input: |-
    input content
  expected: |-
    expected output content
```

`dot` format (default):
```
[name1] optional description
.
input content
.
expected output content
.

[name2] optional description
.
input content
.
expected output content
.
```

Then, use the `param_file` pytest marker to create a parametrized test:

```python
from pathlib import Path
import pytest

import my_function

PATH = Path(__file__).parent.joinpath("test_file.txt")

@pytest.mark.param_file(PATH, fmt="dot")
def test_function(file_params):
    assert my_function(file_params.content) == file_params.expected
```

and the output will be:

```console
$ pytest -v test_file.py
...
test_file.py::test_function[1-name1] PASSED
test_file.py::test_function[8-name2] FAILED
```

Alternatively use the `assert_expected` method, which will can handle more rich assertion features:

```python
@pytest.mark.param_file(PATH, fmt="dot")
def test_function(file_params):
    actual = my_function(file_params.content)
    assert file_params.assert_expected(actual, rstrip=True)
```

```console
$ pytest -v test_file.py
...
test_file.py::test_function[1-name1] PASSED
test_file.py::test_function[8-name2] FAILED
...
E       AssertionError: Actual does not match expected
E       --- /path/to/test_file.txt:8
E       +++ (actual)
E       @@ -1 +1 @@
E       -content
E       +other
```

## Installation

Install from [PyPI][pypi-link]:

```console
$ pip install pytest-param-files
```

or install locally (for development):

```console
$ pip install -e .
```

## Regenerating expected output on failures

Running pytest with the `--regen-file-failure` option will regenerate the parameter file with actual outputs of `assert_expected`, if any test fails.

[pypi-badge]: https://img.shields.io/pypi/v/pytest_param_files.svg
[pypi-link]: https://pypi.org/project/pytest_param_files
