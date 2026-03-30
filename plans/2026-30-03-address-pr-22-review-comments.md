# Plan: Address PR #22 Review Comments

## Context

PR jakekugel/jotquote#22 ("Redesign config") redesigned the settings.conf format from a single `[jotquote]` section to three sections: `[general]`, `[lint]`, and `[web]`. The reviewer left 5 inline comments requesting changes before merge.

---

## Changes Required

### 1. Rename `on_add` → `lint_on_add` in `[lint]` section

**Files:** `jotquote/templates/settings.conf`, `jotquote/cli.py`, `jotquote/api.py` (migration), `DOCUMENTATION.md`

- In `jotquote/templates/settings.conf`: change `on_add = false` → `lint_on_add = false`
- In `jotquote/cli.py` line ~336: change `getboolean('on_add', fallback=False)` → `getboolean('lint_on_add', fallback=False)`
- In `_migrate_legacy_section` in `jotquote/api.py`: when mapping legacy `lint_on_add` to `[lint]`, do NOT strip the `lint_` prefix (keep it as `lint_on_add`). All other `lint_*` keys still get the prefix stripped.
- In `DOCUMENTATION.md`: update the settings table entry for this property.

---

### 2. Add backwards-compatibility comment before `_SECTION_LEGACY`

**File:** `jotquote/api.py` line ~38

Add a one-line comment immediately before `_SECTION_LEGACY = 'jotquote'`:

```python
# Retained for backwards compatibility with the old single-section [jotquote] config format
_SECTION_LEGACY = 'jotquote'
```

---

### 3. Create `_GENERAL_KEYS` and `_LINT_KEYS` frozensets

**File:** `jotquote/api.py`, near the existing `_WEB_KEYS` (line ~585)

Add two new frozensets using legacy (pre-migration) key names, analogous to `_WEB_KEYS`:

```python
_GENERAL_KEYS = frozenset(
    {
        'quote_file',
        'line_separator',
        'show_author_count',
    }
)

_LINT_KEYS = frozenset(
    {
        'lint_on_add',
        'lint_author_antipattern_regex',
    }
)
```

Update `_migrate_legacy_section` to use `_LINT_KEYS` and `_GENERAL_KEYS` instead of `startswith('lint_')`:

```python
if key in _LINT_KEYS:
    new_key = key if key == 'lint_on_add' else key[len('lint_'):]
    config[SECTION_LINT][new_key] = value
elif key in _WEB_KEYS:
    ...  # existing web logic unchanged
else:
    config[SECTION_GENERAL][key] = value
```

---

### 4 & 5. Refactor migration warning out of `api.py` into callers

**Files:** `jotquote/api.py`, `jotquote/cli.py`, `jotquote/web.py`, `tests/conftest.py`

#### `_migrate_legacy_section` (api.py ~line 601)
- Remove the `click.echo(...)` call
- Return `True` if migration occurred, `False` (or `None` → early return becomes `return False`) otherwise

#### `get_config` (api.py ~line 647)
- Capture the return value of `_migrate_legacy_section(config)`
- Return `(config, migrated)` tuple instead of just `config`
- Update docstring

#### `cli.py` call sites (5 total)
| Line | Change |
|------|--------|
| ~62 (main `jotquote()`) | `config, migrated = api.get_config()` + `if migrated: click.echo(warning, err=True)` |
| ~272 (lint command) | `config, _ = api.get_config()` |
| ~325 (`_lint_new_quotes`) | `config, _ = api.get_config()` |
| ~335 (`_add_quotes`) | `config, _ = api.get_config()` |
| ~379 (`_add_quotes` again) | `config, _ = api.get_config()` |

Warning message: `'Warning: settings.conf uses the deprecated [jotquote] section. Please update to [general], [lint], and [web] sections.'`

#### `web.py` call sites (3 total)
| Line | Change |
|------|--------|
| ~65 (`showpage`) | `config, _ = api.get_config()` |
| ~170 (`get_quotes`) | `config, _ = api.get_config()` |
| ~218 (`run_webserver`) | `config, migrated = api.get_config()` + `if migrated: app.logger.warning(warning_message)` |

#### `tests/conftest.py`
- The `config` fixture mocks `api.get_config`. Check if it needs updating to return a tuple.

---

## Critical Files

- [jotquote/api.py](jotquote/api.py) — `_SECTION_LEGACY` (~38), `_GENERAL_KEYS`/`_LINT_KEYS`/`_WEB_KEYS` (~582–598), `_migrate_legacy_section` (~601), `get_config` (~647)
- [jotquote/cli.py](jotquote/cli.py) — 5 `get_config()` call sites (~62, ~272, ~325, ~335, ~379); `lint_on_add` key read (~336)
- [jotquote/web.py](jotquote/web.py) — 3 `get_config()` call sites (~65, ~170, ~218)
- [jotquote/templates/settings.conf](jotquote/templates/settings.conf) — `lint_on_add` rename
- [DOCUMENTATION.md](DOCUMENTATION.md) — settings table update for `lint_on_add`
- [tests/conftest.py](tests/conftest.py) — may need tuple return update

---

## Tests to Add / Update

- Update `tests/conftest.py` `config` fixture mock if it wraps `get_config` (check return value)
- Add/update tests in `tests/cli_test.py` or `tests/cli_integration_test.py` for legacy migration warning via `click.echo`
- Add/update tests in `tests/web_test.py` or `tests/web_integration_test.py` for legacy migration warning via `app.logger`
- Update any tests referencing the `on_add` key name to `lint_on_add`

---

## Verification

```bash
# Lint check
uv run ruff check jotquote/

# Full test suite
uv run pytest

# Development verification (lint built-in quotes)
export JOTQUOTE_CONFIG=jotquote/templates/settings.conf
uv run jotquote lint

# Manual smoke test for legacy migration warning
# Create a temp settings.conf with [jotquote] section and verify the warning appears
```
