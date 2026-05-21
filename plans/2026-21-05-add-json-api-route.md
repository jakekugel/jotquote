# Plan: JSON `/api` route for the jotquote web viewer

## Context

The jotquote web viewer currently serves only HTML pages. There is no way for
external clients (scripts, dashboards, other apps) to consume the daily quote
programmatically. This plan adds a JSON endpoint `GET /api` that returns the
quote and its metadata, mirroring the HTML root page's behavior: timezone-aware
"today", quote resolver, seeded RNG fallback, midnight-aware cache expiration
(in `daily` mode), and the `header_provider_extension` extension point for
cache/auth headers.

`/api` honors `[web].mode` exactly like the HTML root route: in `daily` mode
it returns the deterministic daily quote; in `random` mode it returns a truly
random quote on each request.

## Files to modify

- [jotquote/web/viewer.py](jotquote/web/viewer.py) — add `apiroute()`, extract `_select_quote_for_date()` helper
- [tests/unit/web/test_viewer.py](tests/unit/web/test_viewer.py) — unit tests
- [tests/integration/test_web_viewer.py](tests/integration/test_web_viewer.py) — integration tests
- [USER_DOCUMENTATION.md](USER_DOCUMENTATION.md) — document the new endpoint

No changes to `settings.conf` — no new config keys (the existing
`header_provider_extension` is reused).

## Implementation

### 1. Extract `_select_quote()` helper in `viewer.py`

`showpage()` lines 190-225 contain all quote-selection logic (the `random`
branch plus the resolver-first / RNG-fallback branch). The new route needs
the same behavior, so extract the whole block to avoid duplication:

```python
def _select_quote(config, quotes, mode, date_path_param, now, tz_name):
    """Return (quote, index, permalink) for the configured mode.

    In ``random`` mode (and only on routes without a date_path_param),
    returns a truly random quote with no permalink. Otherwise tries the
    configured quote resolver, falling back to seeded RNG on the root/api
    route or 404 on dated permalink routes when no resolver match is found.
    """
    # Truly random selection only when no date is requested
    if mode == 'random' and date_path_param is None:
        quote = api.get_first_match(quotes, rand=True)
        return quote, quotes.index(quote), None

    # Daily / dated path: try resolver first
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
            permalink = f'/{lookup_date}' if date_path_param is None else None
            return quote, index, permalink
        if date_path_param:
            abort(404)
        index = api.get_random_choice(len(quotes), timezone=tz_name)
        return quotes[index], index, None

    if date_path_param:
        abort(404)
    index = api.get_random_choice(len(quotes), timezone=tz_name)
    return quotes[index], index, None
```

Then replace the entire selection block in `showpage()` (lines 190-225) with:

```python
quote, index, permalink = _select_quote(config, quotes, mode, date_path_param, now, tz_name)
```

This extraction is behavior-preserving — existing tests must remain green
after this change before the new `apiroute()` is added.

### 2. Add `apiroute()` in `viewer.py`

Imports: add `jsonify` to the existing `from flask import ...` line.

Register the route just after `aboutpage()` (around current line 130):

```python
@app.route('/api')
def apiroute():
    # Read configuration and current local time
    config = api.get_config()
    now, tz_name = _get_local_now(config)
    mode = config[api.SECTION_WEB].get('mode', 'daily')

    # Compute cache lifetime (capped at midnight in daily mode) and expires_at
    expiration_seconds, expires_at = _compute_expiration(config, mode, None, now)
    g.expires_at = expires_at

    # Build both date representations
    date_url = now.strftime('%Y%m%d')
    date_formatted = now.strftime('%A, %B %d, %Y')

    # Load quotes; return 503 JSON when unavailable, still applying ext headers
    quotes = get_quotes()
    if quotes is None:
        response = make_response(jsonify({'error': 'quotes unavailable'}), 503)
        _apply_headers(response, config, expiration_seconds)
        return response

    # Select the quote (mirrors HTML root: random | resolver | seeded RNG)
    quote, _index, _permalink = _select_quote(config, quotes, mode, None, now, tz_name)

    # Build and return the JSON response
    body = {
        'quote': quote.quote,
        'author': quote.author,
        'publication': quote.publication,
        'date': date_url,
        'date_formatted': date_formatted,
        'expires_at': expires_at,
    }
    response = make_response(jsonify(body), 200)
    _apply_headers(response, config, expiration_seconds)
    return response
```

Notes:
- `jsonify` sets `Content-Type: application/json` automatically.
- `quote.publication` may be `None` — serialized as JSON `null`.
- Setting `g.expires_at` lets the existing `log_request` after-request hook
  log `expires_at=...` for `/api` access lines for free.
- `_compute_expiration` already applies the midnight cap only in `daily`
  mode — passing the actual mode gives `/api` the same caching behavior the
  HTML root route uses today.

### 3. Unit tests — append to [tests/unit/web/test_viewer.py](tests/unit/web/test_viewer.py)

All tests use the existing `flask_client`, `config`, and `monkeypatch` fixtures. Reuse the existing `_cache_control_provider` helper.

1. `test_api_returns_json_content_type` — `GET /api` returns 200 with `Content-Type` starting with `application/json`.
2. `test_api_response_has_all_fields` — JSON body keys equal exactly `{quote, author, publication, date, date_formatted, expires_at}`.
3. `test_api_field_types` — types correct; `publication` is `str` or `None`.
4. `test_api_date_format_yyyymmdd` — `body['date']` matches `^\d{8}$` and parses with `strptime('%Y%m%d')`.
5. `test_api_date_formatted_long_form` — `body['date_formatted']` parses with `strptime('%A, %B %d, %Y')`.
6. `test_api_expires_at_iso_z_suffix` — `body['expires_at']` matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` and is in the future.
7. `test_api_header_provider_applied` — monkeypatch `_header_fn` to `_cache_control_provider`; assert `Cache-Control` with valid `max-age` on the JSON response.
8. `test_api_no_header_provider` — with `_header_fn=None`, `_header_loaded=False`; no `Cache-Control` set.
9. `test_api_quote_file_missing_returns_503` — remove the quote file, monkeypatch a header provider; assert status 503, body `{'error': 'quotes unavailable'}`, and the provider's headers still applied.
10. `test_api_resolver_overrides_rng` — monkeypatch `_resolver_fn` to return a known 16-char hash from `quotes5.txt`; assert returned `quote`/`author` match.
11. `test_api_daily_mode_stable` — default (`daily`) mode; call `/api` twice; assert identical `quote` (deterministic per day).
12. `test_api_random_mode_varies` — set `config[api.SECTION_WEB]['mode'] = 'random'`; call `/api` many times against a multi-quote fixture; assert at least two distinct `quote` values are observed (random-mode behavior is exercised). Use a loop with a high enough bound (e.g. 30 attempts) to make the test reliable.

Also: verify that the existing `showpage` tests still pass after the `_select_quote` extraction (no new test needed — re-run the existing suite).

### 4. Integration tests — append to [tests/integration/test_web_viewer.py](tests/integration/test_web_viewer.py)

Use the existing `_make_env`, `_copy_quotes`, `wait_for_server`, `_collect_stderr` scaffolding (mirrors the `test_header_provider` pattern at line 299).

1. `test_api_endpoint_returns_json` — `jotquote webserver` running; `urlopen(TEST_URL + 'api')` returns 200, `Content-Type` starts with `application/json`, JSON parses, all six keys present, `date` is 8 digits, `expires_at` ends with `Z`, `quote`/`author` non-empty.
2. `test_api_header_provider_applied` — server started with `header_provider_extension='tests.fixtures.test_header_provider'`; GET `/api`; assert `X-Custom-Test: hello` and `Cache-Control` with `max-age=` on the JSON response.
3. `test_api_random_mode` — server started with `web_mode='random'`; hit `/api` repeatedly (e.g. 30 times) against the multi-quote fixture; assert at least two distinct `quote` values are observed (confirms `/api` honors random mode end-to-end).

### 5. Documentation

In [USER_DOCUMENTATION.md](USER_DOCUMENTATION.md), insert a new `### JSON API` subsection between the existing `### Mode` block (line 231) and the `---` separator (line 238):

```
### JSON API

`GET /api` returns the current quote as JSON. The endpoint honors the
configured `mode` the same way the HTML root route does — a deterministic
daily quote in `daily` mode, or a fresh random quote on each request in
`random` mode. Response shape:

    {
      "quote": "...",
      "author": "...",
      "publication": "..." | null,
      "date": "YYYYMMDD",
      "date_formatted": "Weekday, Month DD, YYYY",
      "expires_at": "YYYY-MM-DDTHH:MM:SSZ"
    }

When the quote file is unavailable the endpoint responds with HTTP 503 and
body `{"error": "quotes unavailable"}`. Custom HTTP headers configured via
`header_provider_extension` are applied to both success and error responses.
```

No table entries need to be added under `[web]` — no new config keys.

## TDD sequence

1. Write unit tests 1-3 (basic shape) — confirm red.
2. Refactor: extract `_select_quote()`; run existing test suite — confirm still green.
3. Implement minimal `apiroute()` (happy path only) — tests 1-3 green.
4. Add tests 4-6 (date / expires_at formats) — red, then green.
5. Add tests 7-9 (headers + 503) — red, then green.
6. Add tests 10-12 (resolver, daily-stable, random-varies) — red, then green.
7. Add integration tests 1-3.
8. Update `USER_DOCUMENTATION.md`.
9. Save final plan to [plans/](plans/) per project rule (filename: `2026-21-05-add-json-api-route.md`).

## Verification

Run from the repo root in this order:

```bash
uv run pytest tests/unit/web/test_viewer.py -v          # unit tests, including new ones
uv run pytest tests/integration/test_web_viewer.py -v   # integration tests
uv run pytest                                            # full suite
uv run ruff check                                        # lint

# Project rule: ensure built-in quotes lint clean
JOTQUOTE_CONFIG=jotquote/resources/settings.conf uv run jotquote lint
```

Manual smoke test:

```bash
uv run jotquote webserver &
curl -s http://127.0.0.1:5544/api | python -m json.tool
curl -i http://127.0.0.1:5544/api | head -20   # eyeball Content-Type + headers
```

Expected: pretty-printed JSON with the six documented fields; `Content-Type:
application/json`; `expires_at` near today's local midnight (+60-120s
jitter).
