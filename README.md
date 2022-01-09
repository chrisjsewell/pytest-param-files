# pytest-param-files

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
def test_function(line, title, description, content, expected):
    assert my_function(content) == expected
```

and the output will be:

```console
$ pytest -v test_file.py
...
test_file.py::test_function[1-name1] PASSED
test_file.py::test_function[8-name2] PASSED
```

## Other formats

TODO ...

## Regenerating expected output on failures

TODO ...
