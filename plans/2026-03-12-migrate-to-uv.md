# Plan: Migrate jotquote to uv

## Context

jotquote currently uses a legacy Python packaging stack: `setup.py` (setuptools), `dev-requirements.txt`, `tox`, and `twine`. The goal is to migrate to `uv` — a modern, fast Python package manager — consolidating all config into `pyproject.toml`, dropping Python 2.7 support (uv doesn't support it), and simplifying the dev workflow to `uv sync` + `uv run`.

CI is also being migrated from Travis CI (which ended free open source support in 2021 and is effectively defunct) to GitHub Actions. The Travis CI build badge in `README.rst` will be replaced with a GitHub Actions badge.

---

## Files to Delete

- `setup.py`
- `setup.cfg` (only contained `[bdist_wheel] universal=1`, irrelevant after dropping py2)
- `dev-requirements.txt`
- `tox.ini` (after migrating flake8 config to `.flake8`)
- `MANIFEST.in` (replaced by hatchling include config in `pyproject.toml`)

---

## Files to Create

### `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "jotquote"
dynamic = ["version"]
description = "A command-line interface for collecting and organizing quotes, and a quote of the day web server."
readme = "README.rst"
license = { text = "MIT License" }
authors = [
    { name = "Jake Kugel", email = "jake_kugel@yahoo.com" }
]
keywords = ["quotes"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Environment :: Web Environment",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "License :: OSI Approved :: MIT License",
]
requires-python = ">=3.8"
dependencies = [
    "flask>=0.10.1",
    "click>=7.0",
]

[project.scripts]
jotquote = "jotquote.cli:main"

[tool.hatch.version]
path = "jotquote/__init__.py"

[tool.hatch.build.targets.wheel]
packages = ["jotquote"]
include = [
    "jotquote/templates/**",
    "jotquote/static/**",
]

[dependency-groups]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mock>=5.0",
    "flake8>=6.0",
    "twine>=4.0",
    "coverage>=7.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Notes:
- **Hatchling** is the build backend — it replaces `setup.py`+setuptools as the tool that creates the `.whl` and `.tar.gz` for PyPI. uv calls it automatically when you run `uv build`. It reads `__version__` from `jotquote/__init__.py` directly via `[tool.hatch.version]` — no regex hack needed.
- `configparser` and `future` dependencies removed — both are Python 2 backports not needed in Python 3
- `click` added explicitly (was an implicit dep via flask previously)

### `.flake8`

Migrated from `[flake8]` section in `tox.ini`:

```ini
[flake8]
ignore = E501, W503, E722
exclude = .tox,*.egg,.git,venv,tests,__pycache__,.venv
max-line-length = 120
select = E,W,F,N,I
application-import-names = jotquote,tests
```

Note: `.venv` added to exclude list (uv's default venv location).

**How pep8/flake8 is run with uv** (replaces `tox -e pep8`):
- Locally: `uv run flake8 .`
- In CI: a dedicated step in the GitHub Actions workflow (see below)
- Flake8 is in the `dev` dependency group, so it's always available after `uv sync --group dev`

---

## Files to Modify

### `jotquote/__init__.py`
- Change `__version__ = "0.9.5.dev"` → `__version__ = "0.9.5.dev0"`
- PEP 440 requires a number after `.dev`; hatchling will reject the current value

### `jotquote/cli.py`
- **Remove line 20**: `click.disable_unicode_literals_warning = True`
  - This attribute was removed from Click and causes `AttributeError` on Click >= 8.x
  - This is a **breaking bug** that must be fixed before tests will pass

### `jotquote/api.py` (optional cleanup)
- Remove `from __future__ import print_function, unicode_literals`
- Remove `from io import open`
- Simplify `write_quotes()`: remove the `hasattr(os, 'replace')` branch (dead code in Python 3)

### `jotquote/web.py` (optional cleanup)
- Remove the `sys.version_info < (3, 0, 0)` / `basestring` block in `run_server()` (dead code)

### `.travis.yml`
- Delete; replaced by `.github/workflows/ci.yml`
- Travis CI stopped providing free CI for open source projects in 2021; GitHub Actions is the standard replacement for GitHub-hosted repos
- The new workflow runs both `uv run pytest` (replaces `tox -e py3x`) and `uv run flake8 .` (replaces `tox -e pep8`) as separate steps

### `README.rst`
- Remove Travis CI build badge:
  ```rst
  .. image:: https://travis-ci.org/jakekugel/jotquote.svg?branch=master
      :target: https://travis-ci.org/jakekugel/jotquote
      :alt: Build Status
  ```
- Replace with GitHub Actions badge:
  ```rst
  .. image:: https://github.com/jakekugel/jotquote/actions/workflows/ci.yml/badge.svg
      :target: https://github.com/jakekugel/jotquote/actions/workflows/ci.yml
      :alt: Build Status
  ```
- Update "Supported environments" section: remove Python 2.7, 3.5, 3.6; add 3.8–3.12

### `CONTRIBUTING.rst`
- Update install instructions: replace `pip install -r dev-requirements.txt` + `pip install --editable .` with `uv sync --group dev`
- Replace `pytest` with `uv run pytest`
- Replace `coverage run -m pytest` / `coverage report` with `uv run coverage run -m pytest` / `uv run coverage report`
- Replace tox section with a note that multi-version testing is handled by CI (GitHub Actions)

### `CLAUDE.md`
- Update Commands section: replace `pip install` steps with `uv sync --group dev`
- Replace `pytest` with `uv run pytest`, `flake8 .` with `uv run flake8 .`, etc.
- Remove `tox` command (no longer applicable)
- Update coverage commands to use `uv run` prefix

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: uv sync --group dev
      - name: Run tests
        run: uv run pytest
      - name: Lint
        run: uv run flake8 .
```

---

## Execution Order

1. Fix `jotquote/cli.py` — remove `click.disable_unicode_literals_warning` line (breaking issue)
2. Fix `jotquote/__init__.py` — update version to `"0.9.5.dev0"`
3. Create `pyproject.toml`
4. Create `.flake8`
5. Run `uv sync --group dev` → generates `uv.lock`
6. Run `uv run pytest` → verify all tests pass
7. Run `uv run flake8 .` → verify no lint errors
8. Delete `setup.py`, `setup.cfg`, `dev-requirements.txt`, `tox.ini`, `MANIFEST.in`
9. Apply optional Python 2 cleanup in `api.py` and `web.py`
10. Delete `.travis.yml`; create `.github/workflows/ci.yml`
11. Update `README.rst` — swap Travis badge for GitHub Actions badge, update supported Python versions
12. Update `CONTRIBUTING.rst` — replace pip/tox commands with uv equivalents
13. Update `CLAUDE.md` — update Commands section to use `uv run` prefix
14. Run `uv build` → verify `dist/` contains `.whl` and `.tar.gz`
15. Save copy of this plan to `plans/2026-03-12-migrate-to-uv.md`

---

## Verification

- `uv run pytest` — all tests pass
- `uv run flake8 .` — no errors
- `uv run jotquote --version` — prints correct version
- `uv run jotquote --help` — CLI loads without error
- `uv build` — produces valid wheel and sdist
- `uv run twine check dist/*` — metadata validates cleanly
- Install wheel in fresh venv and run `jotquote info` — confirms templates/static bundled correctly

---

## Critical Files

| File | Change |
|---|---|
| `jotquote/cli.py:20` | Remove breaking `click.disable_unicode_literals_warning` line |
| `jotquote/__init__.py:7` | Fix version to PEP 440-compliant `"0.9.5.dev0"` |
| `setup.py` | Source of metadata to transcribe into `pyproject.toml`; then delete |
| `tox.ini` | Source of flake8 config to migrate to `.flake8`; then delete |
| `MANIFEST.in` | Documents package data dirs (`templates/`, `static/`) for hatchling include; then delete |
| `README.rst` | Replace Travis badge with GitHub Actions badge; update supported Python versions |
| `CONTRIBUTING.rst` | Update install/test/lint commands to use `uv` |
| `CLAUDE.md` | Update Commands section to use `uv run` prefix throughout |
