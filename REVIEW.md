# jotquote Review App

The review app (`web_review.py`) is a Flask web application for reviewing and tagging your quote collection. It displays the quote of the day alongside the full list of tags in your quote file, letting you update the quote's tags directly from the browser.

---

> **Security Warning**
>
> This app has **no authentication or access control**. Anyone who can reach the server can read your quote file and modify tags. **Only run this app bound to `127.0.0.1` (localhost).** Never expose it on a network interface accessible to other machines.
>
> The Flask development server (used below) binds to `127.0.0.1` by default, which is safe for local use.

---

## Features

- Displays the deterministic quote of the day (same quote shown all day, matching `jotquote webserver`)
- Lists all tags from your quote file in a two-column checkbox layout
- Tags already assigned to the current quote are pre-checked
- Check or uncheck any tag and click **Save Tags** to update the quote file

## Prerequisites

The review app requires Flask, which is included in the jotquote development dependencies:

```bash
uv sync --group dev
```

## Launching the App

```bash
flask --app jotquote/web_review.py run
```

The server starts on `http://127.0.0.1:5000` by default. Open that URL in your browser.

To use a different port:

```bash
flask --app jotquote/web_review.py run --port 8080
```

## Configuration

The review app reads the same `~/.jotquote/settings.conf` file used by the CLI and the main web server. The relevant settings are:

| Property | Description | Default |
|---|---|---|
| `quote_file` | Path to your quote file | `~/.jotquote/quotes.txt` |
| `web_page_title` | HTML page title shown in the browser tab | `jotquote` |
| `web_show_stars` | Show star rating derived from star tags | `false` |

## Saving Tag Changes

1. The page shows all tags in your quote file as checkboxes
2. Tags currently on today's quote are pre-checked
3. Check or uncheck tags as desired
4. Click **Save Tags** — the quote file is updated atomically and the page reloads
