# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Plans

The [plans/](plans/) folder stores implementation plans created by Claude for future PRs. Before starting a non-trivial implementation, save the plan there for reference. At the end of every implementation, save a copy of the final plan to this folder.  The filename format should be `<YYYY>-<DD>-<MM>-<description>.md`, for example:

2026-14-03-migrate-tests-to-pytest.md

All non-trivial implementation plans must include an appropriate number of new unit tests. Integration tests should also be included wherever they add value — at minimum one, but additional integration tests should be added when they cover meaningful scenarios.

When developing a code change with accompanying unit tests, use red/green TDD methodology: write a failing test first, confirm it fails, then write the implementation to make it pass.

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

After any change to `jotquote/` or `jotquote/resources/quotes.txt`, run the linter against the built-in quote collection to confirm there are no lint errors:

```bash
export JOTQUOTE_CONFIG=jotquote/resources/settings.conf
uv run jotquote lint
```

Because the template `settings.conf` uses `quote_file = ./quotes.txt` (a relative path), jotquote resolves it to `jotquote/resources/quotes.txt` automatically. The built-in quotes must always be lint-clean.

## Architecture

**jotquote** is a CLI tool + web server for managing a personal quote collection.

### Core modules

- [jotquote/api/](jotquote/api/) — All business logic and data access, split across focused submodules: `quote.py` (the `Quote` class, `parse_quote`, `parse_tags`), `store.py` (`read_quotes`, `write_quotes`, `add_quote`, `settags`, `set_quote`, SHA-256 concurrency control), `config.py` (`get_config`, section constants, legacy `[jotquote]` migration), `selection.py` (`get_random_choice`, `get_first_match`), and `lint.py` (`lint_quotes`, `apply_fixes`, `LintIssue`, all `_check_*` helpers). `jotquote/api/__init__.py` re-exports the public surface so `from jotquote import api` remains a single-import facade: `api.Quote`, `api.read_quotes`, `api.get_config`, `api.get_random_choice`, `api.LintIssue`, etc. Configuration lives at `~/.jotquote/settings.conf`; quote data at `~/.jotquote/quotes.txt`.

- [jotquote/cli/](jotquote/cli/) — Click-based CLI. Entry point is `main`, re-exported from `jotquote/cli/__init__.py` so the console-script entry point `jotquote.cli:main` still resolves. Subcommands: `add`, `list`, `random`, `today`, `showalltags`, `settags`, `info`, `webserver`, `webeditor`, `lint`. The quote file path flows via Click's context object (`ctx.obj['QUOTEFILE']`).

- [jotquote/web/](jotquote/web/) — Flask subpackage housing both web apps and shared helpers alongside `templates/` and `static/`:
  - [jotquote/web/viewer.py](jotquote/web/viewer.py) — Flask web server (`jotquote webserver`). Displays a deterministic daily quote. Caches quotes in Flask's `g` object and reloads when quote file mtime changes. Flask is lazily imported in `cli.py` so it doesn't load for pure CLI usage. WSGI path: `jotquote.web.viewer:app`.
  - [jotquote/web/editor.py](jotquote/web/editor.py) — Separate Flask app (`jotquote webeditor`) for reviewing and updating quote tags. Serves the daily quote alongside a checkbox list of all tags; tag changes are saved via POST. Intended for local use only (no auth). WSGI path: `jotquote.web.editor:app`.
  - [jotquote/web/helpers.py](jotquote/web/helpers.py) — Shared helpers used by both apps: `TimestampFormatter`, `configure_logging`, `sanitize_for_log`, `get_enabled_checks`, `get_color_config`, `abbreviate_timezone`.

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
- **Config auto-creation**: First run copies `jotquote/resources/settings.conf` to `~/.jotquote/settings.conf` and copies `jotquote/resources/quotes.txt` alongside it. The config file location can be overridden with the `JOTQUOTE_CONFIG` environment variable. Relative paths in `settings.conf` (e.g. `quote_file = ./quotes.txt`) are resolved relative to the directory containing the config file.
- **Quote resolver**: Optional `quote_resolver` config property in `[web]` specifying a dotted Python module path. The module must define `resolve(date_str: str) -> str | None` returning a 16-char MD5 hash or None. When configured, the web server calls the resolver before falling back to the seeded RNG. The `/<date>` route serves a specific date's resolved quote. The resolver is loaded lazily via `importlib.import_module()` and cached for the server lifetime. See [DOCUMENTATION.md](DOCUMENTATION.md#quote-resolver).
- **Version**: Defined in `pyproject.toml` as `version`. `jotquote/__init__.py` exposes it as `__version__` via `importlib.metadata`. Convention is `X.Y.Z.dev0` between releases; strip `.dev0` when releasing and tag the commit.

### Test infrastructure

- `tests/conftest.py` — shared fixtures: `config` (mocks `api.get_config` at both the facade and the `jotquote.api.config` submodule) and `flask_client` (provides a Flask test client with a temporary quote file). `tests/unit/conftest.py` provides the `editor_client` fixture.
- `tests/test_util.py` — helpers: `init_quotefile()` copies a fixture from `tests/testdata/` to a temp dir; `compare_quotes()` does list equality.
- `tests/testdata/` — nine quote fixture files (`quotes1.txt`–`quotes9.txt`).
- `tests/unit/api/` — per-submodule unit tests mirroring `jotquote/api/`: `test_quote.py`, `test_store.py`, `test_config.py`, `test_selection.py`, `test_lint.py`. Private helpers are reached by importing the submodule directly (e.g. `from jotquote.api import store as store_mod`).
- `tests/unit/cli/test_cli.py` — CLI unit tests.
- `tests/unit/web/` — web-subpackage unit tests: `test_viewer.py`, `test_editor.py`, `test_helpers.py`.
- `tests/integration/` — integration tests: `test_cli.py`, `test_web_viewer.py`, `test_web_editor.py`.
- `tests/fixtures/test_resolver.py` — test quote resolver for integration tests.

### Ruff rules

Config is in `pyproject.toml` under `[tool.ruff]`: line length max 120; E501 and E722 are ignored; `tests/` directory is excluded. Single quotes are preferred over double quotes.

### Code style

Prefer modern Python patterns and keep code as simple as possible. Favour the standard library and built-in language features over custom abstractions. When two approaches produce equivalent results, always choose the simpler one.

- **Docstrings**: Public functions must have a docstring that describes the function's purpose and documents the types of all input parameters and return values.
- **Module ordering**: Public functions come first in a module, followed by private helper functions (prefixed with `_`).
- **DRY**: Avoid code duplication. When substantially similar logic appears in multiple places, extract it into a shared helper function.
- **Block comments**: Functions with more than a few statements should have a single-line comment before each logical block, explaining its purpose in plain English.

### settings.conf

Properties in `settings.conf` are organized into three sections: `[general]`, `[lint]`, and `[web]`. The old single-section `[jotquote]` format is still supported via automatic in-memory migration with a deprecation warning. If `settings.conf` properties are added, removed, or changed, the table in [DOCUMENTATION.md](DOCUMENTATION.md) must be updated. Not all documented properties appear in the template `settings.conf` — the code sets in-memory defaults (e.g. `enabled_checks` in `[lint]`) when the property is absent from the file. [DOCUMENTATION.md](DOCUMENTATION.md) is the authoritative reference for all available properties.
