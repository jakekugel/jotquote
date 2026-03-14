# Plan: Migrate Tests from unittest to pytest

**Date:** 2026-03-14
**Branch:** feature/unit-test-cleanup

## Goal

Migrate all unittest-style test files to native pytest, modernize existing pytest tests, and remove the standalone `mock` dev dependency.

## Context

- Three unittest files (`api_test.py`, `cli_test.py`, `web_test.py`) used `unittest.TestCase`, `setUp`/`tearDown`, `self.assert*`, and the `mock` package.
- `api_pytest_test.py` was already pytest-native but had two anti-patterns.
- `tests/conftest.py` already existed (untracked) with `config` and `flask_client` fixtures — no changes needed there.

## Files Changed

| File | Action |
|---|---|
| `tests/api_test.py` | Rewrite (unittest → pytest) + absorb content from `api_pytest_test.py` |
| `tests/api_pytest_test.py` | Deleted (content merged into `api_test.py`) |
| `tests/cli_test.py` | Rewrite (unittest → pytest) |
| `tests/web_test.py` | Rewrite (unittest → pytest) |
| `tests/conftest.py` | No changes — already had `config` and `flask_client` fixtures |
| `tests/test_util.py` | No changes |
| `pyproject.toml` | Removed `mock>=5.0` from dev dependencies |

## Key Changes Applied

### Structural
- Removed all `unittest.TestCase` class wrappers
- Replaced `setUp`/`tearDown` with `config` and `tmp_path` fixtures
- Removed `setUpClass` in `cli_test.py` (sys.path manipulation no longer needed)
- `api_pytest_test.py` content merged into `api_test.py`, then deleted

### Assertions
- `self.assertEqual(a, b)` → `assert a == b`
- `self.assertTrue(x)` → `assert x`
- `self.assertFalse(x)` → `assert not x`
- `self.assertRaisesRegex(Exc, pat)` → `with pytest.raises(Exc, match=re.escape(pat)):`

### Imports removed
- `import unittest`, `import mock`, `from mock import patch`
- `import shutil`, `import tempfile`
- `from __future__ import unicode_literals`, `from __future__ import print_function`
- `import sys` (Python 2 version-check branches removed)

### Imports added
- `import pytest`
- `from unittest.mock import patch` (stdlib, replaces `mock` package)

### Modernizations
- `test_get_random_value_1/2/3` → single `@pytest.mark.parametrize` test
- `test_get_random_value_4` → `test_get_random_value_sequence` (list comprehension)
- `global my_args` in `api_pytest_test.py` → local `captured_args = []` list
- `try/except` in parametrize test → `pytest.raises`
- All `assertRaisesRegex` patterns wrapped with `re.escape()` for safety
- `assert x != None` → `assert x is not None` in `web_test.py`

### Decorator note (`cli_test.py`)
When `@patch(...)` is used on a free function, the mock is injected as the **first** positional argument, before fixtures:
```python
@patch('jotquote.web.run_server')
def test_webserver(mock_run_server, config, tmp_path):
    ...
```
Value-replacement patches like `@patch('jotquote.api.CONFIG_FILE', '/fake/...')` inject no argument.
