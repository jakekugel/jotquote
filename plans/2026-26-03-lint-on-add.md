# Plan: Run Linter Automatically on `jotquote add`

## Context

The `jotquote lint` subcommand exists but runs separately. Users must remember to run it after adding quotes. This change makes `jotquote add` lint quotes **before** writing them to the file. If issues are found, the user is prompted to confirm the add. This catches quality issues at the point of entry.

No new `settings.conf` properties are introduced — the existing `lint_enabled_checks` config controls which checks run, and the new skip option is a CLI flag only.

## Behavior

1. User runs `jotquote add "some quote - author"` (or `jotquote add -` for stdin).
2. Quote(s) are parsed (existing logic).
3. Unless `--no-lint` is passed, lint checks run on the parsed quote(s) using the active check set from config.
4. **No issues found** (or `--no-lint`): quote(s) are added normally.
5. **Issues found**: warnings are displayed, user is prompted `"Lint issues found. Would you like to add the quote anyway? (y/N): "`. On `N` (default), the add is aborted with exit code 1. On `y`, the quote(s) are added.
6. For stdin multi-quote adds (`jotquote add -`), all quotes are linted together with a single batch prompt.

## Changes

### `jotquote/cli.py`

- Added `--no-lint` flag to the `add` command (mirrors git's `--no-verify` convention).
- Added `_lint_new_quotes(quotes)` helper that lazy-imports `lint`, resolves active checks from config via `_get_active_checks`, and runs them. Exceptions propagate (no try/except wrapping).
- Modified `_add_quotes()` to accept `no_lint` parameter. When lint is enabled, quotes are linted after parsing but before writing. Warnings are displayed and `click.confirm(default=False)` gates the add. For stdin path, `click.confirm(..., err=True)` is used since stdin was consumed for quote data.

### `tests/cli_test.py`

- Added `--no-lint` to existing add tests to prevent lint interference with pre-existing test assertions.
- Added 6 new tests: `test_add_lint_warnings_shown_and_confirmed`, `test_add_lint_warnings_declined`, `test_add_lint_no_warnings_when_clean`, `test_add_lint_respects_enabled_checks`, `test_add_no_lint_flag_skips_checks`, `test_add_lint_exception_propagates`.

### `tests/cli_integration_test.py`

- Added `--no-lint` to existing `test_ascii_only` and `test_show_author_count` integration tests.
- Added `test_add_shows_lint_warnings_integration` — subprocess test with smart-quote input, confirms with `y`, verifies warnings and successful add.

## Design decisions

- **`--no-lint` flag**: CLI-only, no new config property needed.
- **Lint before add**: gates the add on lint results per user request.
- **Default N on prompt**: conservative — user must opt in to adding a quote with issues.
- **Batch prompt for stdin**: one prompt for all quotes rather than per-quote.
- **No try/except around lint**: exceptions propagate to caller as requested.
