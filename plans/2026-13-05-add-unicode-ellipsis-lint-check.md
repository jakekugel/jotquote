# Add `unicode-ellipsis` lint check

## Context

The lint suite catches common typographic Unicode characters (smart quotes via `smart-quotes`, en/em dashes via `smart-dashes`) and auto-fixes them to their ASCII equivalents, but it does not flag the Unicode horizontal ellipsis `…` (U+2026). When a user pastes a quote from a typographic source, the ellipsis sneaks through as a single Unicode codepoint instead of `...`. Today the `ascii` check would flag it as a generic non-ASCII character with no auto-fix; we want a dedicated, fixable check named `unicode-ellipsis` that replaces `…` with three ASCII periods.

Outcome: `jotquote lint` reports `[unicode-ellipsis] Unicode ellipsis in <field>` for any quote/author/publication containing `…`; `jotquote lint --fix` rewrites the file with `…` replaced by `...`. The check is enabled by default like every other check in `ALL_CHECKS`.

## Design

Mirror the existing `smart-quotes` pattern exactly — it is the closest fit (single character class, simple ASCII-replacement fix, applies to the three text fields). No new abstractions are needed.

- Detection: a new `_check_unicode_ellipsis(quote)` helper that walks `quote`, `author`, `publication` and emits one `LintIssue` per affected field with `fixable=True` and `fix_value` pre-computed.
- Fix application: a new branch in `apply_fixes()` that, when a `unicode-ellipsis` issue is present on a field, replaces `…` with `...` on the current field value (per-check hard-coded, matching the smart-quotes/smart-dashes/double-spaces precedent).
- Skip from `ascii`: add `'…'` to `_ASCII_SKIP` so the `ascii` check does not double-flag the same character (this is how smart-quote and smart-dash characters are already excluded — see [lint.py:153](jotquote/api/lint.py#L153)).

## Files to modify

### 1. [jotquote/api/lint.py](jotquote/api/lint.py)

- After the dash maps (around [lint.py:32](jotquote/api/lint.py#L32)), add a module constant:
  ```python
  _UNICODE_ELLIPSIS = '…'
  ```
- Extend `_ASCII_SKIP` at [lint.py:153](jotquote/api/lint.py#L153) to include `frozenset(_UNICODE_ELLIPSIS)` so `_check_ascii` does not also flag the ellipsis.
- Add a dispatch line in `lint_quotes()` inside the per-quote loop ([lint.py:79-97](jotquote/api/lint.py#L79-L97)), grouped with the other text-field checks:
  ```python
  if 'unicode-ellipsis' in checks:
      issues.extend(_check_unicode_ellipsis(quote))
  ```
- Add a new check helper modeled on `_check_smart_quotes` at [lint.py:176-194](jotquote/api/lint.py#L176-L194):
  ```python
  def _check_unicode_ellipsis(quote):
      """Flag and fix the Unicode horizontal ellipsis (U+2026) in any field."""
      issues = []
      for field_name, value in [('quote', quote.quote), ('author', quote.author), ('publication', quote.publication)]:
          if value is None:
              continue
          if _UNICODE_ELLIPSIS in value:
              fixed = value.replace(_UNICODE_ELLIPSIS, '...')
              issues.append(
                  LintIssue(
                      line_number=quote.line_number,
                      check='unicode-ellipsis',
                      field=field_name,
                      message='Unicode ellipsis in {}'.format(field_name),
                      fixable=True,
                      fix_value=fixed,
                  )
              )
      return issues
  ```
- Extend the field-fix loop in `apply_fixes()` at [lint.py:128-144](jotquote/api/lint.py#L128-L144) with a new branch — modeled on the existing smart-dashes branch, but using `str.replace` since it's a one-character → three-character substitution (not a translate table):
  ```python
  ue = [i for i in line_fixes if i.check == 'unicode-ellipsis' and i.field == field_name]
  if ue:
      current = getattr(quote, field_name) or ''
      setattr(quote, field_name, current.replace(_UNICODE_ELLIPSIS, '...'))
      fix_count += 1
  ```

### 2. [jotquote/api/config.py](jotquote/api/config.py)

Add `'unicode-ellipsis'` to the `ALL_CHECKS` frozenset at [config.py:15-28](jotquote/api/config.py#L15-L28), grouped near `smart-quotes`/`smart-dashes`:
```python
'unicode-ellipsis',  # Flag (and fix) the Unicode horizontal ellipsis (U+2026)
```
This auto-enables the check via the default-population logic at [config.py:140-141](jotquote/api/config.py#L140-L141).

### 3. [tests/unit/api/test_lint.py](tests/unit/api/test_lint.py)

Use the existing `_make_quote` helper at [test_lint.py:25-29](tests/unit/api/test_lint.py#L25-L29) and follow the existing smart-quotes test pattern.

Import the new helper at [test_lint.py:8-22](tests/unit/api/test_lint.py#L8-L22):
```python
from jotquote.api.lint import (
    ...
    _check_unicode_ellipsis,
    ...
)
```

Add unit tests (TDD: write these first, watch them fail, then implement). Grouped in a new `# _check_unicode_ellipsis` section alongside the other check sections:

- `test_check_unicode_ellipsis_in_quote` — quote text contains `…`; assert one issue with `check='unicode-ellipsis'`, `field='quote'`, `fixable=True`, `fix_value` is the text with `…` replaced by `...`.
- `test_check_unicode_ellipsis_in_author` — same idea, author field.
- `test_check_unicode_ellipsis_in_publication` — same idea, publication field.
- `test_check_unicode_ellipsis_clean` — quote with no `…` returns `[]`.
- `test_check_unicode_ellipsis_multiple_occurrences` — `'Wait… really…'` — assert single issue per field (not per occurrence), `fix_value == 'Wait... really...'`.
- `test_apply_fixes_unicode_ellipsis` — feed a fixable `LintIssue` through `apply_fixes`, assert the quote text is rewritten and `count == 1` (modeled on `test_apply_fixes_smart_quotes` at [test_lint.py:439](tests/unit/api/test_lint.py#L439)).
- `test_check_ascii_does_not_flag_unicode_ellipsis` — quote containing only `…` and ASCII; assert `_check_ascii` returns `[]` (regression guard for the `_ASCII_SKIP` change).

### 4. [tests/integration/test_cli.py](tests/integration/test_cli.py)

Add one integration test next to the other `jotquote lint` integration tests (e.g. after `test_lint_duplicate_hash_integration`):

- `test_lint_unicode_ellipsis_fix_integration` — write a quote file containing a single quote with `…`; run `jotquote lint --select unicode-ellipsis --fix`; assert non-zero on the lint-then-fix flow's expected exit code (look at the existing fixable-check integration shape, if any, or use the pattern from `test_lint_duplicate_hash_integration`); re-read the file and assert `…` is gone and `...` is present.

### 5. [USER_DOCUMENTATION.md](USER_DOCUMENTATION.md)

Two locations list the check names explicitly — both must be updated:
- [USER_DOCUMENTATION.md:173](USER_DOCUMENTATION.md#L173) — "Available checks: …" list.
- [USER_DOCUMENTATION.md:254](USER_DOCUMENTATION.md#L254) — `enabled_checks` config row.

Append `unicode-ellipsis` to both lists. Optionally add a one-sentence description near the `duplicate-hash` blurb at [USER_DOCUMENTATION.md:175](USER_DOCUMENTATION.md#L175) explaining what the check does.

### 6. Project plans folder

Per [CLAUDE.md](CLAUDE.md) ("save a copy of the final plan to this folder"), at the end of implementation copy this plan to `plans/2026-13-05-add-unicode-ellipsis-lint-check.md`.

## Verification

1. **Unit tests (TDD)** — write the seven `test_lint.py` tests first, confirm they fail, then implement:
   ```bash
   uv run pytest tests/unit/api/test_lint.py -q
   ```
2. **Integration test:**
   ```bash
   uv run pytest tests/integration/test_cli.py::test_lint_unicode_ellipsis_fix_integration -q
   ```
3. **Full suite + lint:**
   ```bash
   uv run pytest -q
   uv run ruff check
   ```
4. **Built-in quote collection still lint-clean** (per CLAUDE.md):
   ```bash
   JOTQUOTE_CONFIG=jotquote/resources/settings.conf uv run jotquote lint
   ```
   Expect: `No issues found.` (the bundled `quotes.txt` should contain no `…`; if it does, fix the data file as part of this PR).
5. **Manual smoke test:**
   ```bash
   # create a temp quote file containing '…'
   echo 'Wait… really? | Author | | tag' > /tmp/q.txt
   JOTQUOTE_CONFIG=… uv run jotquote lint --select unicode-ellipsis
   # expect: line 1: [unicode-ellipsis] Unicode ellipsis in quote (fixable)
   JOTQUOTE_CONFIG=… uv run jotquote lint --select unicode-ellipsis --fix
   cat /tmp/q.txt
   # expect: 'Wait... really? | Author | | tag'
   ```

## Out of scope

- No new abstraction over the per-check hard-coded `apply_fixes` branches. The existing pattern is repeated 3× already; making the 4th instance identical is the right move. Refactoring `apply_fixes` to a registry-style dispatch is a separate concern.
- No handling of other Unicode-ellipsis-adjacent characters (e.g. U+22EF, U+22EE, U+2025). The user asked for U+2026 specifically.
