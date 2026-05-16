# Plan: Configurable favicon via `[web]` setting

## Context

The jotquote web apps (`jotquote webserver` and `jotquote webeditor`) previously served a hard-coded `favicon.ico` from [jotquote/web/static/favicon.ico](../jotquote/web/static/favicon.ico), referenced in [jotquote/web/templates/_head_common.html](../jotquote/web/templates/_head_common.html) and [jotquote/web/templates/unavailable.html](../jotquote/web/templates/unavailable.html). Users running their own jotquote instance had no way to brand it with their own favicon without forking the package.

This change adds a `favicon_file` property to the `[web]` section of `settings.conf`. When set, both web apps serve that file at `/favicon.ico`; when empty, they fall back to the bundled default. The setting mirrors the existing `quote_file` pattern: absolute paths are honored as-is, and relative paths resolve against the directory containing `settings.conf`.

An extension-point design (dotted module path + `get_favicon()` callable) was considered but rejected — a favicon is a static binary asset, and requiring users to author a Python module is over-engineering. A file-path setting matches the surface of `quote_file` and is the simplest thing that works.

## Implementation

### Setting

`favicon_file` lives in the `[web]` section. Supported file types: anything browsers accept for `<link rel="icon">` — `.ico`, `.svg`, `.png`. Flask's `send_file` sets `Content-Type` from the filename via `mimetypes`.

Following the existing template convention (only properties with non-empty defaults appear in the bundled `settings.conf`; extension-point and color-override keys are absent), `favicon_file` is **not** added to [jotquote/resources/settings.conf](../jotquote/resources/settings.conf). Users opt in by adding the line themselves.

### Behavior

- Both `viewer.py` and `editor.py` register a `GET /favicon.ico` route that returns either the user-configured file or the bundled default.
- If `favicon_file` is set but the file does not exist, `resolve_favicon_path` logs an error via `jotquote.web.helpers` and returns the bundled default so the page still loads.
- Relative paths are turned into absolute paths at config load time by [`_resolve_config_paths`](../jotquote/api/config.py); the helper only needs to handle empty/missing/exists.
- Templates use `url_for('favicon')` so the new route is canonical and works regardless of the URL prefix the WSGI server is mounted at.

## Files changed

### Code
- [jotquote/api/config.py](../jotquote/api/config.py) — added `'favicon_file'` to `_WEB_KEYS`, added `(SECTION_WEB, 'favicon_file')` to the `_resolve_config_paths` lookup list so relative paths resolve against the config dir.
- [jotquote/web/helpers.py](../jotquote/web/helpers.py) — added `resolve_favicon_path(config)` plus a module logger and `_BUNDLED_FAVICON` constant.
- [jotquote/web/viewer.py](../jotquote/web/viewer.py) — imported `send_file`, added `/favicon.ico` route delegating to `resolve_favicon_path`.
- [jotquote/web/editor.py](../jotquote/web/editor.py) — same.
- [jotquote/web/templates/_head_common.html](../jotquote/web/templates/_head_common.html) — `url_for('static', filename='favicon.ico')` → `url_for('favicon')`.
- [jotquote/web/templates/unavailable.html](../jotquote/web/templates/unavailable.html) — same.

### Tests
- [tests/unit/web/test_helpers.py](../tests/unit/web/test_helpers.py) — 6 cases covering `resolve_favicon_path`: unset, empty, whitespace-only, custom-exists, custom-missing-logs-and-falls-back, bundled-exists.
- [tests/unit/web/test_viewer.py](../tests/unit/web/test_viewer.py) — 4 cases: default favicon served, custom favicon served with correct Content-Type, missing custom falls back, `<link rel="icon">` points at `/favicon.ico`.
- [tests/unit/web/test_editor.py](../tests/unit/web/test_editor.py) — 2 cases: default served, custom served.
- [tests/integration/test_web_viewer.py](../tests/integration/test_web_viewer.py) — `test_custom_favicon`: spawns `jotquote webserver` with `favicon_file` pointing at the fixture SVG, downloads `/favicon.ico`, asserts bytes match. Also added `favicon_file` to `_WEB_NO_PREFIX` so the conf-builder routes it into `[web]`.
- [tests/fixtures/test_favicon.svg](../tests/fixtures/test_favicon.svg) — minimal SVG fixture.

### Documentation
- [USER_DOCUMENTATION.md](../USER_DOCUMENTATION.md) — added `favicon_file` row to the `[web]` properties table (placed between `expiration_seconds` and `header_provider_extension`).

## Verification (executed)

- `uv run pytest` → 398 passed, 1 skipped
- `uv run ruff check` → All checks passed
- `JOTQUOTE_CONFIG=jotquote/resources/settings.conf uv run jotquote lint` → No issues found
- Targeted favicon tests (unit + integration) pass independently.

Manual browser smoke test was not performed in this implementation pass — the integration test exercises end-to-end behavior (subprocess + HTTP + file-bytes comparison), which covers the same code paths.
