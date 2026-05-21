# Plan: Client-side AJAX refresh against `/api`

## Context

Today the viewer page schedules a full-document reload at `expires_at` via
`navigation.navigate(location.href)`. That works but it discards the entire
page (CSS, fonts, JS) just to swap a quote. Now that `/api` exposes the same
quote payload as JSON, the page can refresh in place by fetching `/api`,
updating the DOM nodes that actually change, and re-scheduling itself from
the response's `expires_at`. The cross-document `@view-transition` rule is
inert for in-place updates; we preserve the cross-fade animation by wrapping
DOM updates in `document.startViewTransition()` (with a feature-test
fallback for Firefox).

Two template structural issues block the JS update: the publication div is
gated by `{% if publication is not none %}`, and the permalink button is
gated by `{% if permalink %}`. The publication div needs to always be in the
DOM (toggled via the `hidden` attribute) so JS can populate/show it.  The
permalink button keeps its server-side gating, but stores the current path in
a `data-permalink` attribute so JS can update it from the new `/api` `date`.

## Files to modify

- [jotquote/web/templates/viewer.html](jotquote/web/templates/viewer.html) — publication div, permalink button, CSS @view-transition cleanup, JS rewrite
- [tests/unit/web/test_viewer.py](tests/unit/web/test_viewer.py) — update 2 existing tests, add 4 new tests

No server-side changes. No new fixtures, config keys, or dependencies.

## Implementation

### 1. Template — publication div: always render, use `hidden`

Replace [viewer.html:213-215](jotquote/web/templates/viewer.html#L213-L215):

```html
{% if publication is not none %}
    <div class="publication">{{ publication }}</div>
{% endif %}
```

with:

```html
<div id="publication" class="publication"{% if publication is none %} hidden{% endif %}>{{ publication or '' }}</div>
```

Rationale for `hidden` over a CSS class: it's a built-in HTML feature, the
browser handles `display: none` automatically, and JS toggles it with
`el.hidden = bool` — no class string typos. Always rendering means JS can
unconditionally `getElementById('publication')`.

### 2. Template — permalink button: store path in `data-permalink`

Replace [viewer.html:220-223](jotquote/web/templates/viewer.html#L220-L223):

```html
{% if permalink %}
  <button class="icon-btn" id="permalink-btn" onclick="copyPermalink('{{ permalink }}')" ...>
```

with:

```html
{% if permalink %}
  <button class="icon-btn" id="permalink-btn" data-permalink="{{ permalink }}"
          onclick="copyPermalink(this.dataset.permalink)" ...>
```

The server-side `{% if permalink %}` gate stays — JS will not conjure a
permalink button when none exists. When the button IS present, the refresh
updates `data-permalink` to `/<new_date>`.

### 3. Template — remove dead cross-document view-transition rule

In [viewer.html:19-21](jotquote/web/templates/viewer.html#L19-L21), remove:

```css
@view-transition {
    navigation: auto;
}
```

Keep the `::view-transition-old(root)/::view-transition-new(root)` rule at
lines 23-27 — those animations also apply to `startViewTransition()`.

### 4. Template — JS rewrite

Replace the `scheduleAutoRefresh()` block at
[viewer.html:288-306](jotquote/web/templates/viewer.html#L288-L306) with:

```javascript
// Schedule the next quote refresh at the server-provided expires_at instant.
// Instead of a full-page reload, fetch /api and update the DOM in place.
// On AJAX failure (network or 5xx), retry in 60 seconds and keep the stale
// quote on screen.
async function scheduleAutoRefresh(expiresAt) {
    // First call uses the value Jinja embedded; subsequent calls pass in
    // the value from the most recent /api response.
    if (expiresAt === undefined) {
        expiresAt = {{ expires_at | tojson }};
    }
    if (!expiresAt) return;

    const reloadTime = new Date(expiresAt).getTime();
    const delay = Math.max(reloadTime - Date.now(), 0);
    console.log('The page will refresh automatically on ' + new Date(reloadTime).toLocaleString() + '.');

    setTimeout(async () => {
        try {
            const resp = await fetch('/api', {cache: 'no-store'});
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            const body = await resp.json();
            applyQuoteUpdate(body);
            scheduleAutoRefresh(body.expires_at);
        } catch (err) {
            console.warn('Quote refresh failed, retrying in 60s:', err);
            setTimeout(scheduleAutoRefresh, 60000);
        }
    }, delay);
}

// Apply quote DOM updates inside a same-document view transition so the
// cross-fade animation defined in CSS still plays.  Falls back to a plain
// update on browsers without document.startViewTransition (e.g. Firefox).
function applyQuoteUpdate(body) {
    const update = () => {
        document.querySelector('.quote').textContent = body.quote;
        document.querySelector('.author').textContent = body.author;
        document.querySelector('.date').textContent = body.date_formatted;

        const pub = document.getElementById('publication');
        pub.textContent = body.publication || '';
        pub.hidden = !body.publication;

        const permalinkBtn = document.getElementById('permalink-btn');
        if (permalinkBtn) {
            permalinkBtn.dataset.permalink = '/' + body.date;
        }
    };
    if (document.startViewTransition) {
        document.startViewTransition(update);
    } else {
        update();
    }
}

scheduleAutoRefresh();
```

Key details:
- `cache: 'no-store'` bypasses any HTTP cache for the JSON.
- The recursive `scheduleAutoRefresh(body.expires_at)` reuses the same
  function so the delay-computation logic is shared.
- `pub.textContent = body.publication || ''` handles both `null` and `''`.
- `permalinkBtn` check preserves server-side gating — the button only
  exists when the resolver matched today's quote on initial load.
- Empty-`expiresAt` short-circuit preserved so dated permalink routes
  don't auto-refresh.

## Tests

Append/update in [tests/unit/web/test_viewer.py](tests/unit/web/test_viewer.py).

### Update existing tests

1. `test_expires_at_present_on_root` (line 567): change the assertion
   `b'const expiresAt = null' not in rv.data` → `b'expiresAt = null' not in rv.data`
   (we drop the `const` since the JS now reassigns `expiresAt`).
2. `test_expires_at_null_on_date_route` (line 577): change
   `b'const expiresAt = null' in rv.data` → `b'expiresAt = null' in rv.data`.
3. `test_view_transition_css` (line 587): re-target to assert the
   same-document setup is present:
   ```python
   assert b'::view-transition-old(root)' in rv.data
   assert b'startViewTransition' in rv.data
   assert b'@view-transition {' not in rv.data  # cross-document rule removed
   ```

### New tests

4. `test_publication_div_always_rendered` — using the default `quotes5.txt`
   fixture (empty publication), assert the publication div is in the HTML
   and carries the `hidden` attribute:
   ```python
   rv = client.get('/')
   assert b'id="publication"' in rv.data
   assert b'class="publication" hidden' in rv.data
   ```
5. `test_refresh_calls_api_endpoint` — assert the JS contains
   `fetch('/api'` (single-quoted with opening paren to avoid matching
   prose).
6. `test_no_navigation_navigate` — assert `navigation.navigate` is NOT in
   the rendered HTML.
7. `test_permalink_button_uses_data_attribute` — monkeypatch the resolver
   to populate a permalink, then assert `data-permalink=` and
   `this.dataset.permalink` appear:
   ```python
   monkeypatch.setattr(web, '_resolver_fn', lambda d: 'd4a5c5a909517953')
   monkeypatch.setattr(web, '_resolver_loaded', True)
   rv = client.get('/')
   assert b'data-permalink=' in rv.data
   assert b'this.dataset.permalink' in rv.data
   ```

No JS-runtime tests — the project asserts on rendered HTML strings only.
Behavior of the in-browser fetch/animation/retry is covered by the manual
smoke checks below.

## TDD sequence

1. Update the three existing tests (`test_expires_at_present_on_root`,
   `test_expires_at_null_on_date_route`, `test_view_transition_css`).
   They go red against the current template.
2. Add the four new tests — red.
3. Edit `viewer.html`: publication div, permalink button, remove cross-doc
   CSS rule, replace the JS block.
4. Re-run `pytest tests/unit/web/test_viewer.py -v` — all new + updated
   tests green; existing tests like `test_permalink_button_present` still
   pass (the id and `copyPermalink` symbol are unchanged).
5. Run full unit suite, then integration, then `ruff check`.

## Verification

```bash
uv run pytest tests/unit/web/test_viewer.py -v   # viewer tests
uv run pytest tests/unit -q                       # full unit suite
uv run pytest tests/integration -q                # integration suite
uv run ruff check
```

Manual smoke (the parts pytest can't cover):

1. `uv run jotquote webserver` — open `/` in Chrome with DevTools Network →
   filter to fetch/XHR.
2. Temporarily set `expiration_seconds = 30` in `~/.jotquote/settings.conf`
   so the refresh fires quickly.
3. Reload page. Confirm initial render. Wait ~30s.
4. Verify: one `GET /api` request fires, returns JSON 200, the visible
   quote/author/date cross-fades to the new value (2s animation), and
   console logs the next scheduled refresh time.
5. Switch to a `/YYYYMMDD` permalink. Confirm console does NOT log a
   scheduled refresh (because `expiresAt` is null).
6. Open Firefox (no `startViewTransition`) and verify the DOM update still
   happens, without animation and without JS errors.
7. Offline test: in Chrome DevTools, toggle "Offline" before the next refresh.
   Verify the console warn appears, the stale quote stays on screen, and the
   next attempt fires ~60s later (toggle back online before that).
8. Permalink button (requires a configured `quote_resolver_extension`):
   click → copies the current path. Wait for a refresh in random mode →
   click again → copies the new `/<date>` path.
9. Publication: ensure the page works for both a quote with a publication
   (div visible) and one without (div present but `hidden`).

After approval, save this plan to
`plans/2026-21-05-ajax-refresh-against-api.md` per the project rule.
