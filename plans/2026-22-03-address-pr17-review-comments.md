# Plan: Address PR #17 Review Comments

## Context

PR #17 adds a linter feature to jotquote. The PR reviewer (jakekugel) left 4 comments requesting improvements to code quality and style.

## PR Comments and Fixes

### 1. `jotquote/api.py` line 409 — Add getter for `line_number`

**Comment**: "Can you check if other class properties have a getter method, and add one if so? If they don't have getter methods, then no need for this property."

**Analysis**: The `Quote` class has two getter-style methods: `get_hash()` (line 88) and `get_num_stars()` (line 93). These are the pattern for the class. Direct attributes (`quote`, `author`, `publication`, `tags`) are accessed directly without getters.

**Fix**: Add a `get_line_number()` method to the `Quote` class (after `get_num_stars()` at line 98):
```python
def get_line_number(self):
    """Return the line number of this quote in the quote file."""
    return self.line_number
```

**File**: `jotquote/api.py`

---

### 2. `jotquote/api.py` lines 599–608 — Move lint defaults to `jotquote` section

**Comment**: "This is so concise that it does not need to be in a new section, you can just add a new property to the existing section of the conf file"

**Fix**: Replace the `jotquote.lint` section defaults with properties added to the `jotquote` section. Change:
```python
# Add lint section defaults in memory if not present in the config file
if not config.has_section('jotquote.lint'):
    config.add_section('jotquote.lint')
    config['jotquote.lint']['enabled_checks'] = (...)
    config['jotquote.lint']['visibility_tags'] = ''
    config['jotquote.lint']['spell_ignore'] = ''
    config['jotquote.lint']['author_antipattern_regex'] = ''
```
To:
```python
# Add lint defaults in memory to the jotquote section if not present
if not config.has_option(APP_NAME, 'enabled_checks'):
    config[APP_NAME]['enabled_checks'] = (...)
    config[APP_NAME]['visibility_tags'] = ''
    config[APP_NAME]['spell_ignore'] = ''
    config[APP_NAME]['author_antipattern_regex'] = ''
```

**Cascading changes** (config section name `jotquote.lint` → `jotquote`):
- `jotquote/lint.py` line 47: `lint_cfg = config['jotquote.lint']` → `lint_cfg = config['jotquote']`
- `jotquote/cli.py` line 267: `config.get('jotquote.lint', 'enabled_checks', ...)` → `config.get('jotquote', 'enabled_checks', ...)`

---

### 3. `jotquote/cli.py` lines 253–268 — Extract helper method for active check set

**Comment**: "Can you create a private helper method in cli.py to determine the active check set?"

**Fix**: Extract lines 253–268 into a `_get_active_checks(select_checks, ignore_checks, config)` function defined near the bottom of `cli.py` (alongside `_add_quotes()`). Replace the inline block with a call to the helper.

```python
def _get_active_checks(select_checks, ignore_checks, config):
    """Determine the set of lint checks to run based on CLI flags and config."""
    from jotquote import lint as lintmod
    all_checks = lintmod.ALL_CHECKS
    if select_checks:
        checks = {c.strip() for c in select_checks.split(',') if c.strip()}
        invalid = checks - all_checks
        if invalid:
            raise click.ClickException('Unknown check(s): {}'.format(', '.join(sorted(invalid))))
    elif ignore_checks:
        ignore = {c.strip() for c in ignore_checks.split(',') if c.strip()}
        invalid = ignore - all_checks
        if invalid:
            raise click.ClickException('Unknown check(s): {}'.format(', '.join(sorted(invalid))))
        checks = all_checks - ignore
    else:
        raw = config.get('jotquote', 'enabled_checks', fallback='')
        checks = {c.strip() for c in raw.split(',') if c.strip()} if raw.strip() else all_checks
    return checks
```

In `lint()`, replace the 16-line block with:
```python
checks = _get_active_checks(select_checks, ignore_checks, config)
```

Also remove the `from jotquote import lint as lintmod` import that would now be duplicated (keep only in `_get_active_checks`). Note: `lintmod` is still used later in `lint()` for `lintmod.lint_quotes()` and `lintmod.apply_fixes()`, so keep the import at the top of the `lint()` function as well.

---

### 4. `jotquote/lint.py` lines 9–19 — Format ALL_CHECKS one per line with comments

**Comment**: "Can you format this one per line, and include a code comment explaining what each is?"

**Fix**: Reformat `ALL_CHECKS`:
```python
ALL_CHECKS = frozenset({
    'ascii',            # Flag non-ASCII characters in quote, author, or publication
    'smart-quotes',     # Flag (and fix) typographic/smart quote characters
    'spelling',         # Flag possible misspellings in the quote text (requires pyspellchecker)
    'no-tags',          # Flag quotes with no tags
    'no-author',        # Flag quotes with no author
    'author-antipatterns',  # Flag author fields matching known bad patterns (anonymous, trailing punctuation, all-caps)
    'multiple-stars',   # Flag quotes with more than one star-rating tag
    'no-star',          # Flag quotes with no star-rating tag
    'no-visibility',    # Flag quotes missing a configured visibility tag
})
```

---

## Critical Files

- `jotquote/api.py` — Add `get_line_number()` to `Quote`; change lint defaults to use `jotquote` section
- `jotquote/cli.py` — Extract `_get_active_checks()` helper; update section reference
- `jotquote/lint.py` — Reformat `ALL_CHECKS`; update section reference

## Verification

```bash
uv run pytest                  # All existing tests should pass
uv run ruff check jotquote/    # No lint errors
uv run jotquote lint --help    # CLI still works
```
