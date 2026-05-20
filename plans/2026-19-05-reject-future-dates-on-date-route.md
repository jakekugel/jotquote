# Plan: Reject future dates on `/<date_path_param>` with 404

## Context

The viewer route `/<date_path_param>` ([jotquote/web/viewer.py](../jotquote/web/viewer.py)) previously accepted any well-formed 8-digit calendar date — including dates that haven't occurred yet. Permalinks to future days have no meaningful "quote of the day" and shouldn't be reachable. This change makes the route return 404 when the requested date is *after* today's local date (today itself remains allowed).

"Today" is determined in the configured `[general].timezone` so users in negative-UTC zones don't see a future-date 404 when the system clock has already rolled to UTC tomorrow.

## Approach

Added a single comparison inside `showpage()`, right after the existing `strptime` block. Reuses the `now, tz_name = _get_local_now(config)` already computed earlier in the function — no extra config read, no duplicated timezone logic.

```python
if date_path_param:
    try:
        display_date = datetime.datetime.strptime(date_path_param, '%Y%m%d')
    except ValueError:
        abort(404)
    if display_date.date() > now.date():
        abort(404)
    date1 = display_date.strftime('%A, %B %d, %Y')
```

Notes:

- `display_date` is naive (from `strptime('%Y%m%d')`); `now` may be aware (when `timezone` is set) or naive. Calling `.date()` on each extracts the local calendar date in both cases and is safe to compare.
- The 404 fires before the resolver is consulted, so a resolver that maps a future date to a hash still gets a 404.
- Equality (today) is allowed, matching "*after* the current local date".

## Files modified

### [jotquote/web/viewer.py](../jotquote/web/viewer.py)

Inserted the two-line future-date guard inside `showpage()` between the existing `strptime` block and the `date1 = ...` assignment.

## Tests

### Unit tests — added to [tests/unit/web/test_viewer.py](../tests/unit/web/test_viewer.py)

Use the existing `FakeDatetime` pattern from `test_showpage_uses_configured_timezone_for_date_display` to mock `datetime.datetime.now`. Configure a resolver where appropriate so the new guard — not the no-resolver path — is what produces the 404 on the negative case.

1. `test_date_route_future_date_returns_404` — fixed "now" to 2026-03-19, request `/20260320` with a resolver that would otherwise return 200; expect 404.
2. `test_date_route_today_is_allowed` — fixed "now" to 2026-03-19 in `America/Chicago`, resolver returns the fixture hash for `20260319`; expect 200. Verifies the boundary.
3. `test_date_route_future_check_uses_configured_timezone` — system clock at 02:00 UTC on 2026-03-15 but `America/Chicago` is 21:00 on 2026-03-14; request `/20260315` with resolver; expect 404. Pins the timezone behavior.
4. `test_date_route_past_date_still_works` — regression: fixed "now" to 2026-05-19, request `/20260319` with resolver; expect 200.

### Integration test — added to [tests/integration/test_web_viewer.py](../tests/integration/test_web_viewer.py)

`test_date_route_future_date_returns_404` — hits `/99991231` on a live `jotquote webserver` subprocess and asserts the HTTP response is 404. No TZ mocking required.

## Verification

```powershell
uv run pytest tests/unit/web/test_viewer.py -k "date_route_future or date_route_today_is_allowed or date_route_past_date"
uv run pytest tests/integration/test_web_viewer.py::test_date_route_future_date_returns_404
uv run pytest                                              # 419 passed, 1 skipped
uv run ruff check                                          # All checks passed!
$env:JOTQUOTE_CONFIG = "jotquote/resources/settings.conf"
uv run jotquote lint                                       # No issues found.
```

## Out of scope

- No change to the YYYYMMDD format, invalid-calendar-date handling, or the no-resolver 404 path.
- No change to `datepage()`, `_get_local_now()`, or `_compute_expiration()`.
- No new config keys.
- No change to root-route behavior — only the dated permalink route is affected.
