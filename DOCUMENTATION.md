# jotquote Documentation

## settings.conf

The `settings.conf` file lives at `~/.jotquote/settings.conf` and controls jotquote's behavior. It is created automatically on first run with default values.

### Web server color properties

These optional properties control the foreground (text) and background colors used by the web server templates in light and dark mode. If not set, the defaults are pure black/white.

| Property | Type | Default | Description |
|---|---|---|---|
| `web_light_foreground_color` | hex color | `#000000` | Text color in light mode |
| `web_light_background_color` | hex color | `#ffffff` | Background color in light mode |
| `web_dark_foreground_color` | hex color | `#ffffff` | Text color in dark mode |
| `web_dark_background_color` | hex color | `#000000` | Background color in dark mode |

**Example** — restore the original dark color scheme:

```ini
[jotquote]
web_dark_foreground_color = #e8e8e8
web_dark_background_color = #1a1a1a
```
