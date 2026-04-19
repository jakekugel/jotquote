# Documentation Reorganization Plan

## Context

The project currently has three top-level documentation files with overlapping, non-obvious names: [README.md](../README.md) (overview), `DOCUMENTATION.md` (user/CLI reference), and `DEVELOPMENT.md` (contributor setup/release guide). The names don't clearly signal audience. Additionally, the `jotquote.api` facade is now a stable surface that external consumers (e.g., quote resolvers, header providers, integrations) can program against, but there was previously **no reference documentation for it** — readers had to grep source to learn the signatures.

This plan:
1. Renames the two existing docs to audience-specific names.
2. Adds a new `API_REFERENCE.md` covering the public `jotquote.api` surface with signatures, descriptions, and code examples.
3. Updates the two live cross-reference sites (README.md, CLAUDE.md). Historical plan files under [plans/](../plans/) are intentionally left untouched — they are records of past work.

## Scope & decisions (confirmed with user)

- **API_REFERENCE.md covers**: the 18 module-level functions + the `Quote` class (with its methods) + the `LintIssue` dataclass. Module-level constants (`APP_NAME`, `CONFIG_FILE`, `ALL_CHECKS`, `SECTION_*`) are **not** in scope.
- **Plan files under [plans/](../plans/) are not updated** — they are historical.

## Changes

### 1. File renames

Use `git mv` to preserve rename history:

- `DEVELOPMENT.md` -> `DEVELOPER_DOCUMENTATION.md`
- `DOCUMENTATION.md` -> `USER_DOCUMENTATION.md`

No content changes to either file during the rename.

### 2. Create API_REFERENCE.md

New file at repo root. Structure mirrors the submodule layout documented in [CLAUDE.md](../CLAUDE.md) so readers can map docs back to source:

```
# jotquote API Reference

Brief intro: import via `from jotquote import api`; all symbols below are
re-exported from jotquote.api.

## Classes
  ### Quote        (from jotquote/api/quote.py)
    - Constructor signature + one-paragraph description
    - Attributes table (quote, author, publication, tags, line_number)
    - Methods: has_tag, has_tags, has_keyword, set_tags, get_hash,
      get_num_stars, get_line_number
    - Each method: signature + 1-2 sentence description + code example
  ### LintIssue    (from jotquote/api/lint.py)
    - Dataclass fields + description + example of iterating lint_quotes output

## Quote parsing        (from jotquote/api/quote.py)
  - parse_quote, parse_tags

## Configuration        (from jotquote/api/config.py)
  - get_config, get_filename

## Quote storage        (from jotquote/api/store.py)
  - read_quotes, read_quotes_with_hash, read_tags, parse_quotes,
    add_quote, add_quotes, set_quote, settags, get_sha256,
    write_quotes, format_quote

## Quote selection      (from jotquote/api/selection.py)
  - get_first_match, get_random_choice

## Linting              (from jotquote/api/lint.py)
  - lint_quotes, apply_fixes
```

**Per-function format** (consistent across all 18 functions + class methods):

```markdown
### `function_name`

```python
function_name(arg1: Type, arg2: Type = default) -> ReturnType
```

One- to two-sentence description of what it does and when to use it.
Note any important side effects (file I/O, raises ClickException, etc.).

**Example:**
```python
from jotquote import api

quotes = api.read_quotes('/path/to/quotes.txt')
print(f'Loaded {len(quotes)} quotes')
```
```

Examples should be runnable and use realistic arguments. Where a function
pairs with another (e.g., `read_quotes_with_hash` + `write_quotes` for
concurrency-safe edits), the example demonstrates the pairing.

**Import style in examples — important**: examples must import via the
`jotquote.api` facade and must **never** import directly from submodules
(`jotquote.api.store`, `jotquote.api.quote`, etc.). The facade re-exports
every public symbol, so the submodule paths are implementation detail that
external consumers should not depend on. Use one of these two forms
consistently across all examples:

```python
from jotquote import api
quotes = api.read_quotes('/path/to/quotes.txt')
```

or equivalently:

```python
import jotquote.api
quotes = jotquote.api.read_quotes('/path/to/quotes.txt')
```

Pick one form (recommend `from jotquote import api`) and use it
consistently throughout API_REFERENCE.md.

**Style consistency with existing docs:**
- Match the markdown code-block style used in the renamed `USER_DOCUMENTATION.md`.
- Use single backticks for inline symbols, triple-backtick `python` blocks for signatures and examples.
- Keep a short TOC-like section header list at the top.

**Source of truth for signatures/docstrings**: pull signatures and docstrings directly from the submodule files listed below — do not paraphrase. (These paths are for the doc author's reference only; they must not appear in the documented import examples.)
- [jotquote/api/quote.py](../jotquote/api/quote.py)
- [jotquote/api/config.py](../jotquote/api/config.py)
- [jotquote/api/store.py](../jotquote/api/store.py)
- [jotquote/api/selection.py](../jotquote/api/selection.py)
- [jotquote/api/lint.py](../jotquote/api/lint.py)

### 3. Update cross-references

**[README.md](../README.md)** — 4 existing link updates + 1 new link:
- `DOCUMENTATION.md` web-server section link -> `USER_DOCUMENTATION.md`
- `DOCUMENTATION.md` settings.conf link -> `USER_DOCUMENTATION.md`
- `DOCUMENTATION.md` full reference link -> `USER_DOCUMENTATION.md`
- `DEVELOPMENT.md` link -> `DEVELOPER_DOCUMENTATION.md`
- **Add** a link to the new `API_REFERENCE.md` near the existing documentation-link area so API consumers can find it.

**[CLAUDE.md](../CLAUDE.md)** — 2 references:
- `DOCUMENTATION.md#quote-resolver` -> `USER_DOCUMENTATION.md#quote-resolver`
- `DOCUMENTATION.md` mentions in the settings.conf paragraph (2 on the same line) -> `USER_DOCUMENTATION.md`

No other live files reference these names (confirmed via grep).

## Files modified

| File | Change |
|---|---|
| `DEVELOPMENT.md` | Renamed -> `DEVELOPER_DOCUMENTATION.md` |
| `DOCUMENTATION.md` | Renamed -> `USER_DOCUMENTATION.md` |
| `API_REFERENCE.md` | **New** |
| [README.md](../README.md) | Update 4 links, add 1 link |
| [CLAUDE.md](../CLAUDE.md) | Update 2 references |

## Verification

1. **Rename sanity**: `git status` shows the two files as renames (not delete+add). `git log --follow DEVELOPER_DOCUMENTATION.md` shows full prior history.
2. **No broken links remain in live docs**: from the repo root, grep for `DEVELOPMENT.md` and `DOCUMENTATION.md` with a negative lookbehind for `_` (to exclude `USER_DOCUMENTATION.md` / `DEVELOPER_DOCUMENTATION.md` matches) and confirm zero hits in live docs (plans/ still references the old names — intentional).
3. **API_REFERENCE.md coverage**: cross-check the headings against the re-export list in [jotquote/api/__init__.py](../jotquote/api/__init__.py) — every re-exported function, `Quote`, and `LintIssue` must appear. (Constants are intentionally excluded per user decision.)
4. **Examples use the facade**: grep the new file for `from jotquote.api.` or `import jotquote.api.` — there must be **zero** hits.
5. **Lint still clean**: `uv run jotquote lint` on the built-in collection still passes (no code changes, but per [CLAUDE.md](../CLAUDE.md) this is the project convention after any repo change).
6. **README links resolve**: open README.md in the VS Code preview and click each updated link.

## Out of scope

- No content changes to the renamed files beyond the rename itself. If content updates are desired (e.g., mentioning API_REFERENCE.md from the user docs), that's a follow-up.
- No updates to plan files under [plans/](../plans/).
- No new unit/integration tests — this is documentation-only. (The [CLAUDE.md](../CLAUDE.md) testing requirement applies to code changes.)
