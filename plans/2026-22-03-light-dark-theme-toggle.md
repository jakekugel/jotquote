# Plan: Light/Dark Theme Toggle + UI Polish

## Context

The jotquote web server currently uses a fixed dark color scheme hard-coded into all three HTML templates. This change introduces configurable light/dark colors via `settings.conf`, a client-side theme toggle button (with localStorage persistence), a clipboard-copy permalink icon, and several HTML standards-compliance fixes.

---

## 1. New Config Properties (`settings.conf`)

Add four optional properties, read in `web.py`. No changes needed to `api.py` — the existing `.get(key, default)` pattern handles optional keys.

| Property | Default |
|---|---|
| `web_light_foreground_color` | `#000000` |
| `web_light_background_color` | `#ffffff` |
| `web_dark_foreground_color` | `#ffffff` |
| `web_dark_background_color` | `#000000` |

> **Note on defaults:** The current dark scheme uses `#1a1a1a`/`#e8e8e8` — those only apply if the user explicitly sets them. The new default dark is pure black/white.

---

## 2. Changes to `jotquote/web.py`

In `showpage()`, read the four color values and pass them to all three `render_template()` calls:

```python
web_light_fg = config[api.APP_NAME].get('web_light_foreground_color', '#000000')
web_light_bg = config[api.APP_NAME].get('web_light_background_color', '#ffffff')
web_dark_fg  = config[api.APP_NAME].get('web_dark_foreground_color',  '#ffffff')
web_dark_bg  = config[api.APP_NAME].get('web_dark_background_color',  '#000000')
```

Pass as `light_fg`, `light_bg`, `dark_fg`, `dark_bg` to all three render calls (including `unavailable.html`).

---

## 3. CSS Theming Strategy (all three templates)

Use CSS custom properties with a `data-theme` attribute on `<html>`. A tiny inline `<script>` in `<head>` reads `localStorage` and sets the attribute *before* the page renders, preventing a flash of the wrong theme.

```html
<script>
  document.documentElement.setAttribute(
    'data-theme',
    localStorage.getItem('jotquote-theme') || 'dark'
  );
</script>
```

Define two theme blocks in the `<style>` section. The configurable fg/bg are injected via Jinja; derived "accent" colors are hardcoded per theme:

```css
[data-theme="dark"] {
  --fg:           {{ dark_fg }};
  --bg:           {{ dark_bg }};
  --horiz-line:   #555555;
  --cmd-bg:       #505050;
  --cmd-fg:       #e8e8e8;
  --input-bg:     #2a2a2a;
  --border-color: #555555;
  --btn-bg:       #444444;
  --muted-fg:     #999999;
}

[data-theme="light"] {
  --fg:           {{ light_fg }};
  --bg:           {{ light_bg }};
  --horiz-line:   #aaaaaa;
  --cmd-bg:       #e4e4e4;
  --cmd-fg:       #111111;
  --input-bg:     #f4f4f4;
  --border-color: #bbbbbb;
  --btn-bg:       #dddddd;
  --muted-fg:     #555555;
}
```

Replace all hard-coded color values in each template's CSS with `var(--...)` references. Apply `background-color: var(--bg); color: var(--fg);` to `body` via a CSS rule (remove the inline `style=""` attribute).

---

## 4. Theme Toggle Button (`quote.html` and `review.html`)

**Placement:** Add to the existing flex footer row (the div below the lower horizontal rule).

**Icon:** Unicode swap — show ☀ when in dark mode (click for light), show 🌙 when in light mode (click for dark).

```html
<button class="icon-btn" id="theme-toggle" onclick="toggleTheme()"
        title="Toggle light/dark mode" aria-label="Toggle light/dark mode"></button>
```

```javascript
function toggleTheme() {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('jotquote-theme', next);
  document.getElementById('theme-toggle').textContent = next === 'dark' ? '\u2600' : '\uD83C\uDF19';
}
document.addEventListener('DOMContentLoaded', function() {
  const theme = document.documentElement.getAttribute('data-theme') || 'dark';
  document.getElementById('theme-toggle').textContent = theme === 'dark' ? '\u2600' : '\uD83C\uDF19';
});
```

**Button CSS (shared for both icon buttons):**
```css
.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted-fg);
  font-size: 100%;
  padding: 0;
  line-height: 1;
}
.icon-btn:hover { opacity: 0.7; }
```

---

## 5. Clipboard Permalink Button (`quote.html`)

Replace `<span class="permalink"><a href="{{ permalink }}">permalink</a></span>` with an icon-only button that copies the URL to the clipboard.

**Icon:** 🔗 (link emoji)

```html
{% if permalink %}
  <button class="icon-btn" id="permalink-btn" onclick="copyPermalink('{{ permalink }}')"
          title="Copy permalink" aria-label="Copy permalink">&#x1F517;</button>
{% endif %}
```

```javascript
function copyPermalink(path) {
  navigator.clipboard.writeText(window.location.origin + path);
}
```

`navigator.clipboard` is the modern standard (no deprecated `document.execCommand`).

Remove the `.permalink` and `.permalink a` CSS rules; both buttons share `.icon-btn`.

> **Existing test update required:** `test_root_with_quotemap_today` currently asserts `f'href="/{today}"'.encode() in rv.data`. Since the permalink is now a button (not an anchor), this assertion must be updated to check for `f'copyPermalink(\'/{today}\')'.encode()` or similar.

---

## 6. localStorage vs. Cookies

**Use `localStorage`.** It is the modern standard for client-side UI preferences — not sent to the server, no expiry management, simpler API.

---

## 7. HTML Standards Compliance Fixes

Apply to all three templates:

| Issue | Fix |
|---|---|
| Missing `lang` attribute | `<html lang="en">` |
| `<link rel="shortcut icon">` | `<link rel="icon">` |
| `unavailable.html` missing `<meta name="viewport">` | Add it |
| `unavailable.html` loads Open Sans via external Google Fonts `http://` link | Remove; add self-hosted `@font-face` blocks matching the other templates |
| `quote.html` vendor-prefixed transforms | Remove `-webkit-transform`, `-moz-transform`, `-o-transform`, `-ms-transform` |
| Inline `body style="..."` | Remove; move to CSS rule using custom properties |

---

## 8. New Tests

### Unit tests — `tests/web_test.py`

**`test_web_theme_colors_default`** — verify default dark-mode color values appear in rendered HTML when no color config properties are set:
```python
def test_web_theme_colors_default(flask_client, config):
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'--fg: #ffffff' in rv.data
    assert b'--bg: #000000' in rv.data
```

**`test_web_theme_colors_custom`** — verify custom colors from config appear in rendered HTML:
```python
def test_web_theme_colors_custom(flask_client, config):
    config[api.APP_NAME]['web_dark_foreground_color'] = '#cccccc'
    config[api.APP_NAME]['web_dark_background_color'] = '#111111'
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'--fg: #cccccc' in rv.data
    assert b'--bg: #111111' in rv.data
```

**`test_theme_toggle_button_present`** — verify toggle button is rendered in quote.html:
```python
def test_theme_toggle_button_present(flask_client):
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'id="theme-toggle"' in rv.data
```

**`test_permalink_button_present`** — verify clipboard button appears when quotemap has a today entry:
```python
def test_permalink_button_present(flask_client, config, tmp_path):
    client, quote_file = flask_client
    today = datetime.datetime.now().strftime('%Y%m%d')
    quotemap_file = tmp_path / 'quotemap.txt'
    quotemap_file.write_text(f'{today}: 25382c2519fb23bd\n', encoding='utf-8')
    config[api.APP_NAME]['quotemap_file'] = str(quotemap_file)
    rv = client.get('/')
    assert b'id="permalink-btn"' in rv.data
    assert b'copyPermalink' in rv.data
```

### Integration test — `tests/web_integration_test.py`

**`test_web_theme_colors_config`** — starts a real server with custom color config and verifies the colors appear in the page response body:
```python
def test_web_theme_colors_config(tmp_path):
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(
        tmp_path, quote_file,
        web_dark_foreground_color='#aabbcc',
        web_dark_background_color='#112233',
        web_light_foreground_color='#334455',
        web_light_background_color='#eeddcc',
    )
    proc = subprocess.Popen(...)
    # assert all four color values appear in the response body
```

---

## 9. CLAUDE.md Updates

Two additions to [CLAUDE.md](CLAUDE.md):

1. **Under the Plans section:** Add a note that all non-trivial implementation plans must include an appropriate number of new unit tests and at least one new integration test.

2. **New `settings.conf` section:** Add a note that if `settings.conf` properties are added, removed, or changed, the table in [DOCUMENTATION.md](DOCUMENTATION.md) must be updated.

---

## 10. New `DOCUMENTATION.md`

Create [DOCUMENTATION.md](DOCUMENTATION.md) at the repo root. Add a `## settings.conf` section with a table of the four new properties introduced by this change:

| Property | Type | Default | Description |
|---|---|---|---|
| `web_light_foreground_color` | hex color | `#000000` | Text color in light mode |
| `web_light_background_color` | hex color | `#ffffff` | Background color in light mode |
| `web_dark_foreground_color` | hex color | `#ffffff` | Text color in dark mode |
| `web_dark_background_color` | hex color | `#000000` | Background color in dark mode |

---

## 11. Critical Files

- [jotquote/web.py](jotquote/web.py) — add color var reads + pass to render_template
- [jotquote/web_review.py](jotquote/web_review.py) — add color var reads + pass to render_template
- [jotquote/templates/quote.html](jotquote/templates/quote.html) — theme CSS, toggle button, clipboard button, standards fixes
- [jotquote/templates/review.html](jotquote/templates/review.html) — theme CSS, toggle button, standards fixes
- [jotquote/templates/unavailable.html](jotquote/templates/unavailable.html) — theme CSS, standards fixes
- [tests/web_test.py](tests/web_test.py) — 4 new unit tests; update `test_root_with_quotemap_today`
- [tests/web_integration_test.py](tests/web_integration_test.py) — 1 new integration test
- [CLAUDE.md](CLAUDE.md) — 2 updates
- [DOCUMENTATION.md](DOCUMENTATION.md) — new file

---

## 12. Verification

1. `uv run pytest` — all existing tests pass; 4 new unit tests + 1 integration test pass
2. `uv run ruff check jotquote/` — no lint errors
3. Start server with `jotquote webserver` and manually verify:
   - Page defaults to dark mode on first load
   - Toggle button switches modes and persists across reload
   - Permalink clipboard button copies the URL
   - Theme persists across all three pages (quote, review, unavailable)
4. Add custom colors to `~/.jotquote/settings.conf` and verify they appear
5. Validate HTML structure in browser devtools
