# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Plans

The [plans/](plans/) folder stores implementation plans created by Claude for future PRs. Before starting a non-trivial implementation, save the plan there for reference.

## Commands

```bash
# Install in editable mode for development
pip install --editable .
pip install -r dev-requirements.txt

# Run tests
pytest

# Run a single test file
pytest tests/api_test.py

# Run a single test
pytest tests/api_test.py::TestClassName::test_method_name

# Lint
flake8 .

# Run tests with coverage
coverage run -m pytest
coverage report

# Run all environments (py27, py37, py38, pep8)
tox
```

## Architecture

**jotquote** is a CLI tool + web server for managing a personal quote collection.

### Core modules

- [jotquote/api.py](jotquote/api.py) — All business logic and data access. The `Quote` class is the central data model. Key functions: `read_quotes()`, `parse_quote()`, `add_quote()`, `write_quotes()`, `get_config()`. Configuration lives at `~/.jotquote/settings.conf`; quote data at `~/.jotquote/quotes.txt`.

- [jotquote/cli.py](jotquote/cli.py) — Click-based CLI. Entry point is `main`. Subcommands: `add`, `list`, `random`, `today`, `showalltags`, `settags`, `info`, `webserver`. The quote file path flows via Click's context object (`ctx.obj['QUOTEFILE']`).

- [jotquote/web.py](jotquote/web.py) — Flask web server (`jotquote webserver`). Displays a deterministic daily quote. Caches quotes in Flask's `g` object and reloads when quote file mtime changes. Flask is lazily imported in `cli.py` so it doesn't load for pure CLI usage.

### Quote file format

Pipe-delimited plain text (UTF-8): `quote | author | publication | tag1, tag2, ...`

There are two input formats for the `add` command:
- **Simple** (default): `<quote> - <author> [(publication)]` — heuristically parses the hyphen separator
- **Extended** (`-e` flag): same pipe-delimited format as the quote file

### Key design details

- **Quote identity**: MD5 hash (first 16 chars) of the quote text — used by `settags -s` and `list -s` to identify a specific quote.
- **Daily quote**: `get_random_choice()` seeds RNG with days since 2016-01-01, so the same quote is shown all day. `_get_random_value()` shuffles a list with seed 0 then uses `days % numquotes` as the index.
- **Atomic writes**: `write_quotes()` writes to a randomly-named temp file, sanity-checks it against the backup size, creates a backup, then uses `os.replace()` to atomically swap it in.
- **Duplicate detection**: `add_quotes()` compares quote text (not hash) against existing quotes before appending.
- **Config auto-creation**: First run creates `~/.jotquote/settings.conf` and copies the template quote file from `jotquote/templates/quotes.txt`.
- **Version**: Defined in `jotquote/__init__.py` as `__version__`. Convention is `X.Y.Z.dev` between releases; strip `.dev` when releasing and tag the commit.

### Test infrastructure

- `tests/test_util.py` — helpers: `init_quotefile()` copies a fixture from `tests/testdata/` to a temp dir; `compare_quotes()` does list equality.
- `tests/testdata/` — eight quote fixture files (`quotes1.txt`–`quotes8.txt`).
- `tests/api_test.py` — unittest-style; monkey-patches `api.get_config` in `setUp` to return a test `ConfigParser`.
- `tests/api_pytest_test.py` — pytest-style using `monkeypatch` and `tmp_path`.

### Flake8 rules

Config is in `tox.ini`: line length max 120; E501, W503, and E722 are ignored; `tests/` directory is excluded.
