# Plan: `jotquote quotemap rebuild` CLI Subcommand

## Context

The quotemap file assigns quotes to specific dates for display by the web server. Rather than relying on the default random daily selection, the quotemap allows quotes to be planned in advance and also enables a permalink route (`/<YYYYMMDD>`). This new CLI subcommand auto-generates quotemap entries for the next 10 years, cycling through quotes with even distribution. It also respects "sticky" entries that should not be changed.

## `rebuild` Behavior

**Arguments:**
- `quotefile` (required) — path to the quote file
- `old_quotemapfile` (required) — path to the quotemap file (read for existing entries; created fresh if it doesn't exist)

**Output:** Prints the rebuilt quotemap to **stdout**. The user can redirect to a file with `> quotemap.txt`.

**Algorithm:**

1. Read the quote file via `api.read_quotes(quotefile)` to get all available quotes and their hashes.
2. If the quotemap file exists, read it — but we need the **raw lines** (not just the parsed dict), because we need to detect `# Sticky:` comments and preserve comment lines. We'll need a new function `read_quotemap_raw(filename)` that returns a list of `(date_str, hash_str, raw_line)` tuples plus standalone comment/blank lines.
3. Determine today's date as `YYYYMMDD`.
4. **Preserve** all entries on or before today (keep their raw lines verbatim). **Preserve sticky entries** for future dates — any line where the inline comment contains `# Sticky:` keeps its date-to-hash mapping unchanged. For all preserved entries (past + sticky), if the hash does not resolve to a quote in the quote file, raise a `ClickException` displaying the offending line.
5. For all other future dates (from tomorrow through 10 years from today), assign quotes using the even-distribution algorithm:
   - Build a usage count dict: how many times each hash appears across all dates (preserved past + sticky + newly assigned).
   - Find the minimum usage count among all quote hashes.
   - From quotes at that minimum count, randomly select one.
   - Assign it to the current date, increment its count.
   - Repeat for each date.
6. Write the output quotemap file with:
   - Monthly comment headers: `# Quotes for March 2026`
   - One data line per date: `YYYYMMDD: <hash>  # <quote text snippet> - <author>` (truncated to keep lines reasonable)
   - Sticky entries written as: `YYYYMMDD: <hash>  # Sticky: <quote text snippet> - <author>`

**Random seed:** Use `random.seed(0)` before the selection loop so rebuilds are deterministic (same input → same output), matching the project's convention in `_get_random_value()`.

## Changes

### 1. New `quotemap` command group in [jotquote/cli.py](jotquote/cli.py)

```python
@jotquote.group()
def quotemap():
    """Manage the quotemap file."""
    pass

@quotemap.command()
@click.argument('quotefile', type=click.Path(exists=True))
@click.argument('old_quotemapfile', type=click.Path())
def rebuild(quotefile, old_quotemapfile):
    ...
```

Note: `quotemap` is a `@jotquote.group()` subgroup, so it's invoked as `jotquote quotemap rebuild <quotefile> <old_quotemapfile>`. It does not use `ctx.obj['QUOTEFILE']` — the paths are explicit arguments.

The parent `jotquote` group currently validates that the quote file exists for all subcommands except `webserver` (line 63). We need to also exclude `quotemap` from this check since it takes its own explicit path arguments.

### 2. New `rebuild_quotemap()` function in [jotquote/api.py](jotquote/api.py)

Core business logic function with signature:
```python
def rebuild_quotemap(quotefile, old_quotemapfile):
```

Returns a list of output lines (strings). The CLI command prints these to stdout.

**Steps:**
1. `quotes = read_quotes(quotefile)` — get all quotes
2. Build `hash_to_quote` dict mapping hash → Quote for snippet generation
3. If old quotemap file exists, call `read_quotemap(old_quotemapfile)` to get:
   - Past/today entries (date <= today): preserved as-is
   - Future sticky entries (date > today with `# Sticky:`): preserved
   - Future non-sticky entries: discarded (will be regenerated)
4. Validate that every hash in the preserved entries (past + sticky) maps to a quote in the quote file. If any hash cannot be resolved, raise a `ClickException` displaying the offending quotemap line.
5. Build a `hash_to_count` dict initialized from all quote hashes (set to 0), then increment counts for each preserved entry (past + sticky). This dict is maintained throughout step 7 for efficient lookup.
6. Generate future dates from tomorrow through 10 years out.
7. For each future date not already sticky:
   - Find the minimum value in `hash_to_count`
   - Collect all hashes at that minimum count
   - `random.choice()` from that set (seeded with 0 at start of loop)
   - Assign to the date, increment its count in `hash_to_count`
8. Build output lines:
   - Past entries: raw lines preserved verbatim
   - Future entries (sticky + new): formatted with monthly comment headers
   - Format: `YYYYMMDD: <hash>  # <snippet>` or `YYYYMMDD: <hash>  # Sticky: <snippet>`

**Snippet format:** `<first 60 chars of quote>... - <author>` (truncated if quote > 60 chars)

### 3. Modify `read_quotemap()` in [jotquote/api.py](jotquote/api.py)

Change the return type from `dict[str, str]` to `dict[str, dict]`. Each value is a dict with keys:
- `hash`: the 16-char hex hash (str)
- `sticky`: whether the inline comment contains `# Sticky:` (bool)
- `raw_line`: the original line from the file (str, stripped)

Blank lines and comment-only lines are still skipped (not returned). All existing validation remains.

Update all callers of `read_quotemap()`:
- [jotquote/web.py](jotquote/web.py): access `quotemap[date]['hash']` instead of `quotemap[date]`
- [tests/quotemap_test.py](tests/quotemap_test.py): update assertions to match new return format
- [tests/web_test.py](tests/web_test.py): quotemap test fixtures already write valid files — just need to update assertion expectations if any directly check the dict values

### 4. Update parent group validation in [jotquote/cli.py](jotquote/cli.py)

Change line 63 from:
```python
if ctx.invoked_subcommand != 'webserver' and not os.path.exists(quotefile):
```
to:
```python
if ctx.invoked_subcommand not in ('webserver', 'quotemap') and not os.path.exists(quotefile):
```

### 5. New [QUOTEMAP.md](QUOTEMAP.md)

A dedicated doc file covering the quotemap feature (mirroring the REVIEW.md pattern). Contents:
- Overview: what the quotemap file does (assigns quotes to dates for the web server, enables permalinks)
- File format: `YYYYMMDD: <hash>  # optional comment`, with examples
- settings.conf configuration: `quotemap_file` property
- Web server behavior: `/` route, `/<date>` route, permalink display
- **Rebuild command** section:
  - Purpose: auto-generate a quotemap for the next 10 years
  - Usage: `jotquote quotemap rebuild <quotefile> <old_quotemapfile> > quotemap.txt`
  - How it preserves past/today entries and sticky entries
  - How to mark an entry as sticky by adding `# Sticky:` to the inline comment
  - Even distribution algorithm explanation
  - Example workflow: generate, review, redirect to file

### 6. Tests — new file [tests/api_quotemap_rebuild_test.py](tests/api_quotemap_rebuild_test.py)

**Unit tests for `rebuild_quotemap()`:**
- Generates entries for ~10 years (~3652 days)
- Preserves past/today entries verbatim
- Preserves sticky future entries
- Regenerates non-sticky future entries
- Even distribution: no hash used N+1 times until all used N times
- Monthly comment headers present
- Deterministic: same input produces same output
- Works with nonexistent quotemap file (fresh generation)
- Unresolvable hash in quotemap raises ClickException

**CLI tests for `jotquote quotemap rebuild`:**
- Invokes via CliRunner, checks exit code 0
- Stdout has correct format
- Missing quote file gives error

**CLI integration test — add to [tests/cli_integration_test.py](tests/cli_integration_test.py):**
- `test_quotemap_rebuild` — runs `jotquote quotemap rebuild <quotefile> <old_quotemapfile>` as a subprocess, verifies exit code 0 and stdout contains expected quotemap lines

## Files to modify
- [jotquote/cli.py](jotquote/cli.py) — add `quotemap` group with `rebuild` subcommand, update parent validation
- [jotquote/api.py](jotquote/api.py) — modify `read_quotemap()` return type, add `rebuild_quotemap()`
- [jotquote/web.py](jotquote/web.py) — update `read_quotemap()` caller to use new return format
- [tests/quotemap_test.py](tests/quotemap_test.py) — update assertions for new `read_quotemap()` return format
- [tests/web_test.py](tests/web_test.py) — update assertions if needed for new `read_quotemap()` return format
- [tests/cli_integration_test.py](tests/cli_integration_test.py) — add `test_quotemap_rebuild` integration test

## Files to create
- [QUOTEMAP.md](QUOTEMAP.md) — quotemap feature documentation
- [tests/api_quotemap_rebuild_test.py](tests/api_quotemap_rebuild_test.py) — unit tests

## Post-implementation
- Save a copy of this plan to [plans/2026-19-03-quotemap-rebuild.md](plans/2026-19-03-quotemap-rebuild.md)

## Verification
1. `uv run ruff check jotquote/` — lint passes
2. `uv run pytest` — all tests pass
3. Manual: `jotquote quotemap rebuild ~/.jotquote/quotes.txt ~/.jotquote/quotemap.txt` and inspect stdout
