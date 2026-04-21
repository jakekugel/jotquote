# Update USER_DOCUMENTATION.md — settings.conf reorganization

## Context

[USER_DOCUMENTATION.md](../USER_DOCUMENTATION.md) has a `settings.conf` reference table buried near the bottom of the file (after the Review App section), uses outdated language for `expiration_seconds`, still documents a property (`show_stars`) the user wants removed, and carries a deprecated "Legacy format" note for the old single-section `[jotquote]` layout. The goal is to reshuffle the section to sit immediately after the Web Server description (where readers first encounter web settings), drop dead/deprecated content, and sharpen one wrong description — with the property list verified against the actual code.

## Codebase audit

Every property currently documented in the three `settings.conf` tables was traced to a real read in the code. Nothing is missing and nothing is phantom. Key confirmations:

- **`[general]`** — `quote_file` ([jotquote/api/config.py](../jotquote/api/config.py)), `line_separator` ([jotquote/api/store.py](../jotquote/api/store.py)), `show_author_count` ([jotquote/cli.py](../jotquote/cli.py)). All three documented.
- **`[lint]`** — `enabled_checks` ([jotquote/web/helpers.py](../jotquote/web/helpers.py)), `max_quote_length` ([jotquote/api/lint.py](../jotquote/api/lint.py)), `author_antipattern_regex`, `lint_on_add`, `required_group_<name>` (dynamic prefix). All five documented.
- **`[web]`** — `port`, `ip`, `editor_port`, `editor_ip`, `expiration_seconds`, `page_title`, `show_stars`, `mode`, `about`, `header_provider_extension`, `quote_resolver_extension`, and the four `*_foreground_color` / `*_background_color` keys. All present in code; all documented.
- **`expiration_seconds` actual behavior** ([jotquote/web/viewer.py](../jotquote/web/viewer.py)): read as an int, capped by seconds-until-midnight in `daily` mode, then stored on `g.expires_at` as an ISO-8601 timestamp that the template passes to the browser. The browser uses it to schedule the auto-refresh (plus a 60–120 s random offset). It is **also** forwarded to an optional `header_provider_extension`, which may or may not turn it into a `Cache-Control: max-age` header. The current doc wording ("caches the quote list after a file change") is simply wrong.
- **`show_stars` is alive**, not dead. The user is choosing to drop it from the docs anyway — the property will keep working in `settings.conf`, it just won't be documented.
- **Legacy `[jotquote]` migration code is still active** and prints a deprecation warning. Removing the doc section does **not** remove the migration code — the user is signalling the format is stale enough that we no longer advertise it.

## Changes

All edits are confined to [USER_DOCUMENTATION.md](../USER_DOCUMENTATION.md).

### 1. Move `settings.conf` + `Environment Variables` sections up

Source range: the `## settings.conf` heading through the end of the file (including `## Environment Variables` and the closing example).

Destination: immediately after the `## Web Server` section ends (before `## Quote Resolver`).

Everything from `## settings.conf` through the final `dark_background_color = #1a1a1a` example block moves together as one unit. The later sections (`## Quote Resolver`, `## Header Provider`, `## Review App`) shift down unchanged.

### 2. Rewrite `expiration_seconds` description

Current:
> How long (in seconds) the web server caches the quote list after a file change

New:
> How long (in seconds) before the web page auto-refreshes in the browser. In `daily` mode, this is capped so the refresh happens no later than midnight.

### 3. Reorder the `[web]` table so `mode` is the first row

Move the `mode` row to the top of the `[web]` table, directly under the header row. `mode` determines whether most of the other `[web]` settings (permalinks, expiration cap, resolver) apply at all, so it belongs at the top.

### 4. Remove `show_stars` row

Delete the `show_stars` row from the `[web]` table. The property continues to function in the code; it is simply undocumented after this change.

### 5. Delete the `Legacy format` section

Delete the `### Legacy format` subsection in full. The in-code migration + deprecation warning continue to handle any user still on the old format.

## Out-of-scope / judgment calls

- **Review App sub-table** still lists properties under their legacy prefixed names (`web_page_title`, `web_show_stars`). Not touched — user declined the adjacent cleanup.
- **Auto-refresh paragraph** describes the same mechanism as the revised `expiration_seconds` description, using slightly different language. Not touched — user did not request a rewrite.

## Verification

1. Open the rendered doc in a Markdown previewer; confirm the order is:
   `CLI Commands → Quote File Format → Web Server → settings.conf → Environment Variables → Quote Resolver → Header Provider → Review App`.
2. Grep the final file for `show_stars` (main table), `Legacy format`, `caches the quote list` — all three should return zero matches.
3. Confirm the `[web]` table's first data row is `mode`.
4. Confirm `expiration_seconds` description no longer mentions "file change".
5. `uv run pytest` — must still pass (no code changes; verifies nothing inadvertently relied on doc text).
