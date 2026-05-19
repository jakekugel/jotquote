# jotquote Documentation

## CLI Commands

### `jotquote` (no subcommand)

Displays a random quote from the quote file.

```bash
$ jotquote
The best way out is always through. - Robert Frost
```

Use `--quotefile PATH` to point to a specific quote file, overriding settings.conf:

```bash
$ jotquote --quotefile ~/my-other-quotes.txt
```

---

### `add`

Adds a new quote to the quote file.

```bash
$ jotquote add "The larger the island of knowledge, the longer the shoreline of wonder. - James Madison"
1 quote added for total of 639 quotes.
```

By default, the simple format is used: `<quote> - <author> [(publication)]`. The hyphen is used to split the quote from the author.

Use `-e` / `--extended` to supply a quote in the same pipe-delimited format used in the quote file:

```bash
$ jotquote add -e "The best way out is always through. | Robert Frost | A Servant to Servants | motivational"
```

Use `--no-lint` to skip lint checks for a single invocation (overrides `lint_on_add` in the `[lint]` section of settings.conf).

---

### `list`

Lists quotes from the quote file, optionally filtered.

```bash
# List all quotes
$ jotquote list

# Filter by tag
$ jotquote list -t motivational

# Filter by keyword (searches quote, author, and publication)
$ jotquote list -k Einstein

# Long output (includes publication, tags, and hash)
$ jotquote list -l

# Show quote at a specific line number
$ jotquote list -n 42

# Show quote by hash
$ jotquote list -s a1b2c3d4e5f67890

# Output in pipe-delimited format
$ jotquote list -e
```

---

### `random`

Displays a random quote, optionally filtered by tag or keyword.

```bash
$ jotquote random
$ jotquote random -t motivational
$ jotquote random -k wisdom
```

---

### `today`

Displays the deterministic quote of the day. Seeds the RNG with the current date so the same quote is shown all day (matching the web server's daily quote).

```bash
$ jotquote today
```

---

### `showalltags`

Lists every tag used anywhere in the quote file.

```bash
$ jotquote showalltags
```

---

### `settags`

Replaces the tags on a specific quote. Identify the quote by line number (`-n`) or hash (`-s`).

```bash
# Replace tags using hash
$ jotquote settags -s a1b2c3d4e5f67890 "motivational,life"

# Replace tags using line number
$ jotquote settags -n 42 "funny,historical"
```

---

### `info`

Shows the location of the config file and quote file, plus the quote count.

```bash
$ jotquote info
Config file: /home/user/.jotquote/settings.conf
Quote file:  /home/user/.jotquote/quotes.txt
Quotes:      639
```

---

### `webserver`

Starts the built-in web server to display a quote of the day. Host and port are read from `settings.conf` (defaults: `127.0.0.1:5544`).

```bash
$ jotquote webserver
```

---

### `webeditor`

Starts a local web server for editing quotes. Displays one quote at a time with editable fields for the quote text, author, publication, and tags. Lint issues for the displayed quote are shown inline. Host and port are read from `settings.conf` (`editor_ip` and `editor_port`; defaults: `127.0.0.1:5545`).

```bash
$ jotquote webeditor
```

> **Security Warning**
>
> The editor has **no authentication or access control**. Anyone who can reach the server can read and modify your quote file. **Only run this server bound to `127.0.0.1` (localhost).** Never expose it on a network interface accessible to other machines.

---

### `lint`

Checks the quote file for quality issues. By default, the checks configured in `lint_enabled_checks` are used; if that property is absent, all checks run.

```bash
# Run configured checks
$ jotquote lint

# Run only specific checks
$ jotquote lint --select smart-quotes,double-spaces

# Run all configured checks except one
$ jotquote lint --ignore no-tags

# Auto-fix issues that can be corrected safely
$ jotquote lint --fix
```

Available checks: `smart-quotes`, `smart-dashes`, `unicode-ellipsis`, `double-spaces`, `quote-too-long`, `no-tags`, `no-author`, `required-tag-group`, `duplicate-hash`.

The `unicode-ellipsis` check flags the Unicode horizontal ellipsis character (`…`, U+2026) in any text field. With `--fix`, each occurrence is replaced with three ASCII periods (`...`).

The `duplicate-hash` check flags any quote whose fuzzy hash (the first letter of each word, MD5-hashed) collides with another quote in the file. This catches near-duplicates that differ only in punctuation, casing, or whitespace, as well as the rare unrelated quote that happens to share the same word-initial-letter sequence.

---

---

## Quote File Format

jotquote stores quotes in a plain text file (UTF-8), one quote per line, using a pipe-delimited format:

```
<quote> | <author> | <publication> | <tag1, tag2, ...>
```

Example:

```
The best way out is always through. | Robert Frost | A Servant to Servants | motivational, poetry
```

- **quote** — the quote text (required)
- **author** — the person who said or wrote it (required)
- **publication** — the source publication (optional, leave blank)
- **tags** — comma-separated list of tags (optional, leave blank)

The file can be edited with any plain text editor. Use `jotquote info` to find the file location.

### Two add formats

The `add` command accepts two input formats:

- **Simple** (default): `<quote> - <author> [(publication)]` — the hyphen separates the quote from the author
- **Extended** (`-e` flag): full pipe-delimited format, same as the quote file

---

## Web Server

Start the web server with `jotquote webserver`. It serves a quote of the day at `http://<ip>:<port>/` (configured in the `[web]` section of settings.conf).

### Daily quote algorithm

The daily quote is selected using a seeded random number generator. The seed is derived from the number of days since 2016-01-01, so the same quote is shown for the entire day — and the quote changes at midnight. This matches what `jotquote today` shows on the command line.

When a quote resolver is configured, the resolver takes precedence over the seeded algorithm for dates that it resolves. See the [Quote Resolver](#quote-resolver) section.

### Theming

The web server supports light and dark mode. Colors are controlled via properties in the `[web]` section of `settings.conf` (`light_foreground_color`, `light_background_color`, `dark_foreground_color`, `dark_background_color`). See the [settings.conf](#settingsconf) section for defaults.

### Auto-refresh

The web server instructs the browser to automatically reload the page after the HTTP cache expires. The server passes the cache expiration time (UTC ISO 8601) to the browser, which adds a random delay of 60–120 seconds before reloading to ensure the cache has expired. On browsers that support the View Transitions API, the reload includes a smooth cross-fade animation. Date permalink pages (`/<YYYYMMDD>`) do not auto-refresh.

### Mode

The `mode` property in the `[web]` section controls how quotes are selected:

- **`daily`** (default): A deterministic daily quote is selected using a seeded random number generator. The same quote is shown all day and changes at midnight. A quote resolver (if configured) takes precedence for mapped dates.
- **`random`**: A truly random quote is selected on each page load. The quote resolver is bypassed and permalinks are disabled. The cache expiration is based solely on `expiration_seconds` without the midnight cap.

---

## settings.conf

The `settings.conf` file lives at `~/.jotquote/settings.conf` and controls jotquote's behavior. It is created automatically on first run with default values. Properties are organized into three sections: `[general]`, `[lint]`, and `[web]`.

### `[general]` section

| Property | Default | Description |
|---|---|---|
| `quote_file` | `~/.jotquote/quotes.txt` | Path to the quote file |
| `line_separator` | `platform` | Line ending style: `platform`, `unix`, or `windows` |
| `show_author_count` | `false` | If `true`, shows the number of quotes per author on the web server |
| `timezone` | _(empty)_ | IANA timezone name (e.g. `America/Chicago`) used to determine "today" for the daily-quote rollover. When empty, the system's local time is used. Invalid names raise a `ConfigError` at first use. On Linux/macOS, IANA data ships with the OS; on Windows it is pulled in via the `tzdata` dependency. |

### `[lint]` section

| Property | Default | Description |
|---|---|---|
| `enabled_checks` | _(all checks)_ | Comma-separated list of lint checks to run by default. If empty or absent, all checks run. Valid values: `smart-quotes`, `smart-dashes`, `unicode-ellipsis`, `double-spaces`, `quote-too-long`, `no-tags`, `no-author`, `required-tag-group`, `duplicate-hash` |
| `max_quote_length` | `0` | Maximum allowed quote length in characters; `0` disables the check. Used by the `quote-too-long` lint check |
| `lint_on_add` | `false` | If `true`, lint checks are run automatically when adding a quote via the `add` command. Use `--no-lint` to skip lint for a single invocation regardless of this setting. |
| `required_group_<name>` | _(empty)_ | Defines a named group of required tags; a quote must have at least one tag from this group or it is flagged by the `required-tag-group` check. `<name>` is any identifier (e.g. `stars`, `visibility`). Add multiple properties with different names to define multiple groups. Example: `required_group_stars = 1star, 2stars, 3stars, 4stars, 5stars` |

### `[web]` section

| Property | Default | Description |
|---|---|---|
| `mode` | `daily` | Quote selection mode. `daily` shows a deterministic daily quote (changes at local midnight — see `[general].timezone`). `random` shows a truly random quote on each page load, disabling the permalink feature. |
| `about_content_provider_extension` | _(empty)_ | Dotted Python module path for an about content provider (see [About Content Provider](#about-content-provider)) |
| `header_provider_extension` | _(empty)_ | Dotted Python module path for a header provider (see [Header Provider](#header-provider)) |
| `quote_resolver_extension` | _(empty)_ | Dotted Python module path for a quote resolver (see [Quote Resolver](#quote-resolver)) |
| `port` | `5544` | Port the web server (`jotquote webserver`) listens on |
| `ip` | `127.0.0.1` | IP address the web server (`jotquote webserver`) binds to |
| `editor_port` | `5545` | Port the web editor (`jotquote webeditor`) listens on |
| `editor_ip` | `127.0.0.1` | IP address the web editor (`jotquote webeditor`) binds to |
| `expiration_seconds` | `14400` | How long (in seconds) before the web page auto-refreshes in the browser. In `daily` mode, this is capped so the refresh happens no later than midnight |
| `favicon_file` | _(empty)_ | Path to a custom favicon (`.ico`, `.svg`, or `.png`) served by both the viewer and the editor. Absolute paths are used as-is; relative paths are resolved against the directory containing `settings.conf`. When empty or the file is missing, the bundled default favicon is served. |
| `page_title` | `jotquote` | HTML page title shown in the browser tab |
| `light_foreground_color` | `#000000` | Text color in light mode |
| `light_background_color` | `#ffffff` | Background color in light mode |
| `dark_foreground_color` | `#ffffff` | Text color in dark mode |
| `dark_background_color` | `#000000` | Background color in dark mode |
| `about` | _(empty)_ | Text displayed on the `/about` page. If empty, the `/about` route returns 404. When set, an `@` button appears on the quote page linking to the about page. |

## Environment Variables

| Variable | Description |
|---|---|
| `JOTQUOTE_CONFIG` | Path to the `settings.conf` file. Overrides the default location (`~/.jotquote/settings.conf`). Useful for running jotquote with an alternate configuration, for example during development or in CI. Accepts absolute or relative paths; relative paths are interpreted relative to the current working directory. |

**Example** — restore the original dark color scheme:

```ini
[web]
dark_foreground_color = #e8e8e8
dark_background_color = #1a1a1a
```

---

## Quote Resolver

The quote resolver is a pluggable extension point that allows you to control which quote is displayed on a given date. When configured, the web server calls the resolver before falling back to the default seeded random selection. A resolver also enables permalink URLs (`/<YYYYMMDD>`) so that a specific date's quote can be shared and revisited.

### How It Works

A quote resolver is a Python module that you write and install. The module must define a `resolve` function with this signature:

```python
def resolve(date_str: str) -> str | None:
    """Return a 16-char MD5 hash identifying the quote, or None."""
```

- `date_str` is a date in `YYYYMMDD` format (e.g., `20260319`)
- Return a 16-character MD5 hash string to select a specific quote
- Return `None` to fall back to the default seeded random selection

To find a quote's hash, use `jotquote list -l` or `jotquote list -s <hash>`.

### Configuration

Add the `quote_resolver_extension` property to `~/.jotquote/settings.conf` with the dotted Python module path:

```ini
[web]
quote_resolver_extension = mypackage.my_resolver
```

The module must be importable by the Python environment running the web server. If you installed jotquote with `pip` or `uv`, install your resolver module into the same environment (e.g., `pip install mypackage` or `uv pip install mypackage`). If your resolver is a standalone script rather than an installed package, add its parent directory to `PYTHONPATH` before starting the server (e.g., `PYTHONPATH=/path/to/mymodules jotquote webserver`).

### Web Server Behavior

- `/` — If the resolver returns a hash for today, that quote is shown along with a permalink. If the resolver returns `None` or is not configured, the default seeded random selection is used.
- `/<YYYYMMDD>` — Calls the resolver for that date. If the resolver returns a hash, shows that quote. Returns 404 if the resolver returns `None`, is not configured, or the hash doesn't match any quote.

### Error Handling

- If the resolver module cannot be imported, an error is logged and the server falls back to seeded random selection for all requests.
- If the resolver's `resolve` function raises an exception, the error is logged and the server falls back to seeded random selection on the root route, or returns 404 on date routes.
- The resolver module is loaded once and cached for the lifetime of the server process.

---

## Header Provider

The header provider is a pluggable extension point that controls which HTTP response headers the web server applies to quote page responses. The base package does not set any cache headers by default; configure a header provider to add `Cache-Control` or other headers.

### How It Works

A header provider is a Python module that you write and install. The module must define a `get_headers` function with this signature:

```python
def get_headers(max_age: int) -> dict[str, str]:
    """Return HTTP response headers given the computed max-age value."""
```

- `max_age` is the cache duration in seconds, computed by the web server based on mode (`daily` vs `random`) and the `expiration_seconds` configuration.
- Return a dictionary mapping header names to header values.
- The returned headers are applied to every quote page response.

### Configuration

Add the `header_provider_extension` property to `~/.jotquote/settings.conf` with the dotted Python module path:

```ini
[web]
header_provider_extension = mypackage.my_headers
```

The module must be importable by the Python environment running the web server. If you installed jotquote with `pip` or `uv`, install your header provider module into the same environment. If your provider is a standalone script rather than an installed package, add its parent directory to `PYTHONPATH` before starting the server (e.g., `PYTHONPATH=/path/to/mymodules jotquote webserver`).

When `header_provider_extension` is not set, no custom HTTP headers are applied to responses.

### Example

A simple header provider that sets `Cache-Control`:

```python
def get_headers(max_age):
    return {'Cache-Control': f'public, max-age={max_age}'}
```

### Error Handling

- If the provider module cannot be imported, an error is logged and no custom headers are applied.
- If the `get_headers` function raises an exception, the error is logged and no custom headers are applied to the response.
- The provider module is loaded once and cached for the lifetime of the server process.

---

## About Content Provider

The about content provider is a pluggable extension point that lets you supply the body content of the `/about` page from a Python module instead of hardcoding it in `settings.conf`. The web server keeps owning the page chrome (styling, theme toggle, page title, footer); the extension supplies only the HTML fragment that appears inside the about-text container.

### How It Works

An about content provider is a Python module that you write and install. The module must define a `get_about_content` function with this signature:

```python
def get_about_content() -> str:
    """Return an HTML fragment to be injected as the about-page body content."""
```

- The function takes no arguments.
- Return an HTML fragment string. The fragment is injected into the built-in `about.html` template **without HTML escaping**, so the extension is responsible for returning safe HTML.

### Configuration

Add the `about_content_provider_extension` property to `~/.jotquote/settings.conf`:

```ini
[web]
about_content_provider_extension = mypackage.my_about_content
```

The module must be importable by the Python environment running the web server.

### Precedence and Fallback

- If `about_content_provider_extension` is set: the extension supplies the body content for `/about`. The `about` config property is ignored.
- If `about_content_provider_extension` is not set and `about` has a value: the built-in about template renders the text. (Note: the rendered text is now passed through `|safe`, so HTML in the `about` config property is no longer escaped. Plain text continues to work as before.)
- If neither is configured: `/about` returns 404 and the About button is hidden on the viewer page.

The About button on the viewer page appears when either `about_content_provider_extension` is configured or the `about` property is non-empty.

### Error Handling

- If the provider module cannot be imported, an error is logged and the extension is disabled for the lifetime of the server process. The `about` config property is used as a fallback.
- If `get_about_content` raises an exception, the error is logged and `/about` returns 500.
- The provider module is loaded once and cached for the lifetime of the server process.

---

## Review App

The review app (`jotquote/web/editor.py`) is a Flask web server intended to help manage tags on quotes. It displays the quote of the day alongside the full list of tags in your quote file, letting you update the quote's tags directly from the browser.

---

> **Security Warning**
>
> This app has **no authentication or access control**. Anyone who can reach the server can read your quote file and modify tags. **Only run this app bound to `127.0.0.1` (localhost).** Never expose it on a network interface accessible to other machines.
>
> The launch commands below bind to `127.0.0.1` by default, which is safe for local use.

---

### Features

- Displays the deterministic quote of the day (same quote shown all day, matching `jotquote webserver`)
- Lists all tags from your quote file in a two-column checkbox layout
- Tags already assigned to the current quote are pre-checked
- Check or uncheck any tag and click **Save Tags** to update the quote file

### Launching the App

If you installed jotquote with pip into your global Python environment:

```bash
waitress-serve --host 127.0.0.1 --port 5000 jotquote.web.editor:app
```

If you are running from a local development checkout with uv:

```bash
uv run waitress-serve --host 127.0.0.1 --port 5000 jotquote.web.editor:app
```

Then open `http://127.0.0.1:5000` in your browser.

### Configuration

The review app reads the same `~/.jotquote/settings.conf` file used by the CLI and the main web server. The relevant settings are:

| Property | Description | Default |
|---|---|---|
| `quote_file` | Path to your quote file | `~/.jotquote/quotes.txt` |
| `web_page_title` | HTML page title shown in the browser tab | `jotquote` |
| `web_show_stars` | Show star rating derived from star tags | `false` |

### Saving Tag Changes

1. The page shows all tags in your quote file as checkboxes
2. Tags currently on today's quote are pre-checked
3. Check or uncheck tags as desired
4. Click **Save Tags** — the quote file is updated atomically and the page reloads
