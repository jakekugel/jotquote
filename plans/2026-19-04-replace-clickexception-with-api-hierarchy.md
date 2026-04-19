# Replace `click.ClickException` in `jotquote/api/` with an `ApiException` hierarchy

## Context

The `jotquote/api/` modules currently raise `click.ClickException` as the catch-all error type for every failure — 33 raise sites across [config.py](../jotquote/api/config.py), [quote.py](../jotquote/api/quote.py), and [store.py](../jotquote/api/store.py). This couples the business-logic layer to the Click CLI framework and forces non-CLI callers (the Flask web editor, future third-party extensions) to either import Click just to handle errors or discriminate on error-message substrings.

This plan removes `click.ClickException` from `jotquote/api/` entirely, replacing it with a small domain-specific exception hierarchy rooted at a new `ApiException`. Standard-library exceptions (`TypeError`, `ValueError`) are used for programmer-misuse cases that shouldn't be caught by user-level handlers. The CLI layer catches `ApiException` and re-raises as `ClickException` to preserve existing CLI behavior; the web editor catches `ApiException` instead of `ClickException`.

No user-visible behavior changes (CLI messages, exit codes, web editor re-render flow) — this is a refactor of how errors are typed and dispatched, not what they say or when they occur.

## Exception hierarchy

New module: `jotquote/api/exceptions.py`.

```python
class ApiException(Exception):
    """Base class for all user-facing errors raised by jotquote.api."""


class ConfigError(ApiException):
    """Raised for problems loading or interpreting settings.conf."""


class QuoteValidationError(ApiException):
    """Raised when parsing a quote, tag, or field fails validation.

    Attributes:
        field (str | None): Which field the error applies to —
            'quote', 'author', 'publication', or 'tags'. May be None for
            structural errors (e.g., wrong pipe count).
    """
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


class QuoteNotFoundError(ApiException):
    """Raised when a quote selector (line number, hash) matches no quote."""


class DuplicateQuoteError(ApiException):
    """Raised when adding a quote that is already present in the file."""


class ConcurrentModificationError(ApiException):
    """Raised when the quote file's SHA-256 no longer matches what the caller expected.

    Attributes:
        expected_sha256 (str): The hash the caller passed in.
        current_sha256 (str | None): The file's current hash on disk. May be None
            if the check failed before a current hash could be computed.
    """
    def __init__(self, message: str, expected_sha256: str, current_sha256: str | None = None):
        super().__init__(message)
        self.expected_sha256 = expected_sha256
        self.current_sha256 = current_sha256


class StorageError(ApiException):
    """Raised for I/O failures, missing quote files, and backup sanity check failures."""
```

Re-exported from [jotquote/api/__init__.py](../jotquote/api/__init__.py) so callers use `api.ApiException`, `api.ConcurrentModificationError`, etc. `__all__` updated accordingly.

## Mapping: every current raise site → new exception

Every `click.ClickException` raise in [jotquote/api/](../jotquote/api/) is reclassified. Messages are preserved verbatim so existing `pytest.raises(..., match='...')` assertions keep working where they're re-typed rather than rewritten.

### [config.py](../jotquote/api/config.py)

| Line | Current | New |
|---|---|---|
| 125 | `ClickException` — `'quote_file' is not set in [general]...` | `ConfigError` |
| 151 | `ClickException` — quote file specified in settings.conf not found | `ConfigError` |

### [quote.py](../jotquote/api/quote.py)

| Line | Current | New |
|---|---|---|
| 132 | `ClickException` — tags is not a list | **`TypeError`** (programmer misuse, not user error) |
| 267 | `ClickException` — "a quote was not found" | `QuoteValidationError(field='quote')` |
| 270 | `ClickException` — author missing | `QuoteValidationError(field='author')` |
| 281 | `ClickException` — embedded pipe | `QuoteValidationError(field='quote')` |
| 296 | `ClickException` — can't find hyphen separator | `QuoteValidationError()` |
| 319 | `ClickException` — unable to parse author/publication | `QuoteValidationError()` |
| 336 | `ClickException` — wrong pipe count | `QuoteValidationError()` |
| 353 | `ClickException` — invalid tag chars | `QuoteValidationError(field='tags')` |
| 391 | `ClickException` — forbidden char in field | `QuoteValidationError(field=component_name)` |

### [store.py](../jotquote/api/store.py)

| Line | Current | New |
|---|---|---|
| 48  | `ClickException` — "quote file not found" (read_quotes_with_hash) | `StorageError` |
| 127 | `ClickException` — wraps parse error with line number | `QuoteValidationError` |
| 155 | `ClickException` — both `-s` and `-n` | **`ValueError`** (programmer misuse: CLI validates before calling) |
| 157 | `ClickException` — neither `-n` nor `-s` | **`ValueError`** |
| 163 | `ClickException` — quote number out of range | `QuoteNotFoundError` |
| 168 | `ClickException` — hash matches no quote | `QuoteNotFoundError` |
| 210 | `ClickException` — SHA mismatch in `set_quote` | `ConcurrentModificationError(expected_sha256=sha256, current_sha256=current_sha)` |
| 219 | `ClickException` — no quote at line number | `QuoteNotFoundError` |
| 242 | `ClickException` — quote is not Quote type (add_quote) | **`TypeError`** |
| 267 | `ClickException` — quote file doesn't exist (add_quotes) | `StorageError` |
| 270 | `raise Exception(...)` — newquotes is not a list | **`TypeError`** (was already a bug: bare Exception) |
| 282 | `ClickException` — duplicate against existing quote | `DuplicateQuoteError` |
| 315 | `ClickException` — quote file not found (write_quotes) | `StorageError` |
| 320 | `ClickException` — SHA mismatch in `write_quotes` | `ConcurrentModificationError(expected_sha256=expected_sha256, current_sha256=current_sha)` |
| 355 | `ClickException` — backup larger than tmp | `StorageError` |
| 366 | `ClickException` — backup has more lines than tmp | `StorageError` |
| 376 | `except click.ClickException: raise` — internal guard | `except ApiException: raise` |
| 380 | `ClickException` — generic write error | `StorageError` |
| 387 | `ClickException` — os.replace failed | `StorageError` |
| 406 | `ClickException` — quote is not Quote type (format_quote) | **`TypeError`** |
| 425 | `ClickException` — duplicate in `_check_for_duplicates` | `DuplicateQuoteError` |
| 441 | `ClickException` — invalid `line_separator` config value | `ConfigError` |

After the refactor, none of `jotquote/api/config.py`, `jotquote/api/quote.py`, or `jotquote/api/store.py` will `import click`. [jotquote/api/selection.py](../jotquote/api/selection.py) and [jotquote/api/lint.py](../jotquote/api/lint.py) already don't.

## Changes by file

### New: `jotquote/api/exceptions.py`
Contains the 7 classes above. Pure definitions, no imports from anywhere else in the package.

### [jotquote/api/__init__.py](../jotquote/api/__init__.py)
Add imports from `jotquote.api.exceptions`; extend `__all__` with `ApiException`, `ConfigError`, `QuoteValidationError`, `QuoteNotFoundError`, `DuplicateQuoteError`, `ConcurrentModificationError`, `StorageError`.

### [jotquote/api/config.py](../jotquote/api/config.py), [jotquote/api/quote.py](../jotquote/api/quote.py), [jotquote/api/store.py](../jotquote/api/store.py)
Per the mapping table above. Remove `import click` from all three.

### [jotquote/cli/cli.py](../jotquote/cli/cli.py)
Add a decorator that translates `ApiException` into `click.ClickException` so exit codes and CLI formatting stay identical:

```python
import functools

def _translate_api_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except api.ApiException as e:
            raise click.ClickException(str(e)) from e
    return wrapper
```

Apply to every subcommand function (`add`, `list`, `random`, `today`, `showalltags`, `settags`, `info`, `webserver`, `webeditor`, `lint`) and to the top-level `jotquote` group (for errors raised during `get_config()`). Placement: directly above the function definition, below the `@click.command` / `@click.pass_context` decorators, so it runs innermost.

### [jotquote/web/editor.py](../jotquote/web/editor.py)
Line 111: change `except click.ClickException as e` → `except api.ApiException as e`. Replace `e.format_message()` with `str(e)`. Remove `import click` if it has no other use in this file (grep-verified during implementation).

### [jotquote/web/viewer.py](../jotquote/web/viewer.py)
No current `except click.ClickException` catches, but quote-loading failures currently propagate as `ClickException` and the viewer doesn't handle them explicitly. Behavior after refactor: `ApiException` propagates instead. Flask's default error handler produces a 500; current behavior also produces a 500 via Flask's `ClickException`→`InternalServerError` conversion. No functional change; no code change needed, but spot-check during verification.

## Test strategy

Red/green TDD per [CLAUDE.md](../CLAUDE.md): for each new exception subclass, write a failing unit test first (asserting the new class is raised at the matching call site), confirm it fails, then change the raise site to make it pass.

### Unit-test updates (existing tests, re-typed)

- [tests/unit/api/test_config.py:153](../tests/unit/api/test_config.py#L153) — `click.ClickException` → `api.ConfigError`
- [tests/unit/api/test_quote.py](../tests/unit/api/test_quote.py) — 10 `pytest.raises(Exception, ...)` and `pytest.raises(click.ClickException, ...)` sites → `api.QuoteValidationError` (keep the `match=` strings as-is)
- [tests/unit/api/test_store.py](../tests/unit/api/test_store.py) — ~15 assertions, retype to the correct subclass per the mapping table:
  - SHA mismatch tests → `api.ConcurrentModificationError`
  - "was not found" / "does not exist" → `api.StorageError`
  - out-of-range / "No quote found at line" → `api.QuoteNotFoundError`
  - "both -s and -n" / "either -n or -s" → `ValueError`
  - "quote parameter must be type class Quote" / "tags parameter" → `TypeError`

### New unit tests (one per new exception class, covering structured data where present)

In a new `tests/unit/api/test_exceptions.py`:

1. `ApiException` is a subclass of `Exception` and all 6 concrete classes inherit from it (so `except api.ApiException` catches everything)
2. `QuoteValidationError.field` is set correctly when raised from `parse_quote` on an invalid-char-in-author input
3. `ConcurrentModificationError.expected_sha256` and `.current_sha256` are set correctly when raised from `set_quote` after an out-of-band file modification
4. `DuplicateQuoteError` carries the duplicate quote text in its message (parity with current message format)
5. `ConfigError` raised when `[general]` section is missing `quote_file`

### New integration tests (minimum one per [CLAUDE.md](../CLAUDE.md))

In [tests/integration/test_cli.py](../tests/integration/test_cli.py):

1. **CLI behavior unchanged** — run `jotquote settags -n 999 "x"` against a 4-quote fixture via `CliRunner.invoke()`, assert `result.exit_code == 1` and `'out of range' in result.output`. Confirms the decorator correctly translates `QuoteNotFoundError` → `ClickException` → CLI exit.

In [tests/integration/test_web_editor.py](../tests/integration/test_web_editor.py):

2. **Web editor concurrent modification** — load the editor for a line, mutate the underlying file externally, POST the save with the stale `sha256`, assert the response re-renders with the "modified by another process" message (confirms the except-site switch from `ClickException` to `ApiException` still flows).

## Verification

1. **No more `click.ClickException` in api/**: `grep -rn 'click\.ClickException\|from click' jotquote/api/` returns zero hits. `grep -rn '^import click' jotquote/api/` returns zero hits.
2. **Facade re-exports the new types**: `python -c "from jotquote import api; print(api.ApiException, api.ConcurrentModificationError)"` succeeds.
3. **Tests pass**: `uv run pytest` — all green.
4. **Lint clean**: `uv run ruff check jotquote/` — no new warnings.
5. **CLI UX unchanged**: `uv run jotquote settags -n 999 "x"` against a small fixture prints the same error message and exits with the same code as before the refactor.
6. **Built-in lint still clean** (per project convention): `JOTQUOTE_CONFIG=jotquote/resources/settings.conf uv run jotquote lint` — no issues.
7. **`API_REFERENCE.md` consistency**: update the "Raises" wording in [API_REFERENCE.md](../API_REFERENCE.md) — every `Raises click.ClickException` line becomes `Raises ApiException` (or the most specific subclass where the raise site is a single class). Add a new "Exceptions" section documenting the hierarchy with a small code example showing a caller catching `ConcurrentModificationError` specifically.

## Out of scope

- **Web editor HTTP status-code improvements**: the editor currently always re-renders HTML on error. Translating `ConcurrentModificationError` → 409 and `QuoteValidationError` → 400 becomes *easy* after this refactor, but the behavior change itself is a separate PR.
- **Web viewer error handling**: viewer currently relies on Flask's default 500 for api errors; unchanged.
- **`jotquote.api.lint` and `jotquote.api.selection`**: neither currently raises `ClickException`, so neither changes.
- **Backward-compat shim**: no `ApiException` → `ClickException` alias is provided. Any external caller that had `except click.ClickException` against this API must migrate to `except api.ApiException`. This is explicit in the user's request ("remove all references to ClickException").
