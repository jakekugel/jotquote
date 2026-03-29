# Plan: Address PR #17 Unresolved Review Comments

## Context

PR #17 (`feature/linter`) adds a linting subsystem to jotquote. The reviewer left 18 unresolved comments requesting code quality improvements, removal of the `spelling` check, tag corrections in the built-in quote file, and cleanup of configuration handling. This plan addresses all 18 comments.

---

## Changes by File

### jotquote/lint.py (comments #1, #2, #3, #4, #14, #15, #16, #17)

**Remove `spelling` check entirely** (comment #17 — biggest change):
- Remove `'spelling'` from `ALL_CHECKS` (line 14)
- Remove `_SPELL_IGNORE_BUILTIN` frozenset (line 54) — makes comment #1 moot
- Remove `_make_spellchecker()` function (~lines 240–253)
- Remove `_check_spelling()` function (~lines 256–273)
- Remove the `spell, ignore_words = _make_spellchecker(...)` line in `lint_quotes` (~line 70)
- Remove the `if spell is not None: issues.extend(_check_spelling(...))` block (~lines 83–84)

**Remove `multiple-stars` check** (comments #14, #15):
- Remove `'multiple-stars'` from `ALL_CHECKS` (line 20)
- Remove `_STAR_TAGS` frozenset (line 48)
- Remove `_check_multiple_stars()` function (~lines 344–355)
- Remove the `if 'multiple-stars' in checks:` block in `lint_quotes` (~lines 91–92)

**Add comment for `field` allowed values in `LintIssue`** (comment #16):
- Add inline comment on the `field: str` line (~line 61) stating allowed values are `'quote'`, `'author'`, `'publication'`, `'tags'`

**Add comment before `sq`, `sd`, `ds` variables** (comment #2):
- Add a one-line comment above the `for field_name in ('quote', 'author', 'publication'):` block (~line 115) explaining it applies smart-quote, smart-dash, and double-space fixes to each field

**Add docstrings to all `_check_*` functions** (comments #3, #4):
- `_check_ascii` — flags non-ASCII characters in quote, author, or publication fields
- `_check_smart_quotes` — flags and fixes typographic/smart quote characters
- `_check_smart_dashes` — flags and fixes unicode dash/hyphen variants
- `_check_double_spaces` — flags and fixes runs of multiple consecutive spaces
- `_check_quote_length` — flags quotes exceeding the configured maximum length
- `_check_no_tags` — flags quotes with no tags
- `_check_no_author` — flags quotes with no author
- `_check_author_antipatterns` — flags author fields matching known bad patterns
- `_check_required_tag_groups` — flags quotes missing a tag from a required tag group

---

### jotquote/templates/settings.conf (comment #12)

Add `lint_author_antipattern_regex` with empty default so it no longer needs to be set in-memory in api.py:

```
lint_author_antipattern_regex =
```

---

### jotquote/api.py (comments #10, #11, #12)

**Fix comment at line 601** (comment #10):
- Change `# Copy the default quote file if the resolved path doesn't exist` to `# If the quote file doesn't exist, copy the template quotes.txt to the configuration directory, usually ~/.jotquote/quotes.txt`

**Derive `enabled_checks` from `ALL_CHECKS`** (comment #11):
- Import `ALL_CHECKS` from `jotquote.lint` at the top of api.py
- Replace the hardcoded `enabled_checks` string (~line 618) with `', '.join(sorted(ALL_CHECKS))`

**Remove in-memory config defaults** (comment #12):
- Remove `config[APP_NAME]['spell_ignore'] = ''` (line 620) — spelling is gone
- Remove `config[APP_NAME]['author_antipattern_regex'] = ''` (line 621) — now in settings.conf
- The `if not config.has_option(...)` block now only sets `enabled_checks`

---

### jotquote/cli.py (comment #13)

**Update `--no-lint` help text** (comment #13, line 89):
- Change from: `'Skip lint checks when adding.'`
- Change to: `'Skip lint checks when adding (overrides lint_on_add in settings.conf).'`

---

### jotquote/templates/quotes.txt (comments #5–#9)

Tag corrections:
| Line | Quote (excerpt) | Old tag | New tag |
|------|-----------------|---------|---------|
| 9 | "Life is what happens while you are making other plans" | `life` | `flexibility` |
| 13 | "Those who have knowledge don't predict..." | `knowledge` | `predictions` |
| 15 | "In theory, there is no difference between theory and practice..." | `knowledge` | `theories` |
| 20 | "Make everything as simple as possible, but not simpler" | `work` | `simplicity` |
| 34 | "The key to golf is managing your worst shots" | `sports` | `sports,life` |

---

### pyproject.toml (comment #17)

- Remove `pyspellchecker>=0.7` from `[project.optional-dependencies]` `lint` group
- Remove `pyspellchecker>=0.7` from `[dependency-groups]` `dev` group

---

### DOCUMENTATION.md (comment #17)

- Remove `spelling` from the list of valid `lint_enabled_checks` values
- Remove the `lint_spell_ignore` row from the settings table
- Add `lint_author_antipattern_regex` row if not already present (with default empty string)

---

### tests/ (comment #17)

Remove all spelling-related tests and config references:
- **tests/lint_test.py**: Remove the `_check_spelling` test block (~lines 445–461) and any other spelling test functions
- **tests/cli_test.py**: Remove `--ignore spelling` usage (~lines 640, 657) and related spelling comments (~line 615)
- **tests/conftest.py**: Remove `'spelling'` from `enabled_checks` list (~line 24–26); remove `spell_ignore` config entry (~line 28)

---

### plans/2026-22-03-address-pr17-review-comments.md (comment #18)

- Delete this file

---

## Tests

No new tests required for this change. Existing spelling-related tests will be removed; remaining tests cover the affected code paths.

## Verification

After implementation:

```bash
# Lint the built-in quote collection (must pass clean)
export JOTQUOTE_CONFIG=jotquote/templates/settings.conf
uv run jotquote lint

# Run full test suite
uv run pytest

# Run ruff linter
uv run ruff check jotquote/
```
