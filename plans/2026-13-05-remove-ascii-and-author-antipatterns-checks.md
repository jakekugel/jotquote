# Remove `ascii` and `author-antipatterns` lint checks

## Context

Two lint checks are no longer wanted:

1. **`author-antipatterns`** — currently catches three things: authors matching an unknown/anonymous regex (`unknown`, `anonymous`, `anon`, `n/a`, `none`, `?`), authors containing all-caps words (3+ letters), and authors matching a user-configurable regex from settings.conf. The check is being removed in full per user confirmation (not just the anonymous sub-rule).
2. **`ascii`** — flags non-ASCII characters anywhere in quote/author/publication that aren't already owned by `smart-quotes`/`smart-dashes`/`unicode-ellipsis`. The more specific typographic checks remain and continue to catch their respective characters; this check is being removed in full per user confirmation.

Outcome after this change: `jotquote lint` and `ALL_CHECKS` no longer include either name. The `author_antipattern_regex` config property is removed from the template `settings.conf`; legacy migration of `lint_author_antipattern_regex` falls back to the generic `lint_`-prefix branch (silent no-op) so old user configs don't crash. Built-in `quotes.txt` already lint-clean — remains so.

## Code changes

### 1. [jotquote/api/lint.py](jotquote/api/lint.py)

- Delete module-level constants `_ANON_RE` ([lint.py:37](jotquote/api/lint.py#L37)) and `_ALLCAPS_WORD_RE` ([lint.py:38](jotquote/api/lint.py#L38)).
- Delete `_ASCII_SKIP` ([lint.py:163](jotquote/api/lint.py#L163)).
- Delete `_check_ascii()` ([lint.py:166-180](jotquote/api/lint.py#L166-L180)).
- Delete `_check_author_antipatterns()` ([lint.py:318-358](jotquote/api/lint.py#L318-L358)).
- Remove the two dispatch branches in `lint_quotes()`:
  - `if 'ascii' in checks:` ([lint.py:83-84](jotquote/api/lint.py#L83-L84))
  - `if 'author-antipatterns' in checks:` ([lint.py:97-98](jotquote/api/lint.py#L97-L98))
- The `import re` at [lint.py:5](jotquote/api/lint.py#L5) stays — still used by `_check_double_spaces` and `apply_fixes`.

### 2. [jotquote/api/config.py](jotquote/api/config.py)

- Remove `'ascii'` ([config.py:17](jotquote/api/config.py#L17)) and `'author-antipatterns'` ([config.py:25](jotquote/api/config.py#L25)) from `ALL_CHECKS`.
- Remove `'lint_author_antipattern_regex'` from `_LINT_KEYS` ([config.py:48](jotquote/api/config.py#L48)). The generic `elif key.startswith('lint_'):` branch at [config.py:184-185](jotquote/api/config.py#L184-L185) still migrates the legacy key into `[lint]/author_antipattern_regex`; it's a silent no-op afterwards since no code reads it.

### 3. [jotquote/resources/settings.conf](jotquote/resources/settings.conf)

Remove the `author_antipattern_regex =` line ([settings.conf:8](jotquote/resources/settings.conf#L8)). The `[lint]` section keeps `lint_on_add = false`.

## Test changes

### 4. [tests/unit/api/test_lint.py](tests/unit/api/test_lint.py)

- Drop `_check_ascii` and `_check_author_antipatterns` from the imports ([test_lint.py:10-11](tests/unit/api/test_lint.py#L10-L11)).
- Drop the `author_antipattern_regex` parameter and assignment from the `_make_config` helper ([test_lint.py:33,40](tests/unit/api/test_lint.py#L33)).
- Delete the entire `_check_ascii` section ([test_lint.py:47-84](tests/unit/api/test_lint.py#L47-L84)) — 5 tests including `test_check_ascii_does_not_flag_unicode_ellipsis` (the unicode-ellipsis check now needs no ascii-skip companion).
- Delete the entire `_check_author_antipatterns` section ([test_lint.py:291-343](tests/unit/api/test_lint.py#L291-L343)) — 7 tests.

### 5. [tests/unit/cli/test_cli.py](tests/unit/cli/test_cli.py)

Tests use `'ascii'` as a representative check name in their CliRunner invocations. Substitute another harmless check (`smart-quotes` works since fixture quotes have no smart quotes):

- [test_cli.py:678](tests/unit/cli/test_cli.py#L678) (`test_lint_clean_file`) — `'ascii'` → `'smart-quotes'`. Update the inline comment about "avoid spurious tag failures" to refer to `smart-quotes`.
- [test_cli.py:702](tests/unit/cli/test_cli.py#L702) (`test_lint_select_and_ignore_mutually_exclusive`) — `'ascii'` → `'smart-quotes'`.
- [test_cli.py:716](tests/unit/cli/test_cli.py#L716) (`test_lint_ignore`) — remove `ascii,` and `author-antipatterns,` from the `--ignore` comma-list so it reads `'no-tags,smart-quotes,no-author'`.
- [test_cli.py:849](tests/unit/cli/test_cli.py#L849) (`test_add_lint_respects_enabled_checks`) — `enabled_checks = 'ascii'` → `'smart-quotes'`.

### 6. [tests/unit/api/test_config.py](tests/unit/api/test_config.py)

`test_migrate_legacy_section_prefix_stripping` exercises the legacy `[jotquote]` → `[lint]` migration on a representative set of keys including `lint_author_antipattern_regex`:

- Remove the input line ([test_config.py:162](tests/unit/api/test_config.py#L162)).
- Remove the matching assertion ([test_config.py:178](tests/unit/api/test_config.py#L178)).
- Other migrated keys in this test still exercise the same code paths.

### 7. [tests/conftest.py](tests/conftest.py) and [tests/unit/conftest.py](tests/unit/conftest.py)

Both fixtures populate the test config identically:
- `enabled_checks` value: drop `ascii, ` and `, author-antipatterns` so it becomes `'smart-quotes, no-tags, no-author'` ([conftest.py:22](tests/conftest.py#L22), [unit/conftest.py:22](tests/unit/conftest.py#L22)).
- Delete `cfg[api.SECTION_LINT]['author_antipattern_regex'] = ''` ([conftest.py:23](tests/conftest.py#L23), [unit/conftest.py:23](tests/unit/conftest.py#L23)).

No new tests are required — removal is exhaustively covered by deleting the existing tests above. Negative-coverage (asserting the names are gone from `ALL_CHECKS`) is unnecessary; `test_lint_unknown_check` ([test_cli.py:724](tests/unit/cli/test_cli.py#L724)) already exercises the unknown-check rejection path.

## Documentation changes

### 8. [USER_DOCUMENTATION.md](USER_DOCUMENTATION.md)

- [USER_DOCUMENTATION.md:173](USER_DOCUMENTATION.md#L173) "Available checks: …" — remove `\`ascii\`, ` and `, \`author-antipatterns\``.
- [USER_DOCUMENTATION.md:256](USER_DOCUMENTATION.md#L256) `enabled_checks` row — same removals from the "Valid values" list.
- [USER_DOCUMENTATION.md:258](USER_DOCUMENTATION.md#L258) — delete the entire `author_antipattern_regex` row from the `[lint]` properties table.

### 9. [API_REFERENCE.md](API_REFERENCE.md)

[API_REFERENCE.md:773-775](API_REFERENCE.md#L773-L775) lists checks in prose — remove `\`ascii\`,` and `\`author-antipatterns\`,` and re-flow the sentence.

## Verification

1. **Full test suite:**
   ```bash
   uv run pytest -q
   ```
   Expect: all tests pass (~12 tests removed by deletion, all others green).

2. **Linter:**
   ```bash
   uv run ruff check
   ```
   Expect: `All checks passed!` — also catches any stray import (e.g. accidentally leaving an `import re` only used by the removed code).

3. **Built-in collection still lints clean** (per [CLAUDE.md](CLAUDE.md)):
   ```bash
   JOTQUOTE_CONFIG=jotquote/resources/settings.conf uv run jotquote lint
   ```
   Expect: `No issues found.`

4. **Hand-check that removed names are rejected:**
   ```bash
   JOTQUOTE_CONFIG=jotquote/resources/settings.conf uv run jotquote lint --select ascii
   # expect: error, "Unknown check: ascii"
   JOTQUOTE_CONFIG=jotquote/resources/settings.conf uv run jotquote lint --select author-antipatterns
   # expect: error, "Unknown check: author-antipatterns"
   ```

5. **Save plan copy** per [CLAUDE.md](CLAUDE.md) convention: copy this file to `plans/2026-13-05-remove-ascii-and-author-antipatterns-checks.md` at end of execution.

## Out of scope

- No grep of historic `plans/*.md` files — those are point-in-time records and don't need rewriting.
- No deprecation period or warning shim. Per user direction, the checks are removed outright; any user config still listing `ascii`/`author-antipatterns` in `enabled_checks` will pass through `_get_active_checks` and be silently ignored by `lint_quotes` (the dispatch branches are gone). If hard failure on unknown names in `enabled_checks` is desired, that's a separate change.
