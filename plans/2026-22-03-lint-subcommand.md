# Plan: `lint` Subcommand

## Context

jotquote has no way to check the quality or consistency of a quote collection. Over time a quote file accumulates issues: smart quotes copied from web pages, missing tags, inconsistent author formatting, non-ASCII characters, and more. This plan adds a `jotquote lint` subcommand that surfaces these problems and, where safe to do so, auto-fixes them with a `--fix` flag.

## Goal

Add `jotquote lint` — a configurable quality checker for the quote file. Running without options reports all issues; `--fix` applies safe auto-corrections; `--select`/`--ignore` control which checks run. Exit code 0 = clean, 1 = issues found, 2 = fatal error.

---

## Checks

| Check name | Description | Fixable |
|---|---|---|
| `ascii` | Non-ASCII characters in any field | No |
| `smart-quotes` | Curly/typographic quotes in any field | Yes |
| `spelling` | Misspelled words in quote text (pyspellchecker) | No |
| `no-tags` | Quote has no tags at all | No |
| `no-author` | Author field is empty | No |
| `author-antipatterns` | Author/publication matches a known bad pattern | Partial |
| `multiple-stars` | More than one star tag (1star…5stars) | No |
| `no-star` | No star tag present | No |
| `no-visibility` | No tag from the configured `visibility_tags` list | No |

All checks are **enabled by default** and individually toggleable via `settings.conf` or `--select`/`--ignore`.

---

## `author-antipatterns` sub-checks

1. **Unknown/Anonymous variants** — matches `unknown`, `anonymous`, `anon`, `n/a`, `none`, `?`
2. **Trailing punctuation** — ends with `. , ; : ! ?` — **fixable** with `--fix`
3. **All-caps names** — word of 3+ uppercase letters (acronyms/initials allowed)
4. **Configurable regex patterns** — user-defined regexes in `settings.conf`

---

## CLI Design

```
jotquote lint [OPTIONS]
```

Options: `--fix`, `--select TEXT`, `--ignore TEXT`, `--format [text|json]`, `--quiet`/`-q`

### Text output

```
line 3: [no-author] No author specified
line 3: [smart-quotes] Smart quotes in quote text (fixable): "hello"
line 17: [author-antipatterns] Author matches unknown/anonymous pattern: "Unknown"
```

Summary line always printed. Exit 0 = clean, 1 = issues found.

### JSON output

Array of `{line, check, field, message, fixable}` objects.

---

## New `[jotquote.lint]` config section

Auto-created in `get_config()` with defaults: `enabled_checks`, `visibility_tags`, `spell_ignore`, `author_antipattern_regex`.

---

## Implementation

### `api.py` changes
- `Quote` gains optional `line_number: int = 0` attribute (set in `__init__`)
- `parse_quotes()` sets `quote.line_number = linenum` when building each Quote
- `get_config()` writes `[jotquote.lint]` defaults if section absent

### New `jotquote/lint.py`
- `LintIssue` dataclass: `line_number`, `check`, `field`, `message`, `fixable`, `fix_value`
- `lint_quotes(quotes, checks, config)` — runs all enabled checks, returns list of `LintIssue`
- `apply_fixes(quotes, issues)` — returns corrected quote list + fix count
- Nine private check helpers; `spelling` lazy-imports `pyspellchecker`

### `cli.py` — new `lint` subcommand
- Validates `--select`/`--ignore` mutual exclusion
- Builds active check set from config + CLI flags
- Calls `lint_quotes()` from lint module
- Handles `--fix`: calls `apply_fixes()` then `write_quotes()`
- Outputs results in text or JSON format
- Exits with appropriate code (0/1/2)

---

## `pyproject.toml`
- `pyspellchecker>=0.7` as optional dep under `[project.optional-dependencies]` `lint` extra
- Added to dev dependencies group so tests can run spelling check

---

## Files modified
- `jotquote/api.py` — Quote.line_number attribute, parse_quotes line tracking, get_config lint section
- `jotquote/cli.py` — new `lint` subcommand
- `pyproject.toml` — pyspellchecker optional + dev dep
- `tests/conftest.py` — added jotquote.lint section to config fixture
- `tests/cli_test.py` — lint subcommand tests

## Files created
- `jotquote/lint.py` — LintIssue, lint_quotes, apply_fixes, check helpers
- `tests/lint_test.py` — unit tests for lint.py checks
- `plans/2026-22-03-lint-subcommand.md` — this file

---

## Verification

```bash
# Install with lint extra
uv sync --group dev

# Run all tests (262 passed, 1 skipped)
uv run pytest

# Lint clean
uv run ruff check jotquote/

# Manual smoke test
jotquote lint
jotquote lint --format json
jotquote lint --select smart-quotes
jotquote lint --ignore spelling
jotquote lint --fix
```
