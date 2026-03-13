# Plan: Switch to Waitress and document dual launch methods

## Context
`jotquote webserver` currently uses Flask's built-in Werkzeug dev server (`app.run()`), which prints an unavoidable "do not use in production" warning. Switching `run_server()` to Waitress eliminates the warning and uses a production-grade server while keeping the same single-command launch. The `app` object in `web.py` is a standard WSGI object, so any other WSGI server (Gunicorn, uWSGI, etc.) can also serve it directly — this alternative should be documented.

## Files to Modify

### 1. [pyproject.toml](pyproject.toml)
- Add `"waitress>=3.0"` to the `dependencies` list (alongside flask and click)

### 2. [jotquote/web.py](jotquote/web.py)
Update `run_server()` (lines 82–109):
- Replace `app.run(host=listen_ip, port=listen_port)` with `from waitress import serve` + `serve(app, host=listen_ip, port=int(listen_port))`
- Rewrite the docstring to explain: (a) Waitress is used as the WSGI server, (b) as an alternative, any WSGI server can be pointed at the `app` object exported from this module

### 3. [README.md](README.md)
Expand the "Starting the web server" section (lines 28–41) to document both methods:
- **Method 1** (`jotquote webserver`): simple single command, reads host/port from settings.conf — no mention of Waitress
- **Method 2** (direct WSGI): point any WSGI server at `jotquote.web:app`, e.g. `waitress-serve` or `gunicorn`; host/port passed on the command line

### 4. [DEVELOPMENT.md](DEVELOPMENT.md)
Add a new "Running the web server" section (after "Running unit tests") explaining both methods in a development context:
- Method 1: `uv run jotquote webserver`
- Method 2 (Linux/Mac): `uv run gunicorn jotquote.web:app`

### 5. [tests/webserver_integration_test.py](tests/webserver_integration_test.py) — new file
Two subprocess-based integration tests using `urllib.request` (stdlib) for HTTP:

**Setup approach**: both tests set `HOME`/`USERPROFILE` env vars in the subprocess to a `tmp_path` containing a minimal `settings.conf` (pointing to a copied test quote file at port 15544 on 127.0.0.1). This avoids touching the user's real `~/.jotquote/`.

**Helper**: `wait_for_server(url, timeout=10)` — polls with `urllib.request.urlopen` until a 200 is returned or timeout is reached.

**Test 1 — `test_webserver_command`** (all platforms):
- Starts `jotquote webserver` via `subprocess.Popen` with the temp HOME env
- Calls `wait_for_server`
- Asserts HTTP 200 and that response body contains expected HTML (e.g. `<title>jotquote</title>`)
- Kills subprocess in `finally` block

**Test 2 — `test_waitress_serve_command`** (all platforms):
- Starts `waitress-serve --host 127.0.0.1 --port 15544 jotquote.web:app` via `subprocess.Popen` with temp HOME env
- Same `wait_for_server` + assertion + cleanup pattern as Test 1

**Test 3 — `test_gunicorn_launch`** (Linux/Mac only):
- Decorated with `@pytest.mark.skipif(sys.platform == 'win32', reason='gunicorn not supported on Windows')`
- Starts `gunicorn --bind 127.0.0.1:15544 jotquote.web:app` via `subprocess.Popen` with temp HOME env
- Same `wait_for_server` + assertion + cleanup pattern as Test 1

### 6. [pyproject.toml](pyproject.toml) (dev dependencies)
- Add `"gunicorn>=23.0"` to the `[dependency-groups]` dev group (used only in the integration test)

### 7. [uv.lock](uv.lock)
- Regenerated automatically by `uv sync --group dev` after dependency changes

## Implementation Steps

1. Edit `pyproject.toml`: add `"waitress>=3.0"` to `dependencies`
2. Edit `pyproject.toml`: add `"gunicorn>=23.0"` to dev `[dependency-groups]`
3. Edit `jotquote/web.py`: update `run_server()` to use `waitress.serve()` and rewrite its docstring
4. Edit `README.md`: expand "Starting the web server" section
5. Edit `DEVELOPMENT.md`: add "Running the web server" section with both methods
6. Create `tests/webserver_integration_test.py` with the two integration tests
7. Run `uv sync --group dev` to regenerate `uv.lock`
8. Run `uv run pytest` to verify all tests pass
9. Save a copy of this plan to [plans/](plans/) as `2026-03-13-switch-to-waitress.md`

## Verification

- `uv run pytest` passes (gunicorn test is skipped on Windows)
- `uv run jotquote webserver` starts without the Werkzeug production warning
- `uv run gunicorn jotquote.web:app` (Linux/Mac) also starts successfully
