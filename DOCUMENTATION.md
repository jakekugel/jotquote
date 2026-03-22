# jotquote Documentation

## settings.conf

The `settings.conf` file lives at `~/.jotquote/settings.conf` and controls jotquote's behavior. It is created automatically on first run with default values.

| Property | Default | Description |
|---|---|---|
| `quote_file` | `~/.jotquote/quotes.txt` | Path to the quote file |
| `line_separator` | `platform` | Line ending style: `platform`, `unix`, or `windows` |
| `ascii_only` | `false` | If `true`, rejects quotes containing non-ASCII characters |
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

**Example** — restore the original dark color scheme:

```ini
[jotquote]
web_dark_foreground_color = #e8e8e8
web_dark_background_color = #1a1a1a
```
