# Restructure the `jotquote/` package

## Context

The top-level [jotquote/](jotquote/) package has grown organically and now has some structural asymmetry worth cleaning up before more features are added.

Observations from the current layout:

- **[jotquote/api.py](jotquote/api.py) is ~850 lines** and blends five concerns: the `Quote` data model, quote parsing, file I/O + atomic writes + backups, `settings.conf` loading + legacy-section migration, validation helpers, and the daily-quote RNG. Splitting into focused modules inside an `api/` subpackage (with `__init__.py` re-exports preserving the `from jotquote import api` surface) lets library users keep one import while internal structure is cleaner.
- **Flask apps sit at the top level but depend on a [jotquote/web/](jotquote/web/) subpackage.** [jotquote/web_viewer.py](jotquote/web_viewer.py) and [jotquote/web_editor.py](jotquote/web_editor.py) both do `from jotquote.web import core as web_core`, yet they themselves are not inside `web/`. The subpackage currently holds only [jotquote/web/core.py](jotquote/web/core.py).
- **[jotquote/templates/](jotquote/templates/) mixes two unrelated "template" concepts:** Flask HTML templates (`quote.html`, `editor.html`, `about.html`, partials) and file templates copied on first run (`settings.conf`, `settings.legacy.conf`, `quotes.txt`).
- **[jotquote/static/](jotquote/static/)** (favicon, fonts, icons) is only ever used by the Flask apps but sits at package root, not next to the web code.
- **[jotquote/cli.py](jotquote/cli.py)** is a single 485-line file; moving it into a `cli/` subpackage mirrors the `api/` and `web/` layout and leaves room to split later without another rename.

## Proposed structure

```
jotquote/
├── __init__.py
├── api/
│   ├── __init__.py                 # re-exports the public surface (Quote,
│   │                               #   read_quotes, parse_quote, get_config,
│   │                               #   SECTION_*, ALL_CHECKS, LintIssue, ...)
│   │                               #   so `from jotquote import api` still works
│   ├── quote.py                    # Quote class, parse_quote, parse_tags,
│   │                               #   _assert_* validators, INVALID_CHARS*
│   ├── store.py                    # read_quotes(_with_hash), write_quotes,
│   │                               #   add_quote(s), set_quote, settags,
│   │                               #   _check_for_duplicates, get_sha256,
│   │                               #   _get_newline, format_quote
│   ├── config.py                   # get_config, get_filename, CONFIG_FILE,
│   │                               #   APP_NAME, SECTION_GENERAL/LINT/WEB,
│   │                               #   ALL_CHECKS, _migrate_legacy_section,
│   │                               #   _resolve_config_paths
│   ├── selection.py                # get_random_choice, get_first_match,
│   │                               #   _get_random_value
│   └── lint.py                     # LintIssue, lint_quotes, apply_fixes,
│                                   #   all _check_* helpers (moved from
│                                   #   top-level jotquote/lint.py)
├── cli/
│   ├── __init__.py                 # re-exports `main` so the console-script
│   │                               #   entry point `jotquote.cli:main` still
│   │                               #   resolves
│   └── cli.py                      # moved unchanged from jotquote/cli.py
├── resources/                      # renamed from templates/ — NOT Flask templates
│   ├── settings.conf
│   ├── settings.legacy.conf
│   └── quotes.txt
└── web/
    ├── __init__.py
    ├── helpers.py                  # renamed from core.py: TimestampFormatter,
    │                               #   configure_logging, sanitize_for_log,
    │                               #   get_enabled_checks, get_color_config,
    │                               #   abbreviate_timezone
    ├── viewer.py                   # was jotquote/web_viewer.py
    ├── editor.py                   # was jotquote/web_editor.py
    ├── templates/                  # Flask HTML templates
    │   ├── _font_faces.html
    │   ├── _head_common.html
    │   ├── _theme_toggle.html
    │   ├── about.html
    │   ├── editor.html
    │   ├── viewer.html             # renamed from quote.html
    │   └── unavailable.html
    └── static/
        ├── favicon.ico
        ├── fonts/
        └── icons/
```

### What this buys us

1. **Focused modules inside `api/`.** Each of `quote.py`, `store.py`, `config.py`, `selection.py`, and `lint.py` has one concern and can be read or tested without pulling the others.
2. **`from jotquote import api` still works** for external code: `jotquote/api/__init__.py` re-exports the existing public names so `api.Quote`, `api.read_quotes`, `api.SECTION_WEB`, `api.LintIssue`, etc. remain available as a single-import facade.
3. **Symmetrical layout — `api/`, `cli/`, `web/`** each live as a subpackage of `jotquote/`. Both Flask apps live in `web/` alongside the helpers they share. The WSGI paths become `jotquote.web.viewer:app` and `jotquote.web.editor:app`.
4. **Flask auto-discovers `web/templates/` and `web/static/`** because each `Flask(__name__)` call uses the module's own package. No Flask config changes needed once the files move.
5. **Clear separation of the two "template" concepts.** `resources/` holds files copied to `~/.jotquote/` on first run; `web/templates/` holds Jinja HTML.
6. **`viewer.html` matches `viewer.py`.** Renaming `quote.html` → `viewer.html` aligns the template name with the Flask app that renders it (the editor template is already `editor.html`).

## `api/__init__.py` re-exports

Every public name currently accessed as `api.X` from CLI, web, or tests is re-exported, so external call sites keep working. Exact list (derived from the current `jotquote/api.py` + `jotquote/lint.py`):

```python
# jotquote/api/__init__.py
from jotquote.api.config import (
    ALL_CHECKS,
    APP_NAME,
    CONFIG_FILE,
    SECTION_GENERAL,
    SECTION_LINT,
    SECTION_WEB,
    get_config,
    get_filename,
)
from jotquote.api.lint import LintIssue, apply_fixes, lint_quotes
from jotquote.api.quote import (
    INVALID_CHARS,
    INVALID_CHARS_QUOTE,
    Quote,
    parse_quote,
    parse_tags,
)
from jotquote.api.selection import get_first_match, get_random_choice
from jotquote.api.store import (
    add_quote,
    add_quotes,
    format_quote,
    get_sha256,
    parse_quotes,
    read_quotes,
    read_quotes_with_hash,
    read_tags,
    set_quote,
    settags,
    write_quotes,
)

__all__ = [ ... ]  # same symbol list
```

## `cli/__init__.py`

```python
# jotquote/cli/__init__.py
from jotquote.cli.cli import main

__all__ = ['main']
```

This keeps the `project.scripts` entry `jotquote = "jotquote.cli:main"` working in [pyproject.toml](pyproject.toml) without change.

## Docstring audit for `jotquote/api/`

Every public (non-underscore) function, method, and class in `jotquote/api/quote.py`, `store.py`, `config.py`, `selection.py`, and `lint.py` will have a docstring that:

- describes the function's purpose in one or two sentences,
- lists each parameter with its type and meaning,
- describes the return value with its type,
- uses a consistent style — Google-style (`Args:` / `Returns:` / `Raises:` blocks) is already in use in [jotquote/web_editor.py](jotquote/web_editor.py) and will be adopted across `api/`.

Example of the target style:

```python
def read_quotes_with_hash(filename):
    """Read quotes and compute the SHA-256 hash of the file in a single pass.

    Args:
        filename (str): Path to the quote file to read.

    Returns:
        tuple[list[Quote], str]: The parsed quotes and the hex SHA-256 digest of
            the file contents.

    Raises:
        click.ClickException: If the file does not exist or contains a duplicate
            or malformed quote.
    """
```

The split PR updates or adds docstrings for the following symbols (current public names in `api.py` + `lint.py`):

- `quote.py`: `Quote` (class) and methods `__init__`, `__eq__`, `__ne__`, `has_tag`, `has_tags`, `has_keyword`, `set_tags`, `get_hash`, `get_num_stars`, `get_line_number`; module functions `parse_quote`, `parse_tags`.
- `store.py`: `read_quotes`, `read_quotes_with_hash`, `read_tags`, `parse_quotes`, `add_quote`, `add_quotes`, `set_quote`, `settags`, `write_quotes`, `format_quote`, `get_sha256`.
- `config.py`: `get_config`, `get_filename`.
- `selection.py`: `get_first_match`, `get_random_choice`.
- `lint.py`: `lint_quotes`, `apply_fixes`; `LintIssue` dataclass fields documented.

## Test layout

Unit tests mirror the new package layout:

```
tests/
├── conftest.py
├── integration/
│   ├── conftest.py
│   ├── test_cli.py                  # was test_cli_integration.py (if present)
│   ├── test_web_viewer.py
│   └── test_web_editor.py
└── unit/
    ├── conftest.py
    ├── api/
    │   ├── __init__.py              # if current layout uses packages
    │   ├── test_quote.py            # from test_api.py — Quote + parsing tests
    │   ├── test_store.py            # from test_api.py — read/write/add tests
    │   ├── test_config.py           # from test_api.py — settings.conf tests
    │   ├── test_selection.py        # from test_api.py — RNG + get_first_match
    │   └── test_lint.py             # was tests/unit/test_lint.py
    ├── cli/
    │   └── test_cli.py              # was tests/unit/test_cli.py
    └── web/
        ├── test_helpers.py          # was tests/unit/web/test_core.py
        ├── test_viewer.py           # was tests/unit/test_web_viewer.py
        └── test_editor.py           # was tests/unit/test_web_editor.py
```

Existing `tests/unit/test_api.py` is split along the same lines as `api.py` itself, so each new test file targets exactly one of the new modules. No test logic changes — just relocation and import updates.

## Files that need edits (beyond renames/moves)

- [jotquote/cli.py](jotquote/cli.py) (moving to `cli/cli.py`) — imports already use `from jotquote import api` and `api.X`; those keep working thanks to `api/__init__.py` re-exports. Update the two lazy web imports: `import jotquote.web_viewer` → `import jotquote.web.viewer`, `import jotquote.web_editor` → `import jotquote.web.editor`.
- **New `web/viewer.py` and `web/editor.py`** — `from jotquote import api, lint` → `from jotquote import api` (since lint is now `api.lint`, or import as `from jotquote.api import lint`). `from jotquote.web import core as web_core` → `from jotquote.web import helpers as web_helpers`. Update `render_template('quote.html', ...)` → `render_template('viewer.html', ...)` in `web/viewer.py`.
- [jotquote/web/core.py](jotquote/web/core.py) — renamed to `helpers.py`; `from jotquote import api` still works via the re-export facade, no change needed there.
- **[pyproject.toml](pyproject.toml)** — `hatch.build.targets.wheel.include` needs the new paths (`jotquote/resources/**`, `jotquote/web/templates/**`, `jotquote/web/static/**`). `project.scripts` entry stays the same.
- **[CLAUDE.md](CLAUDE.md) and [DOCUMENTATION.md](DOCUMENTATION.md)** — update WSGI invocation examples (`jotquote.web_viewer:app` → `jotquote.web.viewer:app`, same for editor), the Architecture section's module list (describe the `api/`, `cli/`, `web/` subpackages), and the template path (`jotquote/templates/quotes.txt` → `jotquote/resources/quotes.txt`).
- **Template-copy paths in `api/config.py`** — the `get_config()` first-run code reads `jotquote/templates/settings.conf` and `jotquote/templates/quotes.txt`; these become `jotquote/resources/settings.conf` and `jotquote/resources/quotes.txt`.
- **Tests** — imports updated to the new layout. Because `api/__init__.py` re-exports, `from jotquote import api` in tests continues to work; only web- and CLI-specific module-path imports change (`jotquote.web_viewer` → `jotquote.web.viewer`, `jotquote.web_editor` → `jotquote.web.editor`, `jotquote.web.core` → `jotquote.web.helpers`). `tests/conftest.py`, `tests/unit/conftest.py`, `tests/integration/conftest.py`, `tests/integration/test_web_editor.py` all touch those paths.

## Breaking changes

Hard break — no compat shims. `from jotquote import api` continues to work (via the new `api/__init__.py`), so that is **not** a breaking change. The breaks are:

- Users running their own WSGI server update the module path from `jotquote.web_viewer:app` → `jotquote.web.viewer:app` (and the same for editor).
- Any code that imported `jotquote.lint` directly (rather than through `api`) changes to `jotquote.api.lint`.
- Any code that imported `jotquote.web.core` changes to `jotquote.web.helpers`.

No version bump and no [CHANGELOG.md](CHANGELOG.md) edit as part of this PR — those are handled out-of-band when the release is cut.

## Delivery

Single PR. Every import + doc + test is updated together, so `uv run pytest` and `uv run ruff check jotquote/` stay green at each commit boundary and the release can go out atomically.

## Verification

1. `uv run ruff check jotquote/` — clean.
2. `uv run pytest` — full suite passes (including the relocated `tests/unit/api/*`, `tests/unit/cli/*`, `tests/unit/web/*`).
3. `export JOTQUOTE_CONFIG=jotquote/resources/settings.conf && uv run jotquote lint` — built-in quotes remain lint-clean (confirms the renamed resource directory resolves correctly).
4. `uv run jotquote webserver` and `uv run jotquote webeditor` — each starts, serves the root page, renders CSS + fonts (confirms `web/static/` is discovered) and HTML (confirms `web/templates/` is discovered; confirms `viewer.html` renders).
5. `python -c "from jotquote import api; print(api.Quote, api.read_quotes, api.SECTION_WEB, api.LintIssue)"` — the re-export facade exposes all advertised symbols.
6. `uv build` — wheel inspection (`unzip -l dist/*.whl`) should show `jotquote/resources/*`, `jotquote/web/templates/*`, `jotquote/web/static/*`, and the new `api/` and `cli/` subpackage `.py` files.
