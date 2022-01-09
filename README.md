# pytest-param-files

[![PyPI][pypi-badge]][pypi-link]

A small package to create pytest parametrize decorators from external files.

Simply create a text file with the following (`dot`) format:

```
[name1] description
.
input content
.
expected output content
,

[name2] description
.
input content
.
expected output content
,
```

Then, use the `with_parameters` decorator to create a parametrized test:

```python
from pathlib import Path
from pytest_param_files import with_parameters

import my_function

PATH = Path(__file__).parent.joinpath("test_file.txt")

@with_parameters(PATH, fmt="dot")
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
@with_parameters(PATH, fmt="dot")
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
E       -content+other
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

## Other formats

TODO ...

## Regenerating expected output on failures

TODO ...

[pypi-badge]: https://img.shields.io/pypi/v/pytest_param_files.svg
[pypi-link]: https://pypi.org/project/pytest_param_files
