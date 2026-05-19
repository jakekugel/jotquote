# Add timezone config property for daily-quote rollover

## Context

The user runs jotquote on a Linux host where the system clock is UTC. In `daily` mode, `jotquote/api/selection.py::get_random_choice()` calls `datetime.datetime.now()` (naive, system local time) to compute "today since 2016-01-01" and index into a deterministic seeded shuffle. On a UTC host, that means the quote rolls over at 00:00 UTC, which is 19:00 the previous day in US Central time — five hours too early for the user.

The fix is to introduce an optional IANA timezone config property and use it when computing "now" for the rollover. When unset, current behavior is preserved (system local time), so existing installs are unaffected.

## Design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Section | `[general]` | Both the CLI `today` command and the web viewer use the rollover; matches cross-cutting peers `quote_file`, `line_separator`. |
| Property name | `timezone` | Concise and conventional. Example value: `America/Chicago`. |
| Default | unset → naive `datetime.now()` | Pure backward compatibility for existing installs. |
| Library | stdlib `zoneinfo.ZoneInfo` | `requires-python = ">=3.9"` already satisfies this — no new runtime dep on POSIX. |
| Windows IANA data | Add `tzdata; sys_platform == 'win32'` to `pyproject.toml` | Tiny wheel; avoids a Windows-only stack trace. |
| Invalid value handling | Wrap `zoneinfo.ZoneInfoNotFoundError` in `ConfigError` at the call sites | Matches the existing pattern (`get_filename` validates on use, not at config load), and avoids penalizing CLI subcommands that don't consult the timezone (`add`, `list`, `lint`). |

## Files to modify

### `jotquote/api/selection.py`
- Add `import zoneinfo` and `from jotquote.api.exceptions import ConfigError`.
- Change `get_random_choice(numquotes)` → `get_random_choice(numquotes, timezone=None)` (lines 52-78).
- Replace `now = datetime.datetime.now()` at line 68 with:
  ```python
  if timezone:
      try:
          tz = zoneinfo.ZoneInfo(timezone)
      except zoneinfo.ZoneInfoNotFoundError as e:
          raise ConfigError(f"Invalid timezone '{timezone}' in [general] section of settings.conf.") from e
      now = datetime.datetime.now(tz)
  else:
      now = datetime.datetime.now()
  ```
- Update docstring to document `timezone` and the unset-fallback semantics.

### `jotquote/api/config.py`
- Add `'timezone'` to `_GENERAL_KEYS` (line 35) so legacy `[jotquote] timezone = ...` migrates to `[general]` via the explicit-membership branch (today it would still arrive there via the `else` fallthrough, but the frozenset stays self-documenting).
- No `get_config` validation — failure happens at call site (see decisions table).

### `jotquote/cli/cli.py`
- In `today()` (lines 222-238), read the timezone and pass it through:
  ```python
  config = api.get_config()
  tz = config[api.SECTION_GENERAL].get('timezone') or None
  index = api.get_random_choice(len(quotes), timezone=tz)
  ```

### `jotquote/web/viewer.py`
- Add `import zoneinfo` and `from jotquote.api.exceptions import ConfigError`.
- Add a local helper `_get_local_now(config)` that returns `(now, tz_name)`:
  ```python
  def _get_local_now(config):
      """Return ``(now, tz_name)`` for use in :func:`showpage`.

      Reads the optional ``timezone`` property from the ``[general]`` section
      of settings.conf.  When set, returns an aware ``datetime`` in that
      IANA timezone.  When empty or absent, returns a naive ``datetime`` from
      the system local clock — preserving legacy behavior.

      Args:
          config (ConfigParser): The application configuration.

      Returns:
          tuple[datetime.datetime, str | None]: The current time and the
              raw timezone name (or ``None`` when unset).

      Raises:
          ConfigError: If the configured timezone is not a known IANA name.
      """
      tz_name = config[api.SECTION_GENERAL].get('timezone') or None
      if tz_name:
          try:
              tz = zoneinfo.ZoneInfo(tz_name)
          except zoneinfo.ZoneInfoNotFoundError as e:
              raise ConfigError(f"Invalid timezone '{tz_name}' in [general] section of settings.conf.") from e
          return datetime.datetime.now(tz), tz_name
      return datetime.datetime.now(), None
  ```
- In `showpage()` (line 128-131), reorder so `config = api.get_config()` is read first, then call the helper:
  ```python
  config = api.get_config()
  now, tz_name = _get_local_now(config)
  ```
- Pass `timezone=tz_name` to both `api.get_random_choice(len(quotes))` calls (lines 198 and 205).
- No change to `_compute_expiration`: once `now` is tz-aware, the midnight cap at line 363 (`(now + timedelta(days=1)).replace(hour=0, ...)`) automatically computes the user's local midnight, and the absolute `reload_dt` at line 373 already uses UTC, so the ISO `expires_at` stays correct.
- `lookup_date = now.strftime('%Y%m%d')` (line 179) and `date1 = now.strftime(...)` (line 154) now reflect the user's local date — exactly what we want.

### `jotquote/resources/settings.conf`
Under `[general]`, add a commented opt-in line:
```
# timezone = America/Chicago
```

### `pyproject.toml`
Add to `dependencies`:
```
"tzdata; sys_platform == 'win32'",
```

### `USER_DOCUMENTATION.md`
Add to the `[general]` table (around line 250):
```
| `timezone` | _(empty)_ | IANA timezone name (e.g. `America/Chicago`) used to determine "today" for the daily-quote rollover. When empty, the system's local time is used. Invalid names produce a `ConfigError` at first use. |
```

Also update the `[web].mode` row's `daily` description to clarify: "changes at local midnight (see `[general].timezone`)".

## Tests (red → green TDD per CLAUDE.md)

### `tests/unit/api/test_selection.py`
Existing tests at lines 30-57 use a `FakeDatetime` whose `now(cls, tz=None)` returns a naive datetime — keep them as-is for back-compat coverage. Add:

1. `test_get_random_choice_uses_timezone_before_cutoff` — `FakeDatetime.now(tz)` returns aware `2026-03-14 23:44 America/Chicago`; pass `timezone='America/Chicago'`; expect index for 2026-03-14.
2. `test_get_random_choice_uses_timezone_advances_at_cutoff` — same with 23:45 → expect 2026-03-15.
3. `test_get_random_choice_timezone_fixes_utc_rollover_bug` — `FakeDatetime.now()` (naive) returns `2026-03-15 02:00`; `FakeDatetime.now(ZoneInfo('America/Chicago'))` returns aware `2026-03-14 21:00`; with `timezone='America/Chicago'` the result must equal the index for 2026-03-14, not 2026-03-15. **This is the literal user-bug test.**
4. `test_get_random_choice_invalid_timezone_raises_config_error` — `timezone='Not/AZone'` raises `api.ConfigError` with "timezone" in the message.

### `tests/unit/api/test_config.py`
5. `test_get_config_reads_timezone_from_general` — settings.conf with `timezone = America/Chicago` is read into `config[SECTION_GENERAL]['timezone']`.
6. `test_get_config_timezone_absent_by_default` — fresh default config has no `timezone` option.
7. `test_legacy_jotquote_timezone_migrates_to_general` — legacy `[jotquote] timezone = ...` migrates to `[general]`.

### `tests/unit/web/test_viewer.py`
8. `test_showpage_uses_configured_timezone_for_date_display` — set `timezone='America/Chicago'`; freeze datetime so UTC says one date and Chicago says the previous day; GET `/`; assert the Chicago-local date string is in the rendered HTML.
9. `test_showpage_passes_timezone_to_get_random_choice` — monkeypatch `api.get_random_choice` with a recording lambda; assert it received `timezone='America/Chicago'`.

### `tests/unit/cli/test_cli.py`
10. `test_today_passes_timezone_to_get_random_choice` — config sets `timezone='America/Chicago'`; spy `api.get_random_choice`; invoke `today` via Click runner; assert spy got `timezone='America/Chicago'`.

### `tests/integration/test_web_viewer.py`
11. `test_timezone_changes_displayed_date` — end-to-end: settings.conf with `timezone='America/Chicago'`; with a mocked `datetime.datetime`, the served page shows the Chicago-local date even when the system clock is in UTC.

## Verification

1. `uv run pytest` — full suite green.
2. `uv run ruff check` — clean.
3. Built-in quotes still lint:
   ```
   JOTQUOTE_CONFIG=jotquote/resources/settings.conf uv run jotquote lint
   ```
4. Manual smoke test: write a temp settings.conf with `timezone = America/Chicago`, run `JOTQUOTE_CONFIG=/tmp/... uv run jotquote today` at a time when UTC and Chicago dates differ; confirm the index matches the Chicago date.
5. Invalid value: set `timezone = Not/AZone`, run `jotquote today`; confirm the user-friendly `ConfigError` message (no raw `ZoneInfoNotFoundError` stack trace).
6. `uv build` — wheel builds; dependency list shows the conditional `tzdata`.

## After implementation

Per CLAUDE.md, copy this plan to `plans/2026-19-05-add-timezone-config-property.md` in the repo so a record lives with the project.
