# Plan: Startup log for configured timezone and daily-refresh notice

## Context

The web viewer (`jotquote.web.viewer`) already logs three INFO lines at module-import time via `_log_startup_info()` (settings path, quote file path, package version). Operators have no quick way, however, to confirm two operationally important things from the logs:

1. Whether the optional `timezone` property in `[general]` is being picked up, and what the current local time looks like under that zone.
2. That in `mode = daily`, the page is engineered to refresh exactly at local midnight (the `_compute_expiration()` cap).

This plan extends `_log_startup_info()` with up to three additional INFO lines so the operator can verify both at a glance, without making any other behavioral changes.

## Approach

Extend the existing `_log_startup_info()` in [jotquote/web/viewer.py](../jotquote/web/viewer.py). All new logging uses the existing `_logger`, which already inherits `TimestampFormatter` via `web_helpers.configure_logging()`.

Because the new logic calls `_get_local_now()` (which is defined later in the module), the module-level call `_log_startup_info()` is moved to the bottom of the file so it executes after all helpers are bound.

### New log lines

After the existing three lines, append (subject to the conditions below):

```
configured timezone: <tz_name>
current local time: <YYYY-MM-DD HH:MM:SS AM/PM TZABBR>
quote of the day will refresh at 12:00 AM local time
```

### Branching rules

- **Timezone unset** (`config[general].timezone` is empty/absent):
  - Line 1 → `configured timezone: <not set; using system local time>`
  - Line 2 → current naive system local time (the `_get_local_now(config)` `None` branch already returns this).
- **Timezone set to an invalid IANA name**:
  - `_get_local_now()` raises `ConfigError`. Wrap the call in `try/except ConfigError` and log a single WARNING line: `invalid timezone in [general] section: <name>; skipping timezone log lines`. Do not raise — the rest of startup (and existing tests) must continue to succeed. (Per-request handlers will surface the error to users as today.)
- **`mode = random`**:
  - Skip the "quote of the day will refresh at 12:00 AM local time" line entirely (would be inaccurate). Still log timezone + current local time.
- **`mode = daily` (default)**:
  - Log all three new lines.

### Time formatting

Use a single `strftime` format that round-trips both aware and naive datetimes:
`'%Y-%m-%d %I:%M:%S %p %Z'` (with a trailing `.strip()` so naive datetimes don't have a dangling space). For aware datetimes `%Z` yields the abbreviation (e.g. `CDT`); for naive ones it yields `''`.

## Files modified

### [jotquote/web/viewer.py](../jotquote/web/viewer.py)

Extended `_log_startup_info()`:

1. Read `mode = config[api.SECTION_WEB].get('mode', 'daily')`.
2. Call existing helper `_get_local_now(config)` inside a `try/except ConfigError` block.
3. On success: log `configured timezone: ...` (or the "not set" variant when `tz_name is None`) and `current local time: ...`.
4. On `ConfigError`: log the warning line and return.
5. If `mode != 'random'`: log the refresh line.

Moved the module-level `_log_startup_info()` call to the bottom of the file (after `_get_local_now` is defined).

## Tests

### Unit tests — added to [tests/unit/web/test_viewer.py](../tests/unit/web/test_viewer.py)

Uses `caplog.at_level(..., logger='jotquote.web.viewer')` plus the existing `config` fixture (which mocks `api.get_config()`):

1. `test_startup_logs_configured_timezone` — `timezone = America/Chicago`, `mode = daily`. All three new lines appear.
2. `test_startup_logs_unset_timezone_falls_back` — no `timezone` key. `<not set; using system local time>` substring is present and `current local time:` line is logged.
3. `test_startup_skips_midnight_line_in_random_mode` — `mode = random`. Timezone + local time lines present, refresh line absent.
4. `test_startup_logs_warning_on_invalid_timezone` — `timezone = Not/A_Zone`. WARNING is logged, no `ConfigError` propagates, midnight line absent.

### Integration test — extended [tests/integration/test_web_viewer.py](../tests/integration/test_web_viewer.py)

Augmented `_run_startup_log_test` with three additional `wait_for_log_line` assertions for `configured timezone:`, `current local time:`, and `quote of the day will refresh at 12:00 AM local time`. Both existing `test_webserver_startup_logs` and `test_waitress_serve_startup_logs` now exercise the new lines.

## Verification

```powershell
uv run pytest tests/unit/web/test_viewer.py -k startup     # 4 passed
uv run pytest tests/integration/test_web_viewer.py::test_webserver_startup_logs
uv run pytest tests/integration/test_web_viewer.py::test_waitress_serve_startup_logs
uv run pytest                                              # 414 passed, 1 skipped
uv run ruff check                                          # All checks passed!
$env:JOTQUOTE_CONFIG = "jotquote/resources/settings.conf"
uv run jotquote lint                                       # No issues found.
```

Manual smoke (bundled config, `timezone` commented out):

```
INFO path to settings.conf file: jotquote/resources/settings.conf
INFO path to the quote file: .../jotquote/resources/quotes.txt
INFO jotquote package version: 0.9.5.dev0
INFO configured timezone: <not set; using system local time>
INFO current local time: 2026-05-19 06:07:01 PM
INFO quote of the day will refresh at 12:00 AM local time
INFO Serving on http://127.0.0.1:5544
```

## Out of scope

- No changes to `_compute_expiration()` or any request-path code.
- No new config keys.
- No changes to `TimestampFormatter` or `configure_logging()`.
- No re-logging on each request — these lines fire exactly once at module import, mirroring the existing three lines.
