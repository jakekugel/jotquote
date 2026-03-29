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

Use `--no-lint` to skip lint checks for a single invocation (overrides `lint_on_add` in settings.conf).

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

Available checks: `ascii`, `smart-quotes`, `smart-dashes`, `double-spaces`, `quote-too-long`, `no-tags`, `no-author`, `author-antipatterns`, `required-tag-group`.

---

### `quotemap rebuild`

Auto-generates a quotemap for the next 10 years (3652 days by default) with even quote distribution. Prints to stdout; redirect to a file to save.

```bash
$ jotquote quotemap rebuild ~/.jotquote/quotes.txt quotemap_new.txt
```

Use `--oldquotemap` to preserve past entries and sticky future entries from an existing quotemap:

```bash
$ jotquote quotemap rebuild --oldquotemap ~/.jotquote/quotemap.txt ~/.jotquote/quotes.txt quotemap_new.txt
```

Use `--days` to control how many days are generated:

```bash
$ jotquote quotemap rebuild --days 365 ~/.jotquote/quotes.txt quotemap_new.txt
```

See the [Quotemap](#quotemap) section for full details.

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

Start the web server with `jotquote webserver`. It serves a quote of the day at `http://<web_ip>:<web_port>/`.

### Daily quote algorithm

The daily quote is selected using a seeded random number generator. The seed is derived from the number of days since 2016-01-01, so the same quote is shown for the entire day — and the quote changes at midnight. This matches what `jotquote today` shows on the command line.

When a quotemap is configured, the quotemap takes precedence over the seeded algorithm for dates that have an entry. See the [Quotemap](#quotemap) section.

### Theming

The web server supports light and dark mode. Colors are controlled via `settings.conf` properties (`web_light_foreground_color`, `web_light_background_color`, `web_dark_foreground_color`, `web_dark_background_color`). See the [settings.conf](#settingsconf) section for defaults.

---

## Quotemap

The quotemap file assigns specific quotes to specific dates for display by the jotquote web server. When configured, the web server checks the quotemap before falling back to the default seeded random selection. The quotemap also enables permalink URLs (`/<YYYYMMDD>`) so that a specific date's quote can be shared and revisited.

### File Format

The quotemap file is a plain text file (UTF-8) where each line maps a date to a quote hash:

```
YYYYMMDD: <16-char-hex-hash>  # optional comment
```

- The date must be exactly 8 digits (`YYYYMMDD`)
- The hash must be exactly 16 lowercase hexadecimal characters
- Everything after `#` on a data line is treated as a comment and ignored
- Blank lines and lines starting with `#` are ignored
- If any line fails validation, the entire file is rejected

Example:

```
# Quotes for March 2026
20260319: a1b2c3d4e5f67890  # "The only way to do great work..." - Steve Jobs
20260320: 25382c2519fb23bd  # "Be yourself; everyone else is taken." - Oscar Wilde

# Quotes for April 2026
20260401: 9f8e7d6c5b4a3210  # April Fools quote
```

To find a quote's hash, use `jotquote list -l` or `jotquote list -s <hash>`.

### Configuration

Add the `quotemap_file` property to `~/.jotquote/settings.conf`:

```ini
[jotquote]
quotemap_file = ~/.jotquote/quotemap.txt
```

### Web Server Behavior

- `/` — If today's date has an entry in the quotemap, that quote is shown along with a permalink. Otherwise, the default seeded random selection is used.
- `/<YYYYMMDD>` — Shows the quote mapped to that date. Returns 404 if the date is not in the quotemap.

### Rebuild Command

The `jotquote quotemap rebuild` command auto-generates a quotemap for the next 10 years, cycling through quotes with even distribution.

#### Usage

```bash
jotquote quotemap rebuild <quotefile> <newquotemap>
```

The command writes the rebuilt quotemap to `<newquotemap>` (the file must not already exist).

Use `--oldquotemap` to read an existing quotemap file (preserving past and sticky entries):

```bash
jotquote quotemap rebuild --oldquotemap quotemap.txt quotes.txt quotemap_new.txt
```

Use `--days` to control how many days into the future are generated (default: 3652, about 10 years):

```bash
jotquote quotemap rebuild --days 365 quotes.txt quotemap_new.txt
```

#### How It Works

1. Reads all quotes from the quote file
2. If `--oldquotemap` is given, reads existing entries:
   - **Past/today entries** are preserved verbatim
   - **Future sticky entries** (lines with `# Sticky:` in the comment) are preserved
   - All other future entries are discarded and regenerated
3. Validates that every preserved hash maps to a quote in the quote file
4. For each future date without a sticky entry, assigns a quote using even distribution:
   - Tracks how many times each quote hash has been used
   - Selects from the least-used quotes
   - Uses a deterministic seed so rebuilds produce the same output

#### Sticky Entries

To mark an entry as sticky (so it won't be overwritten during a rebuild), add `# Sticky:` to the inline comment:

```
20260401: 9f8e7d6c5b4a3210  # Sticky: April Fools quote
```

**Auto-sticky for new quotes:** When a quote's hash has never appeared in the old quotemap file, the rebuild automatically marks its first occurrence as Sticky. This preserves the debut date for newly added quotes across future rebuilds. Only the first occurrence is marked; subsequent assignments of the same hash are normal.

#### Example Workflow

```bash
# Generate a fresh quotemap
jotquote quotemap rebuild --oldquotemap ~/.jotquote/quotemap.txt \
    ~/.jotquote/quotes.txt /tmp/quotemap_new.txt

# Review the output
less /tmp/quotemap_new.txt

# Replace the old quotemap
cp /tmp/quotemap_new.txt ~/.jotquote/quotemap.txt
```

---

## Review App

The review app (`web_review.py`) is a Flask web server intended to help manage tags on quotes. It displays the quote of the day alongside the full list of tags in your quote file, letting you update the quote's tags directly from the browser.

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
waitress-serve --host 127.0.0.1 --port 5000 jotquote.web_review:app
```

If you are running from a local development checkout with uv:

```bash
uv run waitress-serve --host 127.0.0.1 --port 5000 jotquote.web_review:app
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

---

## settings.conf

The `settings.conf` file lives at `~/.jotquote/settings.conf` and controls jotquote's behavior. It is created automatically on first run with default values. Properties are organized into three sections: `[general]`, `[lint]`, and `[web]`.

### `[general]` section

General configuration properties:

| Property | Default | Description |
|---|---|---|
| `quote_file` | `~/.jotquote/quotes.txt` | Path to the quote file |
| `line_separator` | `platform` | Line ending style: `platform`, `unix`, or `windows` |
| `quotemap_file` | _(empty)_ | Path to an optional quotemap file (see [Quotemap](#quotemap)) |
| `web_page_title` | `jotquote` | HTML page title shown in the browser tab |

### `[lint]` section

Lint configuration properties:

| Property | Default | Description |
|---|---|---|
| `lint_enabled_checks` | _(all checks)_ | Comma-separated list of lint checks to run by default. If empty or absent, all checks run. Valid values: `ascii`, `smart-quotes`, `smart-dashes`, `double-spaces`, `quote-too-long`, `no-tags`, `no-author`, `author-antipatterns`, `required-tag-group` |
| `lint_max_quote_length` | `0` | Maximum allowed quote length in characters; `0` disables the check. Used by the `quote-too-long` lint check |
| `lint_author_antipattern_regex` | _(empty)_ | Comma-separated list of regex patterns; authors matching any pattern are flagged by the `author-antipatterns` lint check |
| `lint_on_add` | `false` | If `true`, lint checks are run automatically when adding a quote via the `add` command. Use `--no-lint` to skip lint for a single invocation regardless of this setting. |
| `lint_required_group_<name>` | _(empty)_ | Defines a named group of required tags; a quote must have at least one tag from this group or it is flagged by the `required-tag-group` check. `<name>` is any identifier (e.g. `stars`, `visibility`). Add multiple properties with different names to define multiple groups. Example: `lint_required_group_stars = 1star, 2stars, 3stars, 4stars, 5stars` |

### `[web]` section

Web server configuration properties:

| Property | Default | Description |
|---|---|---|
| `web_port` | `5544` | Port the web server listens on |
| `web_ip` | `127.0.0.1` | IP address the web server binds to |
| `web_cache_minutes` | `240` | How long (in minutes) the web server caches the quote list after a file change |
| `web_show_stars` | `false` | If `true`, shows star ratings on the web server |
| `web_light_foreground_color` | `#000000` | Text color in light mode |
| `web_light_background_color` | `#ffffff` | Background color in light mode |
| `web_dark_foreground_color` | `#ffffff` | Text color in dark mode |
| `web_dark_background_color` | `#000000` | Background color in dark mode |

### Backward Compatibility

The configuration system automatically supports the old single-section `[jotquote]` format for backward compatibility. When loading an old-format `settings.conf`, a warning is displayed to encourage migration to the new three-section format. All properties continue to work as expected.

## Environment Variables

| Variable | Description |
|---|---|
| `JOTQUOTE_CONFIG` | Path to the `settings.conf` file. Overrides the default location (`~/.jotquote/settings.conf`). Useful for running jotquote with an alternate configuration, for example during development or in CI. Accepts absolute or relative paths; relative paths are interpreted relative to the current working directory. |

**Example** — restore the original dark color scheme:

```ini
[jotquote]
web_dark_foreground_color = #e8e8e8
web_dark_background_color = #1a1a1a
```
