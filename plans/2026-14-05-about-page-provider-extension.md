# Plan: About Page Provider Extension Point

## Context

The jotquote web viewer currently supports a static about page via the `about` config property (renders `about.html` with plain text). Users have no way to serve a dynamic or richly formatted about page. This plan adds an `about_page_provider_extension` extension point following the same lazy-load module pattern used by `quote_resolver_extension` and `header_provider_extension`.

The About button on the viewer is currently conditional on `about_text` being non-empty. After this change it will be conditional on a new `show_about` boolean that's true when either the extension is configured or `about_text` is non-empty — preserving backward compatibility.

## Extension Contract

The provider module must define:

```python
def get_about_page(page_title: str, colors: dict) -> str:
    """Return full HTML for the /about page."""
```

- `page_title` — the configured `page_title` value (for `<title>` consistency)
- `colors` — dict with keys `light_fg`, `light_bg`, `dark_fg`, `dark_bg` (for theme CSS consistency)
- Returns a full HTML string; returned directly to the browser, not processed by Jinja2

Recommended parameters rationale: `page_title` keeps the browser tab consistent with the rest of the site. `colors` allows the extension to match the viewer's light/dark theme without re-reading config.

## Behavior Rules

- Extension configured → `/about` calls provider; `about` text config is ignored
- Extension not configured, `about` text set → existing static behavior (backward compat)
- Neither configured → 404; About button hidden
- Provider raises exception → log it, return 500 (unlike header provider which silently omits; an about-page failure is user-visible and should signal the misconfiguration)
- Provider module missing or lacks `get_about_page` → log error, disable extension for lifetime of process, fall back to `about` text or 404

## Files to Modify

| File | Change |
|------|--------|
| `jotquote/api/config.py` | Add `'about_page_provider_extension'` to `_WEB_KEYS` frozenset |
| `jotquote/web/viewer.py` | New globals, `_get_about_provider()`, `_reset_about_provider()`, update `aboutpage()`, update `showpage()` |
| `jotquote/web/templates/viewer.html` | Line 224: `{% if about_text %}` → `{% if show_about %}` |
| `jotquote/web/templates/unavailable.html` | Replace `about_text=about_text` with `show_about=show_about` |
| `USER_DOCUMENTATION.md` | New row in `[web]` table + new "About Page Provider" section |
| `tests/unit/web/test_viewer.py` | New test class for the extension |
| `tests/integration/test_web_viewer.py` | Add to `_WEB_NO_PREFIX`; two new tests |
| `tests/fixtures/test_about_provider.py` | New fixture module |

## Step-by-Step Implementation (TDD Order)

### 1. New test fixture: `tests/fixtures/test_about_provider.py`

```python
_SENTINEL = '<h1>Test About Page</h1>'

def get_about_page(page_title, colors):
    """Returns minimal HTML. page_title is embedded in <title> for assertions."""
    return (
        '<!DOCTYPE html><html><head><title>{}</title></head>'
        '<body>{}</body></html>'.format(page_title, _SENTINEL)
    )
```

### 2. Write failing unit tests in `tests/unit/web/test_viewer.py`

Add a new test section after the existing about-page tests. Use monkeypatch on `web._about_provider_fn` and `web._about_provider_loaded` (same pattern as `_header_fn`/`_resolver_fn`):

- `test_about_provider_returns_html` — monkeypatch provider returning `'<html>custom</html>'`; GET `/about`; assert 200 + body contains sentinel
- `test_about_provider_receives_page_title_and_colors` — capture args in the patched fn; assert `page_title` forwarded and `colors` dict has the four expected keys
- `test_about_provider_takes_priority_over_about_text` — set `config[api.SECTION_WEB]['about'] = 'config text'` AND patch provider; assert extension HTML returned, config text absent
- `test_about_provider_exception_returns_500` — patch provider that raises `RuntimeError`; assert GET `/about` returns 500
- `test_no_provider_falls_back_to_about_text` — patch `_about_provider_fn = None, _about_provider_loaded = True`; set `about = 'Fallback'`; assert 200 + `b'Fallback'` in response
- `test_no_provider_no_about_text_returns_404` — patch `_about_provider_fn = None, _about_provider_loaded = True`; no `about` key; assert 404
- `test_about_button_shown_with_provider` — patch provider, no `about` text; GET `/`; assert `b'href="/about"'` in response
- `test_about_button_shown_with_about_text` — no provider; set `about = 'text'`; GET `/`; assert `b'href="/about"'` in response (regression guard)
- `test_about_button_hidden_with_neither` — no provider, no `about` text; GET `/`; assert `b'href="/about"'` NOT in response
- `test_get_about_provider_caches_result` — call `_reset_about_provider()`; set no extension in config; call `_get_about_provider(config)` twice; assert loaded and returns None both times
- `test_get_about_provider_import_error` — call `_reset_about_provider()`; set `about_page_provider_extension = 'nonexistent.module'`; call `_get_about_provider(config)` in app context; assert returns None, `_about_provider_loaded` is True

### 3. Write failing integration tests in `tests/integration/test_web_viewer.py`

- Add `'about_page_provider_extension'` to `_WEB_NO_PREFIX` set
- `test_about_page_provider_extension` — launch server with `about_page_provider_extension='tests.fixtures.test_about_provider'`; GET `/about`; assert 200 + sentinel in body; GET `/`; assert about button present
- `test_about_page_provider_passes_page_title` — launch server with extension + `web_page_title='Integration Title'`; GET `/about`; assert `<title>Integration Title</title>` in body

### 4. Add `about_page_provider_extension` to `_WEB_KEYS` in `jotquote/api/config.py`

Add alongside `'header_provider_extension'` and `'quote_resolver_extension'` in the frozenset.

### 5. Implement in `jotquote/web/viewer.py`

**New globals** (after line 57):
```python
_about_provider_fn = None
_about_provider_loaded = False
```

**New `_get_about_provider(config)`** (after `_reset_header_provider`, around line 278):
- Same lazy-load pattern as `_get_header_provider`
- Config key: `'about_page_provider_extension'`
- Function name to load: `'get_about_page'`
- Log error on `ImportError`/`AttributeError`

**New `_reset_about_provider()`** — same pattern as `_reset_resolver`, for tests only

**Update `aboutpage()` route** (lines 86–95):
```python
@app.route('/about')
def aboutpage():
    config = api.get_config()
    page_title = config[api.SECTION_WEB].get('page_title', 'jotquote')
    colors = web_helpers.get_color_config(config)

    about_provider = _get_about_provider(config)
    if about_provider:
        try:
            return about_provider(page_title, colors)
        except Exception:
            app.logger.exception('about page provider error')
            abort(500)

    about_text = config[api.SECTION_WEB].get('about', '')
    if not about_text:
        abort(404)
    return render_template('about.html', about_text=about_text, page_title=page_title, **colors)
```

**Update `showpage()`** (around lines 116–200):
- After computing `about_text`, add: `show_about = bool(about_text) or (_get_about_provider(config) is not None)`
- In both `render_template` calls, replace `about_text=about_text` with `show_about=show_about`

### 6. Update `jotquote/web/templates/viewer.html`

Line 224: `{% if about_text %}` → `{% if show_about %}`

### 7. Update `jotquote/web/templates/unavailable.html`

Replace `about_text=about_text` with `show_about=show_about` in the `render_template` call in `showpage()` (viewer.py line 141).

### 8. Update `USER_DOCUMENTATION.md`

- Add row to `[web]` table: `about_page_provider_extension` | _(empty)_ | Dotted Python module path for a custom about page (see About Page Provider)
- Add new `## About Page Provider` section (after `## Header Provider`) documenting: the function signature, parameter semantics, config snippet, precedence/fallback rules, error handling, and caching behavior

## Verification

```bash
# Run all tests
uv run pytest

# Verify linter clean
export JOTQUOTE_CONFIG=jotquote/resources/settings.conf
uv run jotquote lint

# Run only the new unit tests
uv run pytest tests/unit/web/test_viewer.py -k "about_provider"

# Run only the new integration tests
uv run pytest tests/integration/test_web_viewer.py -k "about_page_provider"
```
