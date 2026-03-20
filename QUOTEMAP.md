# Quotemap

The quotemap file assigns specific quotes to specific dates for display by the jotquote web server. When configured, the web server checks the quotemap before falling back to the default seeded random selection. The quotemap also enables permalink URLs (`/<YYYYMMDD>`) so that a specific date's quote can be shared and revisited.

## File Format

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

## Configuration

Add the `quotemap_file` property to `~/.jotquote/settings.conf`:

```ini
[jotquote]
quotemap_file = ~/.jotquote/quotemap.txt
```

## Web Server Behavior

- `/` — If today's date has an entry in the quotemap, that quote is shown along with a permalink. Otherwise, the default seeded random selection is used.
- `/<YYYYMMDD>` — Shows the quote mapped to that date. Returns 404 if the date is not in the quotemap.

## Rebuild Command

The `jotquote quotemap rebuild` command auto-generates a quotemap for the next 10 years, cycling through quotes with even distribution.

### Usage

```bash
jotquote quotemap rebuild <quotefile> <old_quotemapfile> > quotemap.txt
```

The command prints the rebuilt quotemap to stdout. Redirect to a file to save it.

Use `--days` to control how many days into the future are generated (default: 3652, about 10 years):

```bash
jotquote quotemap rebuild --days 365 quotes.txt quotemap.txt > quotemap_new.txt
```

### How It Works

1. Reads all quotes from the quote file
2. If the old quotemap file exists, reads existing entries:
   - **Past/today entries** are preserved verbatim
   - **Future sticky entries** (lines with `# Sticky:` in the comment) are preserved
   - All other future entries are discarded and regenerated
3. Validates that every preserved hash maps to a quote in the quote file
4. For each future date without a sticky entry, assigns a quote using even distribution:
   - Tracks how many times each quote hash has been used
   - Selects from the least-used quotes
   - Uses a deterministic seed so rebuilds produce the same output

### Sticky Entries

To mark an entry as sticky (so it won't be overwritten during a rebuild), add `# Sticky:` to the inline comment:

```
20260401: 9f8e7d6c5b4a3210  # Sticky: April Fools quote
```

**Auto-sticky for new quotes:** When a quote's hash has never appeared in the old quotemap file, the rebuild automatically marks its first occurrence as Sticky. This preserves the debut date for newly added quotes across future rebuilds. Only the first occurrence is marked; subsequent assignments of the same hash are normal.

### Example Workflow

```bash
# Generate a fresh quotemap
jotquote quotemap rebuild ~/.jotquote/quotes.txt ~/.jotquote/quotemap.txt > /tmp/quotemap_new.txt

# Review the output
less /tmp/quotemap_new.txt

# Replace the old quotemap
cp /tmp/quotemap_new.txt ~/.jotquote/quotemap.txt
```
