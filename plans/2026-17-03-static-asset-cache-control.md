# Set long max-age for static assets

## Context
Flask's built-in static file handler only sets `Last-Modified` by default, with no `Cache-Control` header. This means browsers (and CDNs) must revalidate static assets on every page load, resulting in unnecessary 304 round-trips for files like fonts that rarely change.

## Change

### 1. `jotquote/web.py` — one line after line 13
After `app = Flask(__name__)`, add:
```python
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 24 hours
```

### 2. `tests/web_test.py` — new unit test
Add a test following the existing `test_cache_control_header` pattern (line 59). Uses the `flask_client` fixture to request a static asset and asserts the response has `Cache-Control` with the expected `max-age`:

```python
def test_static_asset_cache_control(flask_client):
    """Static assets have a long Cache-Control max-age."""
    client, quote_file = flask_client
    rv = client.get('/static/fonts/OpenSans-Regular.ttf')
    cc = rv.headers.get('Cache-Control', '')
    assert 'max-age=86400' in cc
```

### 3. `tests/web_integration_test.py` — new integration test
Add a test following the existing `_run_server_test` / `_assert_response` pattern. Starts a real server subprocess and fetches a font file, asserting the `Cache-Control` header:

```python
def test_static_asset_cache_header(tmp_path):
    """Static assets served by the webserver include a long Cache-Control max-age."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)

    proc = subprocess.Popen(
        [_script("jotquote"), "webserver"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), "Server did not start within timeout"
        url = TEST_URL.rstrip('/') + '/static/fonts/OpenSans-Regular.ttf'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            cc = resp.headers.get('Cache-Control', '')
        assert 'max-age=86400' in cc
    finally:
        proc.terminate()
        proc.wait(timeout=10)
```

## Verification
1. `uv run ruff check jotquote/ tests/` — lint passes
2. `uv run pytest tests/web_test.py tests/web_integration_test.py` — all tests pass
3. Manual: run `jotquote webserver`, load `/` twice, confirm font requests don't appear in the log on the second load
