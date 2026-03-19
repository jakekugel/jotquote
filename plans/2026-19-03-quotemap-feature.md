# Plan: Quotemap — Date-to-Quote Mapping for Web Server

## Context

Currently the jotquote web server shows a deterministic daily quote using a seeded RNG algorithm. The user wants the ability to curate which quote appears on specific dates via a **quotemap file** — a simple text file mapping dates to quote hashes. This also includes adding a date-based URL route, permalink support, and removing the `/tags` route.

## Quotemap File Syntax

The quotemap file is a plain text file (UTF-8) that maps dates to quote hashes. Each line assigns a specific quote to a specific date.

**Line format:**
```
YYYYMMDD: <16-char-hex-hash>  # optional comment
```

**Rules:**
- The date portion must be exactly 8 digits (`YYYYMMDD`)
- A single colon (`:`) separates the date from the hash
- The hash must be exactly 16 lowercase hexadecimal characters (`[0-9a-f]`)
- Everything after a `#` character (after the hash) is treated as a comment and ignored — this is useful for adding a human-readable note about which quote the hash refers to
- Lines that are blank or start with `#` are ignored entirely (full-line comments)
- If any line fails validation, a `ClickException` is raised and the entire quotemap is rejected; the web server falls back to the seeded RNG

**Example file:**
```
# Quotemap for March 2026
20260319: a1b2c3d4e5f67890  # "The only way to do great work..." - Steve Jobs
20260320: 25382c2519fb23bd  # "Be yourself; everyone else is taken." - Oscar Wilde
20260401: 9f8e7d6c5b4a3210  # April Fools quote

# Quotemap for April 2026
20260401: 9f8e7d6c5b4a3210  # April Fools quote
20260415: 1a2b3c4d5e6f7890  # Tax day quote
```

## Changes

### 1. New `quotemap_file` setting in config ([jotquote/api.py](jotquote/api.py))

- Add `quotemap_file` to the default config created in `get_config()` (after line 383), with an empty string default (disabled by default).
- Example in settings.conf: `quotemap_file = ~/.jotquote/quotemap.txt`

### 2. New quotemap parsing function ([jotquote/api.py](jotquote/api.py))

Add a function `read_quotemap(filename)` that parses a quotemap file per the syntax described above. The parameter name `filename` matches the convention used by `read_quotes(filename)`. Implementation details:
- Returns a `dict[str, str]` mapping `"YYYYMMDD"` → `"<16-char hash>"`
- Skips blank lines and full-line comments (lines starting with `#`)
- For data lines: strip inline comments (everything after `#` following the hash), then validate strictly:
  - Split on `:` — must produce exactly 2 parts
  - Date part (left of `:`): stripped, must be exactly 8 characters, all digits
  - Hash part (right of `:`): stripped (after removing inline comment), must be exactly 16 characters, all lowercase hex (`[0-9a-f]`)
  - If **any** check fails on **any** line: raise a `click.ClickException` with a message including the line number and the problematic content (e.g., `"quotemap line 3: invalid date '2026031X'"`)
- Raises `click.ClickException` if the file does not exist

### 3. Remove `/tags` route ([jotquote/web.py](jotquote/web.py))

- Delete the `/tags` route and `tagspage()` function (lines 45-47)
- Remove the `settags` parameter from `showpage()` and all associated logic (the `hashstring`, `show_tags` template variable, etc.)
- Remove `show_tags` handling from [quote.html](jotquote/templates/quote.html) (the tags display section, EDIT TAGS button, settag command div)

### 4. Add `/<date>` route ([jotquote/web.py](jotquote/web.py))

**New route with optional date parameter:**
- Add `@app.route('/<date>')` alongside the existing `/` route
- The `date` parameter is a string in `YYYYMMDD` format
- Validate: must be exactly 8 digits; if invalid, return 404 via `abort(404)`
- Both `/` and `/<date>` call `showpage()` with an optional `date_path_param` parameter

**Updated `showpage()` logic:**
- Read `quotemap_file` path from config via `config[api.APP_NAME].get('quotemap_file', '')`
- If quotemap_file is configured (non-empty), call `api.read_quotemap(quotemap_file)` (passing the path as `filename`) to load mappings
- Determine the lookup date: use `date_path_param` if provided, otherwise today's date formatted as `YYYYMMDD`
- If the lookup date exists in the quotemap dict:
  - Find the quote by hash using `api.get_first_match(quotes, hash_arg=hash_value)`
  - If found, use that quote instead of the RNG-selected one
  - If the hash doesn't match any quote, log a warning and fall back to RNG
  - Set `permalink = f"/{lookup_date}"` when serving from `/` (today's quotemap hit); set `permalink = None` when already on a `/<date>` URL
  - When `date_path_param` is provided, format `date1` from the override date instead of `now`
- If not in quotemap or quotemap not configured, fall back to existing RNG behavior with `permalink = None`
- **Error handling**: Wrap the `api.read_quotemap()` call in a try/except for `click.ClickException`. If caught, log the error and fall back to seeded RNG as if no quotemap was configured.

**Cache considerations:**
- When serving a quotemap-based quote via `/<date>`, the content is static so `max_age` can be the full `cap_minutes * 60` (no midnight constraint needed)
- For `/` with quotemap hit for today, keep existing midnight-based caching

### 5. Permalink display in template ([jotquote/templates/quote.html](jotquote/templates/quote.html))

- Pass new template variable `permalink` (a URL string or `None`)
- Display a small permalink link beneath the bottom horizontal rule, inside the flex row alongside the date:
  ```html
  {% if permalink %}
  <span class="permalink"><a href="{{ permalink }}">permalink</a></span>
  {% endif %}
  ```
- CSS class `.permalink`: 75% font size, color `#999999`, no text-decoration on the link

### 6. Update [README.md](README.md)

Add a new section "Quotemap" after the "Starting the web server" section:
- Purpose: manually assign specific quotes to specific dates
- settings.conf configuration: `quotemap_file = ~/.jotquote/quotemap.txt`
- File format referencing the syntax (with inline comment example):
  ```
  # My quote schedule
  20260319: a1b2c3d4e5f67890  # "The only way to do great work..." - Steve Jobs
  20260320: 25382c2519fb23bd  # "Be yourself..." - Oscar Wilde
  ```
- How to find quote hashes: `jotquote list` with the hash shown by `-s`
- Date URL: `http://host:port/YYYYMMDD` to view a specific date's quote
- Permalink: automatically shown when today's quote comes from the quotemap

### 7. Update [CLAUDE.md](CLAUDE.md)

Add to the Architecture / Key design details section:
- **Quotemap**: optional `quotemap_file` config property pointing to a date-to-hash mapping file. Format: `YYYYMMDD: <16-char-hash>`, one per line. When configured, the web server checks this file before falling back to the seeded RNG. The `/<date>` route serves a specific date's mapped quote.

### 8. Tests

#### Unit tests for `read_quotemap()` — new file [tests/quotemap_test.py](tests/quotemap_test.py)
- `test_read_quotemap_valid` — valid file with multiple entries returns correct dict
- `test_read_quotemap_empty_file` — empty file returns empty dict
- `test_read_quotemap_comments_and_blanks` — comments (`#`) and blank lines are skipped
- `test_read_quotemap_missing_file` — nonexistent path raises ClickException
- `test_read_quotemap_empty_path` — empty string path returns empty dict
- `test_read_quotemap_invalid_date` — line with non-digit date chars raises ClickException
- `test_read_quotemap_invalid_hash_length` — hash not 16 chars raises ClickException
- `test_read_quotemap_invalid_hash_chars` — hash with non-hex chars raises ClickException
- `test_read_quotemap_no_colon` — line without colon separator raises ClickException
- `test_read_quotemap_inline_comments` — lines with `# comment` after the hash are parsed correctly, comment stripped
- `test_read_quotemap_mixed_valid_invalid` — any invalid line causes ClickException (entire file rejected)

#### Unit tests for web routes — add to [tests/web_test.py](tests/web_test.py)
- `test_date_route_with_quotemap` — `/<date>` with quotemap entry returns the mapped quote
- `test_date_route_without_quotemap` — `/<date>` with no quotemap falls back to RNG
- `test_date_route_invalid_format` — non-8-digit date returns 404
- `test_root_with_quotemap_today` — `/` with today in quotemap returns mapped quote and permalink
- `test_root_without_quotemap` — `/` without quotemap returns RNG quote, no permalink
- `test_date_route_no_permalink` — `/<date>` does not show permalink (already on permalink)
- `test_quotemap_hash_not_found` — quotemap entry with hash that doesn't match any quote falls back to RNG
- `test_tags_route_removed` — `/tags` returns 404

#### Integration tests — add to [tests/web_integration_test.py](tests/web_integration_test.py)
- `test_quotemap_date_route` — start webserver with quotemap configured, request `/<date>`, verify mapped quote appears in response HTML
- `test_quotemap_root_permalink` — start webserver with quotemap containing today's date, request `/`, verify permalink link appears

These integration tests follow the existing pattern: use `_make_env` with `quotemap_file` extra prop, create a quotemap file in `tmp_path`, start subprocess, poll with `wait_for_server`, make HTTP requests, assert on response body.

## Files modified
- [jotquote/api.py](jotquote/api.py) — added `read_quotemap()`, updated `get_config()` default
- [jotquote/web.py](jotquote/web.py) — removed `/tags` route, added `/<date>` route, updated `showpage()` logic
- [jotquote/templates/quote.html](jotquote/templates/quote.html) — removed tags/settag markup, added permalink
- [tests/web_test.py](tests/web_test.py) — removed `test_page_tags`, added new quotemap web tests
- [tests/web_integration_test.py](tests/web_integration_test.py) — added quotemap integration tests
- [README.md](README.md) — added quotemap section
- [CLAUDE.md](CLAUDE.md) — updated architecture

## Files created
- [tests/quotemap_test.py](tests/quotemap_test.py) — unit tests for `read_quotemap()`
