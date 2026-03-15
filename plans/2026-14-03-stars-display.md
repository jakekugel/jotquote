# Plan: Display Star Ratings on Web Page

## Context

Quotes can be tagged with `1star`, `2stars`, `3stars`, `4stars`, or `5stars` to indicate a rating. The web page should visually display the corresponding number of filled star characters (★) beneath the quote, so users can see the rating at a glance. Quotes without a star tag show nothing extra.

---

## Changes

### 1. `jotquote/web.py` — extract star count from tags

In `showpage()`, after `quote = quotes[index]`, compute a `stars` integer (0 = no rating, 1–5 otherwise):

```python
_STAR_TAG_MAP = {'1star': 1, '2stars': 2, '3stars': 3, '4stars': 4, '5stars': 5}
stars = next((v for t, v in _STAR_TAG_MAP.items() if t in quote.tags), 0)
```

Pass `stars=stars` to `render_template(...)`.

### 2. `jotquote/templates/quote.html` — render stars

**CSS** — add a `.stars` rule after `.publication`:

```css
.stars {
    font-size: 175%;
    color: #FFD700;
    text-align: right;
}
```

**HTML** — add a conditional `<div>` between the publication block and the second `<div class="horiz-line">`:

```html
{% if stars > 0 %}
    <div class="stars">{{ '★' * stars }}</div>
{% endif %}
```

### 3. `tests/web_test.py` — add unit tests

Two tests added:
- `test_stars_displayed`: writes a quote with `3stars` tag to the temp file, monkeypatches `get_random_choice` to return index 0, asserts `★★★` in response and `★★★★` not in response.
- `test_no_stars_when_untagged`: verifies no `class="stars"` div appears for quotes without a star tag.

### 4. `tests/webserver_integration_test.py` — add integration test

`test_stars_displayed`: writes a single-quote file with `3stars` tag, starts a real `jotquote webserver` subprocess, fetches the page, and asserts `★★★` is present in the body. A single-quote file guarantees `get_random_choice(1)` always returns index 0 (`days % 1 == 0`).

---

## Critical files

- [jotquote/web.py](jotquote/web.py)
- [jotquote/templates/quote.html](jotquote/templates/quote.html)
- [tests/web_test.py](tests/web_test.py)
- [tests/webserver_integration_test.py](tests/webserver_integration_test.py)

---

## Verification

```bash
uv run pytest tests/web_test.py -v
uv run pytest tests/webserver_integration_test.py::test_stars_displayed -v
uv run pytest
```
