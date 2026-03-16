# Plan: web_review.py, review.html, and api.settags()

## Context
A new Flask app (`web_review.py`) serves the daily quote alongside an interactive tag management panel. The page shows all unique tags from the quote file in a two-column checkbox list; tags on the current quote are pre-checked. Submitting the form updates the quote's tags via a POST `/settags` route, which delegates to a new `api.settags()` function. No caching. The new `api.settags()` consolidates logic currently inline in the CLI, which will be updated to call it. A new `Quote.get_num_stars()` method will be extracted and reused in both `web.py` and `web_review.py`. Documentation will be added in `REVIEW.md`.

## Files to Modify / Create
| File | Action |
|---|---|
| `jotquote/api.py` | Add `settags()` function; add `get_num_stars()` method on `Quote` |
| `jotquote/cli.py` | Update `settags` command to delegate to `api.settags()` |
| `jotquote/web.py` | Replace inline star logic with `quote.get_num_stars()` |
| `jotquote/web_review.py` | Create new Flask app |
| `jotquote/templates/review.html` | Create new template |
| `tests/api_test.py` | Add unit tests for `api.settags()` |
| `tests/web_review_integration_tests.py` | Create integration tests modeled on `webserver_integration_test.py` |
| `REVIEW.md` | Create usage documentation |

---

## 1. Quote.get_num_stars() method

Add to the `Quote` class in `jotquote/api.py`:

```python
def get_num_stars(self):
    """Return the star rating (0-5) derived from star tags."""
    for i, label in enumerate(['1star', '2stars', '3stars', '4stars', '5stars'], 1):
        if self.has_tag(label):
            return i
    return 0
```

Update `web.py` to replace the inline star-extraction loop with `quote.get_num_stars()`.

---

## 2. api.settags() Function

Add to `jotquote/api.py`. Uses `click.ClickException` (already used throughout `api.py`).

**Signature:**
```python
def settags(quotefile, n, hash, newtags):
```

**Parameters:**
- `quotefile` — path to the quote file
- `n` — 1-based quote number (int or None)
- `hash` — 16-char MD5 hash string (str or None)
- `newtags` — list of tag strings (already parsed; pass `[]` to clear all tags)

**Logic:**
1. Raise `ClickException` if both `n` and `hash` are provided
2. Raise `ClickException` if neither is provided
3. Call `read_quotes(quotefile)`
4. Find quote:
   - By `n`: `quotes[n - 1]` — raise `ClickException` if index out of range
   - By `hash`: iterate to find `q.get_hash() == hash` — raise `ClickException` if not found
5. `quote.set_tags(newtags)`
6. `write_quotes(quotefile, quotes)`

---

## 3. cli.py settags update

Simplify the existing `settags` command to delegate to `api.settags()`:

```python
def settags(ctx, number, hash, newtags):
    quotefile = ctx.obj['QUOTEFILE']
    quotenum = _parse_number_arg(number)
    tags = api.parse_tags(newtags)
    api.settags(quotefile, n=quotenum, hash=hash, newtags=tags)
```

---

## 4. web_review.py

```python
from flask import Flask, render_template, request, redirect
from jotquote import api
import datetime

app = Flask(__name__)

@app.route('/')
def index():
    config = api.get_config()
    quotefile = config.get(api.APP_NAME, 'quote_file')
    page_title = config.get(api.APP_NAME, 'web_page_title', fallback='jotquote')
    show_stars = config.getboolean(api.APP_NAME, 'web_show_stars', fallback=False)

    quotes = api.read_quotes(quotefile)
    idx = api.get_random_choice(len(quotes))
    quote = quotes[idx]

    all_tags = api.read_tags(quotefile)
    quote_tags = set(quote.tags)
    date1 = datetime.datetime.now().strftime("%A, %B %-d, %Y")  # same format as web.py

    return render_template('review.html',
        quote=quote.quote, author=quote.author, publication=quote.publication,
        hash=quote.get_hash(), date1=date1,
        page_title=page_title, show_stars=show_stars, stars=quote.get_num_stars(),
        all_tags=all_tags, quote_tags=quote_tags)

@app.route('/settags', methods=['POST'])
def settags():
    config = api.get_config()
    quotefile = config.get(api.APP_NAME, 'quote_file')
    hash_val = request.form.get('hash')
    newtags = request.form.getlist('tags')
    api.settags(quotefile, n=None, hash=hash_val, newtags=newtags)
    return redirect('/')
```

**On the HTTP verb:** HTML forms natively support only GET and POST. This operation performs a full replacement of a quote's tags (REST: PUT semantics), but POST is the correct choice for browser form submissions without JavaScript. No workaround needed.

No `run_server()` — started with `flask --app jotquote/web_review.py run`.

---

## 5. review.html

Based on `quote.html`. Changes:
- **Remove** EDIT TAGS button and hidden command div
- **Add** below the bottom `<hr>` a `<form method="POST" action="/settags">`:
  - `<input type="hidden" name="hash" value="{{ hash }}">`
  - Two-column tag list (CSS `column-count: 2`):
    ```html
    <div style="column-count: 2; margin-top: 1em;">
      {% for tag in all_tags %}
        <div>
          <input type="checkbox" name="tags" value="{{ tag }}"
            {% if tag in quote_tags %}checked{% endif %}>
          {{ tag }}
        </div>
      {% endfor %}
    </div>
    ```
  - `<button type="submit">Save Tags</button>`

---

## 6. Unit Tests — tests/api_test.py

Add pytest-style tests (no class, using `tmp_path` and `config` fixture from `conftest.py`).

| Test | Scenario |
|---|---|
| `test_settags_by_hash` | Find quote by hash, replace tags, verify file written correctly |
| `test_settags_by_number` | Find quote by 1-based n, replace tags |
| `test_settags_clears_tags` | Pass `newtags=[]`, verify tags cleared |
| `test_settags_both_n_and_hash_raises` | Both provided → ClickException |
| `test_settags_neither_n_nor_hash_raises` | Neither provided → ClickException |
| `test_settags_hash_not_found_raises` | Unknown hash → ClickException |
| `test_settags_n_out_of_range_raises` | n > len(quotes) → ClickException |

---

## 7. Integration Tests — tests/web_review_integration_tests.py

Modeled on `webserver_integration_test.py`. Uses `subprocess.Popen` to launch the Flask dev server (`flask --app jotquote/web_review.py run --port 15545`). Reuse helpers from the existing file (or duplicate as needed): `_make_env()`, `_copy_quotes()`, `wait_for_server()`, `wait_for_log_line()`.

| Test | Scenario |
|---|---|
| `test_get_index` | Server starts, GET `/` returns HTTP 200 with `<title>jotquote</title>` |
| `test_tags_displayed` | GET `/` response body contains tag checkbox inputs |
| `test_page_title_config` | `web_page_title` config value appears in `<title>` |
| `test_post_settags` | POST `/settags` with hash + tags updates the quote file and redirects (HTTP 302) |

Use a different port (`15545`) to avoid conflicts with the existing integration tests.

---

## 8. REVIEW.md

Create at the project root. Include:
- Brief description of what the review app does
- **Prominent security warning**: the app has no authentication or access control and must only be run bound to `127.0.0.1` (localhost); never expose it on a network interface
- How to launch: `flask --app jotquote/web_review.py run` (Flask dev server binds to 127.0.0.1 by default)
- How to configure quote file (settings.conf)
- What the page shows (daily quote + all-tags checkbox list)
- How to save tag changes

---

## Verification

1. `uv run python -c "from jotquote import web_review; print('ok')"` — no import errors
2. `uv run pytest tests/api_test.py -k settags` — all new unit tests pass
3. `uv run pytest tests/web_review_integration_tests.py` — all integration tests pass
4. `uv run pytest` — full suite still passes
5. `uv run ruff check jotquote/` — no lint errors
6. Manual: `flask --app jotquote/web_review.py run` → verify quote + two-column checkboxes; save tags and confirm file updated
