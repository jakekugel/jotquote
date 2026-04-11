# Plan: Add Full Screen Button to quote.html

## Context

The user wants a fullscreen toggle button added to the quote viewer web page, positioned to the right of the existing buttons (permalink, about, theme toggle). The SVG icon (`full-screen-circle.svg`) already exists in the static icons directory. The third-party licenses file also needs updating with the icon's attribution.

## Files Modified

1. `jotquote/templates/quote.html` -- added button HTML, CSS, and JavaScript
2. `LICENSES_THIRD_PARTY.txt` -- added icon attribution entry
3. `tests/unit/test_web_viewer.py` -- added unit test for fullscreen button

## Implementation

### 1. CSS (quote.html `<style>` section)

Added `.fullscreen-icon` to the existing shared icon rule and added a new rule for the mask-image referencing `full-screen-circle.svg`.

### 2. HTML (quote.html, inside `.btn-group`, after the theme toggle include)

Added the fullscreen button after `{% include '_theme_toggle.html' %}` with `margin-left: 1.25em` for spacing.

### 3. JavaScript (quote.html `<script>` section)

Added a `toggleFullscreen()` function using the Fullscreen API that toggles between `requestFullscreen()` and `exitFullscreen()`.

### 4. LICENSES_THIRD_PARTY.txt

Appended entry for Full Screen Circle Icon from Solar Outline Icons collection (CC Attribution License, author: Solar Icons).

### 5. Tests (TDD -- red/green)

Added `test_fullscreen_button_present` in `tests/unit/test_web_viewer.py` verifying the button ID, click handler, and icon class appear in the rendered HTML.

## Verification

- All 379 tests pass, 1 skipped
- Ruff linter: all checks passed
