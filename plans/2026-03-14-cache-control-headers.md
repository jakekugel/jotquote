# Plan: Add Cache-Control Headers + Pre-midnight Quote Advance

## Context

jotquote's web server serves a daily quote page via Flask. Currently no `Cache-Control` headers are set, so CDNs (e.g. Cloudflare on render.com) pass every request through to the origin — no caching benefit. The goal is to let CDNs and browsers cache the page for up to 4 hours, but never past midnight.

To prevent stale quotes being served when caches expire at midnight, the quote selection logic in `api.py` will be changed to serve the next day's quote starting at 11:45 PM. This means caches that expire at midnight already hold the correct new-day quote, so users see a seamless transition.

Note: HTML `<meta>` cache tags were considered but rejected — CDNs ignore them entirely. HTTP response headers are the correct mechanism.

## Files to Modify

- `jotquote/api.py` — advance quote selection to next day after 11:45 PM
- `jotquote/web.py` — add `Cache-Control` response headers
- `tests/api_test.py` — add tests for the time-based quote advance
- `tests/web_test.py` — add tests for the cache header

## Implementation

### 1. `jotquote/api.py` — modify `get_random_choice()` (line 476)

Replace:
```python
endday = datetime.datetime.now().date()
```
With:
```python
now = datetime.datetime.now()
if now.hour == 23 and now.minute >= 45:
    endday = (now + datetime.timedelta(days=1)).date()
else:
    endday = now.date()
```

From 11:45 PM onward, the server returns the next day's quote, so caches expiring at midnight already contain the correct new quote.

### 2. `jotquote/web.py` — `make_response` import and `Cache-Control` header

**Import change (line 9):**
```python
from flask import Flask, make_response, render_template, g, request
```

**In `showpage()`, compute `max_age` after `now` is defined:**
```python
midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
seconds_until_midnight = int((midnight - now).total_seconds())
max_age = min(14400, seconds_until_midnight)  # 14400 = 4 hours in seconds
```

**Wrap both `render_template` calls with `make_response` and set the header:**

Unavailable branch:
```python
response = make_response(render_template("unavailable.html", date1=date1))
response.headers['Cache-Control'] = f'public, max-age={max_age}'
return response
```

Normal branch (replace final `return render_template(...)`):
```python
response = make_response(render_template("quote.html", quote=quotestring, author=author, date1=date1,
                                         publication=publication, quotenum=(index + 1), totalquotes=len(quotes),
                                         space_tags=space_tags, comma_tags=comma_tags, hash=hashstring,
                                         show_tags=False))
response.headers['Cache-Control'] = f'public, max-age={max_age}'
return response
```

## Tests to Add

### `tests/api_test.py` — quote advance logic (pytest style, using `monkeypatch`)

```python
import datetime as real_datetime


def test_get_random_choice_uses_today_before_cutoff(monkeypatch):
    """Before 11:45 PM, today's date drives quote selection."""
    class FakeDatetime(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 3, 14, 23, 44, 0)

    monkeypatch.setattr(api.datetime, 'datetime', FakeDatetime)
    result = api.get_random_choice(100)
    beginday = real_datetime.date(2016, 1, 1)
    days = (real_datetime.date(2026, 3, 14) - beginday).days
    assert result == api._get_random_value(days, 100)


def test_get_random_choice_uses_tomorrow_at_cutoff(monkeypatch):
    """At 11:45 PM exactly, tomorrow's date drives quote selection."""
    class FakeDatetime(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 3, 14, 23, 45, 0)

    monkeypatch.setattr(api.datetime, 'datetime', FakeDatetime)
    result = api.get_random_choice(100)
    beginday = real_datetime.date(2016, 1, 1)
    days = (real_datetime.date(2026, 3, 15) - beginday).days
    assert result == api._get_random_value(days, 100)
```

### `tests/web_test.py` — cache header

```python
def test_cache_control_header(flask_client):
    """Cache-Control header is set and max-age is within expected bounds."""
    client, quote_file = flask_client
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    assert cc.startswith('public, max-age=')
    max_age = int(cc.split('=')[1])
    assert 0 < max_age <= 14400


def test_cache_control_header_unavailable(flask_client):
    """Cache-Control header is set even when quote file is unavailable."""
    client, quote_file = flask_client
    os.remove(quote_file)
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    assert cc.startswith('public, max-age=')
    max_age = int(cc.split('=')[1])
    assert 0 < max_age <= 14400
```

## Verification

```bash
uv run python -m pytest tests/api_test.py tests/web_test.py -v
```
