# Plan: Web Server Startup Logging

## Context

When `jotquote` is run as a web server (either via `jotquote webserver` or directly via `waitress-serve jotquote.web_viewer:app`), there is currently no indication in the logs of which config file, quote file, or package version is in use. Adding three INFO log messages at startup makes it easier to verify correct configuration at a glance.

## Approach

Log the three messages at **module import time** in `web_viewer.py`, immediately after `configure_logging()`. This is the correct trigger point because:

- Both launch paths import the module before serving begins.
- `configure_logging()` is already called at module level for the same reason — "so the format applies regardless of whether the app is launched via 'jotquote webserver' or a WSGI server directly."
- This avoids duplicating the logic across `run_server()` and a separate module-level hook.

## Files to Modify

### `jotquote/web_viewer.py`

After the existing module-level setup block (lines 16–25), add:

1. A module-level named logger using `logging.getLogger(__name__)` (logger name will be `jotquote.web_viewer`).
2. A private helper `_log_startup_info()` that:
   - Computes the config file path using `os.environ.get('JOTQUOTE_CONFIG') or api.CONFIG_FILE` (same logic as `api.get_config()` internally).
   - Calls `api.get_config()` to get the resolved quote file path.
   - Imports `jotquote.__version__` for the version string.
   - Logs three INFO messages.
3. A call to `_log_startup_info()` right after `configure_logging()`.

**Log message format** (using the existing `%(name)s` field in the log format):
```
<timestamp> INFO jotquote.web_viewer:settings: /home/user/.jotquote/settings.conf
<timestamp> INFO jotquote.web_viewer:quotes: /home/user/.jotquote/quotes.txt
<timestamp> INFO jotquote.web_viewer:version: 0.9.5
```

## Files to Add Tests To

### `tests/integration/test_web_viewer.py`

Add two new integration test functions that verify all three startup log lines appear in stderr:

- `test_webserver_startup_logs(tmp_path)` — launches via `jotquote webserver`, checks for `settings:`, `quotes:`, and `version:` substrings in stderr. Uses the existing `_run_server_test` helper or a similar inline pattern.
- `test_waitress_serve_startup_logs(tmp_path)` — launches via `waitress-serve ... jotquote.web_viewer:app`, same checks.

Both tests should use the existing helpers: `_make_env`, `_copy_quotes`, `_collect_stderr`, `wait_for_server`, and `wait_for_log_line`.

## TDD Order

1. Write `test_webserver_startup_logs` and `test_waitress_serve_startup_logs` — confirm they fail.
2. Implement `_log_startup_info()` and the module-level call in `web_viewer.py`.
3. Confirm both new tests pass, existing tests still pass.
4. Run the linter: `uv run jotquote lint` with `JOTQUOTE_CONFIG=jotquote/templates/settings.conf`.

## Verification

```bash
# Run new integration tests
uv run pytest tests/integration/test_web_viewer.py::test_webserver_startup_logs
uv run pytest tests/integration/test_web_viewer.py::test_waitress_serve_startup_logs

# Full test suite
uv run pytest

# Lint built-in quotes
export JOTQUOTE_CONFIG=jotquote/templates/settings.conf
uv run jotquote lint
```
