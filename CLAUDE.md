# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Plans

The [plans/](plans/) folder stores implementation plans created by Claude for future PRs. Before starting a non-trivial implementation, save the plan there for reference. At the end of every implementation, save a copy of the final plan to this folder.  The filename format should be `<YYYY>-<DD>-<MM>-<description>.md`, for example:

2026-14-03-migrate-tests-to-pytest.md

All non-trivial implementation plans must include an appropriate number of new unit tests and at least one new integration test.

## Commands

```bash
# Install project and dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run a single test file
uv run pytest tests/api_test.py

# Run a single test
uv run pytest tests/api_test.py::TestClassName::test_method_name

# Lint
uv run ruff check jotquote/

# Run tests with coverage
uv run coverage run -m pytest
uv run coverage report

# Build wheel and sdist
uv build
```

## Development Verification

After any change to `jotquote/` or `jotquote/templates/quotes.txt`, run the linter against the built-in quote collection to confirm there are no lint errors:

```bash
export JOTQUOTE_CONFIG=jotquote/templates/settings.conf
uv run jotquote lint
```

Because the template `settings.conf` uses `quote_file = ./quotes.txt` (a relative path), jotquote resolves it to `jotquote/templates/quotes.txt` automatically. The built-in quotes must always be lint-clean.

## Architecture

**jotquote** is a CLI tool + web server for managing a personal quote collection.

### Core modules

- [jotquote/api.py](jotquote/api.py) — All business logic and data access. The `Quote` class is the central data model. Key functions: `read_quotes()`, `parse_quote()`, `add_quote()`, `write_quotes()`, `get_config()`. Configuration lives at `~/.jotquote/settings.conf`; quote data at `~/.jotquote/quotes.txt`.

- [jotquote/cli.py](jotquote/cli.py) — Click-based CLI. Entry point is `main`. Subcommands: `add`, `list`, `random`, `today`, `showalltags`, `settags`, `info`, `webserver`, `lint`, `quotemap` (with sub-subcommand `rebuild`). The quote file path flows via Click's context object (`ctx.obj['QUOTEFILE']`).

- [jotquote/web.py](jotquote/web.py) — Flask web server (`jotquote webserver`). Displays a deterministic daily quote. Caches quotes in Flask's `g` object and reloads when quote file mtime changes. Flask is lazily imported in `cli.py` so it doesn't load for pure CLI usage.

- [jotquote/web_review.py](jotquote/web_review.py) — Separate Flask app for reviewing and updating quote tags. Serves the daily quote alongside a checkbox list of all tags; tag changes are saved via POST. Intended for local use only (no auth). Start with `waitress-serve --host 127.0.0.1 --port 5000 jotquote.web_review:app`.

- [jotquote/lint.py](jotquote/lint.py) — All lint logic. `ALL_CHECKS` frozenset defines the valid check names. `lint_quotes()` runs enabled checks against a list of quotes and returns a list of `LintIssue`. `apply_fixes()` applies auto-fixable issues in place. Available checks: `ascii`, `smart-quotes`, `smart-dashes`, `double-spaces`, `quote-too-long`, `no-tags`, `no-author`, `author-antipatterns`, `required-tag-group`.

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
- **Config auto-creation**: First run copies `jotquote/templates/settings.conf` to `~/.jotquote/settings.conf` and copies `jotquote/templates/quotes.txt` alongside it. The config file location can be overridden with the `JOTQUOTE_CONFIG` environment variable. Relative paths in `settings.conf` (e.g. `quote_file = ./quotes.txt`) are resolved relative to the directory containing the config file.
- **Quotemap**: Optional `quotemap_file` config property pointing to a date-to-hash mapping file. Format: `YYYYMMDD: <16-char-hash>  # optional comment`, one per line. When configured, the web server checks this file before falling back to the seeded RNG. The `/<date>` route serves a specific date's mapped quote. Parsed by `read_quotemap()` in `api.py`; raises `ClickException` on any validation failure. `read_quotemap()` returns `dict[str, dict]` where each value has keys `hash`, `sticky`, `raw_line`. The `jotquote quotemap rebuild` subcommand auto-generates entries for approximately 10 years (3652 days) with even distribution; see [DOCUMENTATION.md](DOCUMENTATION.md#quotemap).
- **Version**: Defined in `pyproject.toml` as `version`. `jotquote/__init__.py` exposes it as `__version__` via `importlib.metadata`. Convention is `X.Y.Z.dev0` between releases; strip `.dev0` when releasing and tag the commit.

### Test infrastructure

- `tests/conftest.py` — shared fixtures: `config` (mocks `api.get_config` to return a test `ConfigParser`) and `flask_client` (provides a Flask test client with a temporary quote file).
- `tests/test_util.py` — helpers: `init_quotefile()` copies a fixture from `tests/testdata/` to a temp dir; `compare_quotes()` does list equality.
- `tests/testdata/` — nine quote fixture files (`quotes1.txt`–`quotes9.txt`).
- `tests/api_test.py` — unittest-style API tests.
- `tests/api_pytest_test.py` — pytest-style API tests using `monkeypatch` and `tmp_path`.
- `tests/api_quotemap_rebuild_test.py` — quotemap rebuild API tests.
- `tests/cli_test.py` — CLI unit tests.
- `tests/cli_integration_test.py` — CLI integration tests.
- `tests/lint_test.py` — lint module unit tests.
- `tests/quotemap_test.py` — quotemap functionality tests.
- `tests/web_test.py` — web server unit tests.
- `tests/web_integration_test.py` — web server integration tests.
- `tests/web_review_integration_test.py` — review app integration tests.

### Ruff rules

Config is in `pyproject.toml` under `[tool.ruff]`: line length max 120; E501 and E722 are ignored; `tests/` directory is excluded. Single quotes are preferred over double quotes.

### Code style

Prefer modern Python patterns and keep code as simple as possible. Favour the standard library and built-in language features over custom abstractions. When two approaches produce equivalent results, always choose the simpler one.

### settings.conf

If `settings.conf` properties are added, removed, or changed, the table in [DOCUMENTATION.md](DOCUMENTATION.md) must be updated. Not all documented properties appear in the template `settings.conf` — the code sets in-memory defaults (e.g. `lint_enabled_checks`) when the property is absent from the file. [DOCUMENTATION.md](DOCUMENTATION.md) is the authoritative reference for all available properties.
