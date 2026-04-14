# Plan: Replace quotemap with pluggable quote resolver extension point

## Context

The quotemap feature maps dates to specific quotes via a flat file (`quotemap_file` in `[web]` config). It includes a `quotemap rebuild` CLI subcommand for generating these files. This plan replaces the entire quotemap subsystem with a pluggable Python extension point — a user-supplied module that the web server imports at runtime. The `quotemap rebuild` CLI subcommand is removed entirely, and all quotemap references are cleaned from the codebase.

---

## 1. New extension point in web_viewer.py

**Config property:** `quote_resolver` in `[web]` section of settings.conf  
**Value:** A dotted Python module path (e.g., `mypackage.my_resolver`)  
**Contract:** The module must define `resolve(date_str: str) -> str | None` where `date_str` is `YYYYMMDD` and the return is a 16-char MD5 hash or `None`.

### Module loading

- Use `importlib.import_module()` to load the module
- Cache at module level: `_resolver_fn = None`, `_resolver_loaded = False`
- Load on first request (inside `showpage()`), not at startup — avoids import errors blocking server start
- If import fails or module lacks `resolve`, log error and set `_resolver_fn = None` (no retries)
- Provide `_reset_resolver()` to clear cached state (for tests)

### Changes to showpage() (lines 151-193)

Replace the quotemap block with:

```python
# Try the configured quote resolver
resolver = _get_resolver(config)
lookup_date = date_path_param if date_path_param else now.strftime('%Y%m%d')
resolved_hash = None
if resolver:
    try:
        resolved_hash = resolver(lookup_date)
    except Exception:
        app.logger.exception('quote resolver error for date %s', lookup_date)

if resolved_hash:
    quote = api.get_first_match(quotes, hash_arg=resolved_hash)
    if quote:
        index = quotes.index(quote)
        if date_path_param is None:
            permalink = f'/{lookup_date}'
        if date_path_param:
            max_age = cap_seconds
    elif date_path_param:
        abort(404)
    else:
        # Hash not found, fall back to RNG
        index = api.get_random_choice(len(quotes))
        quote = quotes[index]
elif date_path_param:
    abort(404)
else:
    index = api.get_random_choice(len(quotes))
    quote = quotes[index]
```

### Helper function

```python
def _get_resolver(config):
    """Return the cached resolver function, or None."""
    global _resolver_fn, _resolver_loaded
    if _resolver_loaded:
        return _resolver_fn
    _resolver_loaded = True
    module_path = config[api.SECTION_WEB].get('quote_resolver', '')
    if not module_path:
        return None
    try:
        mod = importlib.import_module(module_path)
        _resolver_fn = getattr(mod, 'resolve')
    except (ImportError, AttributeError) as e:
        app.logger.error('failed to load quote resolver %r: %s', module_path, e)
    return _resolver_fn
```

Remove the `from jotquote import quotemap as quotemapmod` import. Add `import importlib`.

### Files modified
- [jotquote/web_viewer.py](jotquote/web_viewer.py)

---

## 2. Config changes in api.py

- Remove `'quotemap_file'` from `_WEB_KEYS` frozenset (line 418)
- Add `'quote_resolver'` to `_WEB_KEYS`
- Remove `(SECTION_WEB, 'quotemap_file')` from `_resolve_config_paths()` path_lookups (line 466) — `quote_resolver` is a module path, not a file path, so no resolution needed

### Files modified
- [jotquote/api.py](jotquote/api.py)

---

## 3. Remove quotemap CLI subcommand from cli.py

- Remove `from jotquote import quotemap as quotemapmod` import (line 13)
- Remove `'quotemap'` from the `ctx.invoked_subcommand not in (...)` tuple (line 78) — it becomes `('webserver', 'webeditor')`
- Update the comment on line 75-77 to remove quotemap mention
- Delete the `quotemap` group and `rebuild` command (lines 237-257)

### Files modified
- [jotquote/cli.py](jotquote/cli.py)

---

## 4. Delete quotemap module and test files

### Files deleted
- [jotquote/quotemap.py](jotquote/quotemap.py) — entire module
- [tests/unit/test_quotemap_read.py](tests/unit/test_quotemap_read.py) — entire file
- [tests/unit/test_quotemap_rebuild.py](tests/unit/test_quotemap_rebuild.py) — entire file

---

## 5. Update existing tests

### tests/unit/test_web_viewer.py

Rewrite the three quotemap tests to use the resolver pattern. Use `monkeypatch` to inject `_resolver_fn` and `_resolver_loaded` directly on the `web_viewer` module, avoiding real imports.

- `test_date_route_with_quotemap` (line 198) → `test_date_route_with_resolver` — monkeypatch a resolver that returns hash `25382c2519fb23bd`, verify `/20260319` returns Ben Franklin quote
- `test_date_route_without_quotemap` (line 210) → `test_date_route_without_resolver` — no resolver configured, `/<date>` returns 404
- `test_root_with_quotemap_today` (line 237) → `test_root_with_resolver_today` — resolver returns hash for today, verify permalink shown
- `test_root_without_quotemap` (line 251) → `test_root_without_resolver` — no resolver, RNG used, no permalink

### tests/unit/test_api.py

- Line 956: Remove `quotemap_file = /some/quotemap.txt` from legacy config test string; replace with `quote_resolver = mypackage.resolver`
- Lines 974-975: Change assertion from path-resolution of `quotemap_file` to verifying `quote_resolver` value is preserved as-is (not path-resolved)
- Line 1029: Update legacy migration test — replace `quotemap_file` with `quote_resolver`

### tests/integration/test_cli.py

- Line 44: Change `_WEB_NO_PREFIX = {'quotemap_file'}` to `_WEB_NO_PREFIX = {'quote_resolver'}`
- Delete `_rebuild()` helper (lines 174-189)
- Delete all `test_quotemap_*` functions (lines 192-257)

### tests/integration/test_web_viewer.py

- Line 49: Change `_WEB_NO_PREFIX = {'quotemap_file'}` to `_WEB_NO_PREFIX = {'quote_resolver'}`
- Rewrite `test_quotemap_date_route` (line 277) and `test_quotemap_root_permalink` (line 307) to use a test resolver module
- Create `tests/fixtures/test_resolver.py` — a tiny module that reads date→hash mappings from `TEST_RESOLVER_MAP` env var (format: `YYYYMMDD=hash,YYYYMMDD=hash`)

### tests/integration/test_web_editor.py

- Line 37: Change `_WEB_NO_PREFIX = {'quotemap_file'}` to `_WEB_NO_PREFIX = {'quote_resolver'}`

---

## 6. New tests for the extension point

Add to `tests/unit/test_web_viewer.py`:

- `test_resolver_returns_none_root` — resolver returns `None`, seeded RNG used
- `test_resolver_returns_none_date_route` — resolver returns `None`, 404
- `test_resolver_exception_root` — resolver raises exception, falls back to RNG
- `test_resolver_exception_date_route` — resolver raises exception, 404
- `test_resolver_hash_not_found_root` — resolver returns unknown hash, falls back to RNG
- `test_resolver_hash_not_found_date_route` — resolver returns unknown hash, 404

Add integration tests in `tests/integration/test_web_viewer.py`:

- `test_resolver_date_route` — configure test resolver with env var mapping, verify `/<date>` serves correct quote
- `test_resolver_root_permalink` — configure test resolver with today's date, verify permalink on `/`

---

## 7. Update documentation

### DOCUMENTATION.md
- Remove `### quotemap rebuild` CLI section (lines 177-197)
- Remove entire `## Quotemap` section (lines 258-363)
- Add new `## Quote Resolver` section documenting the extension point: config property, function contract, fallback behavior, permalink behavior
- Replace `quotemap_file` row in config properties table (line 448) with `quote_resolver`
- Update web server description (lines 237-254) to reference resolver instead of quotemap

### README.md
- Line 104: Replace quotemap bullet with quote resolver mention

### CLAUDE.md
- Line 60: Remove `quotemap` from CLI subcommand list
- Lines 93, 97: Remove references to quotemap test files
- Add mention of quote resolver extension point in architecture section

---

## Verification

```bash
# Run all tests
uv run pytest

# Run linter against built-in quotes
JOTQUOTE_CONFIG=jotquote/templates/settings.conf uv run jotquote lint

# Run ruff
uv run ruff check jotquote/

# Verify quotemap is fully removed
grep -ri quotemap jotquote/ tests/ README.md DOCUMENTATION.md CLAUDE.md

# Start server and test manually
uv run jotquote webserver
```
