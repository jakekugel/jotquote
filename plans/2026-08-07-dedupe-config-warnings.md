# Plan: Emit config warnings once, cleanly, from the CLI

## Context

When `jotquote add` (or any subcommand) runs with a typo'd property in
`settings.conf` — e.g. `font_family` in `[web]` — the warning is printed
**five times**, each with noisy Python-internal formatting:

```
C:\...\jotquote\cli\cli.py:78: UserWarning: settings.conf: unrecognized key 'font_family' in [web] section will be ignored.
  config = api.get_config()
C:\...\jotquote\cli\cli.py:368: UserWarning: settings.conf: unrecognized key 'font_family' in [web] section will be ignored.
  config = api.get_config()
... (3 more) ...
```

**Root cause.** `get_config()` is called ~5 times per invocation (the `jotquote`
group callback at `cli.py:78`, `_add_quotes` at `cli.py:368`, `_lint_new_quotes`
at `cli.py:358`, `store.py:468`, and the author-count block at `cli.py:412`).
Each call re-runs `_warn_unknown_keys()` in
[jotquote/api/config.py](jotquote/api/config.py), which calls
`warnings.warn(...)`. Python's *default* warning filter deduplicates by
**call-site (module + line number)**, so each distinct caller prints its own
copy. The `file:line: UserWarning:` prefix and echoed source line are the
default `warnings` formatting.

**Intended outcome.** A single, clean, one-line warning per unique config
problem, printed once to **stderr** (conventional for diagnostics), for CLI
usage. The library/web/API `warn-on-every-call` contract stays unchanged.

## Approach

Fix this at the **CLI entry point only** — a presentation concern that belongs
to the front-end, not the API. Leave [jotquote/api/config.py](jotquote/api/config.py)
untouched so `get_config()` keeps emitting a warning on every call (the web apps
and the existing `pytest.warns`-based api tests depend on this).

In [jotquote/cli/cli.py](jotquote/cli/cli.py), install a custom
`warnings.showwarning` handler in `main()` that:
- Deduplicates by message text via a local `set` (so repeated identical
  warnings across the many `get_config()` calls print only once), and
- Prints each unique warning as a clean single line: `Warning: <message>` to
  `sys.stderr`.

This handles both the unrecognized-key warnings **and** the legacy `[jotquote]`
deprecation warning (same mechanism, any `UserWarning`).

### Changes

**[jotquote/cli/cli.py](jotquote/cli/cli.py)**

- Add `import warnings` (top of file, alongside existing stdlib imports).
- Add a small helper near the bottom, before `main()`:

  ```python
  def _install_clean_warning_handler():
      """Print each unique warning once as a clean one-line message to stderr.

      The CLI calls get_config() several times per invocation and each call
      re-emits config warnings; Python's default filter dedups by call site,
      so the same warning would otherwise print once per caller. This handler
      collapses duplicates (by message text) and strips the noisy
      file:line/source-line formatting.
      """
      seen = set()

      def _show(message, category, filename, lineno, file=None, line=None):
          text = str(message)
          if text in seen:
              return
          seen.add(text)
          print('Warning: {}'.format(text), file=sys.stderr)

      warnings.showwarning = _show
  ```

- Call it at the start of `main()`:

  ```python
  def main():
      _install_clean_warning_handler()
      return jotquote(obj={})
  ```

`sys` is already imported. No changes to any `get_config()` call site.

### Why not the alternatives

- **Process-level dedup inside `get_config()`** — changes the warn-on-every-call
  semantics that `tests/unit/api/test_config.py` (`pytest.warns` on each call)
  and the web apps rely on; two api tests assert the *same* legacy message and
  would collide under a shared process-level cache.
- **`warnings.filterwarnings('once', ...)`** — collapses duplicates but keeps the
  ugly default `file:line:` formatting, so it fails the "clean" requirement.
  The custom `showwarning` handler gives both dedup and clean formatting in one
  place.

## Tests (red/green TDD)

**Unit — [tests/unit/cli/test_cli.py](tests/unit/cli/test_cli.py)**

Add tests that exercise the handler directly (restore `warnings.showwarning`
afterward to avoid leaking global state into other tests — use a fixture or
`monkeypatch.setattr(warnings, 'showwarning', warnings.showwarning)`):

1. `test_clean_warning_handler_dedups` — install the handler, call
   `warnings.warn('settings.conf: unrecognized key ...', UserWarning)` twice;
   assert (via `capsys`) exactly one `Warning: settings.conf: unrecognized key ...`
   line on stderr.
2. `test_clean_warning_handler_distinct_messages` — two *different* warning
   messages each print once.
3. `test_clean_warning_handler_format` — output line starts with `Warning: `
   and contains no `UserWarning`/`.py:` file-and-line noise.

**Integration — [tests/integration/test_cli.py](tests/integration/test_cli.py)**

This suite already runs the real `jotquote` script via `subprocess` (so it goes
through `main()`) and builds a `settings.conf` via `_make_env`. Add:

4. `test_add_bad_config_key_warns_once` — build an env whose `[web]` section
   contains an unrecognized key (e.g. `font_family = serif`), run `jotquote add`
   on a fixture quote file, and assert:
   - the process succeeds and prints the `... quote added ...` line, and
   - the warning `unrecognized key 'font_family'` appears **exactly once**
     across combined stdout+stderr (`output.count("unrecognized key 'font_family'") == 1`),
     and no `.py:` / `UserWarning:` prefix is present.

   Note: `_make_env` routes unknown/`web_`-prefixed keys — pass the bad key so it
   lands in `[web]` (e.g. via the `web_` handling or by extending the helper if
   needed), matching the reported `font_family` scenario.

## Verification

```bash
# Unit + integration tests
uv run pytest tests/unit/cli/test_cli.py tests/integration/test_cli.py

# Full suite + lint
uv run pytest
uv run ruff check

# Built-in quote collection must stay lint-clean
export JOTQUOTE_CONFIG=jotquote/resources/settings.conf
uv run jotquote lint
```

Manual end-to-end reproduction of the original report: add `font_family = serif`
under `[web]` in `~/.jotquote/settings.conf`, run
`jotquote add -e "Some quote | Author | | 3stars"`, and confirm a single clean
line on stderr:

```
Warning: settings.conf: unrecognized key 'font_family' in [web] section will be ignored.
```
