# pytest-param-files

[![PyPI][pypi-badge]][pypi-link]

A small package to generate parametrized [pytests](https://docs.pytest.org) from external files.

Simply create a text file with an available format:

`dot` format (default):
```
[name1] description
.
input content
.
expected output content
.

[name2] description
.
input content
.
expected output content
.
```

`yaml` format:
```yaml
- title: name1
  description: description
  input: |-
    input content
  expected: |-
    expected output content
- title: name2
  description: description
  input: |-
    input content
  expected: |-
    expected output content
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

Running pytest with the `--regen-file-failure` option will regenerate the parameter file with actual output, if any test fails.

Note, currently regeneration of YAML files may not provide the same formatting as the original file, and will not preserve comments.

## Other formats

TODO ...

[pypi-badge]: https://img.shields.io/pypi/v/pytest_param_files.svg
[pypi-link]: https://pypi.org/project/pytest_param_files
