# jotquote Documentation

## settings.conf

The `settings.conf` file lives at `~/.jotquote/settings.conf` and controls jotquote's behavior. It is created automatically on first run with default values.

| Property | Default | Description |
|---|---|---|
| `quote_file` | `~/.jotquote/quotes.txt` | Path to the quote file |
| `line_separator` | `platform` | Line ending style: `platform`, `unix`, or `windows` |
| `show_author_count` | `false` | If `true`, shows the number of quotes per author on the web server |
| `quotemap_file` | _(empty)_ | Path to an optional quotemap file (see [QUOTEMAP.md](QUOTEMAP.md)) |
| `web_port` | `5544` | Port the web server listens on |
| `web_ip` | `127.0.0.1` | IP address the web server binds to |
| `web_cache_minutes` | `240` | How long (in minutes) the web server caches the quote list after a file change |
| `web_page_title` | `jotquote` | HTML page title shown in the browser tab |
| `web_show_stars` | `false` | If `true`, shows star ratings on the web server |
| `web_light_foreground_color` | `#000000` | Text color in light mode |
| `web_light_background_color` | `#ffffff` | Background color in light mode |
| `web_dark_foreground_color` | `#ffffff` | Text color in dark mode |
| `web_dark_background_color` | `#000000` | Background color in dark mode |
| `lint_enabled_checks` | _(all checks)_ | Comma-separated list of lint checks to run by default. If empty or absent, all checks run. Valid values: `ascii`, `smart-quotes`, `smart-dashes`, `spelling`, `double-spaces`, `quote-too-long`, `no-tags`, `no-author`, `author-antipatterns`, `multiple-stars`, `required-tag-group` |
| `lint_max_quote_length` | `0` | Maximum allowed quote length in characters; `0` disables the check. Used by the `quote-too-long` lint check |
| `lint_spell_ignore` | _(empty)_ | Comma-separated list of words the spell checker should treat as correctly spelled. The spelling check applies to quote text only. |
| `lint_author_antipattern_regex` | _(empty)_ | Comma-separated list of regex patterns; authors matching any pattern are flagged by the `author-antipatterns` lint check |
| `lint_required_group_<name>` | _(empty)_ | Defines a named group of required tags; a quote must have at least one tag from this group or it is flagged by the `required-tag-group` check. `<name>` is any identifier (e.g. `stars`, `visibility`). Add multiple properties with different names to define multiple groups. Example: `lint_required_group_stars = 1star, 2stars, 3stars, 4stars, 5stars` |

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
