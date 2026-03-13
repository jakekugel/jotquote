# Plan: Remove Twine, Use uv publish

## Context
The project currently uses `twine` for validating and uploading distributions to PyPI. `uv publish` now covers both of these capabilities, making twine redundant. This change removes the dependency and updates the publishing workflow documentation.

## Files to Modify

### 1. [pyproject.toml](pyproject.toml)
- Remove `"twine>=4.0"` from `[dependency-groups]` dev group

### 2. [PUBLISH.md](PUBLISH.md)
Remove all twine references entirely; replace with `uv publish` equivalents:
- Remove `TWINE_USERNAME`/`TWINE_PASSWORD` prerequisite — replace with `UV_PUBLISH_TOKEN` (API token) or `--token` flag
- Remove the "validate dist" twine check step entirely — uv publish validates on upload
- Step: upload to TestPyPI — replace with `uv publish --publish-url https://test.pypi.org/legacy/ dist/*`
- Step: upload to PyPI — replace with `uv publish dist/*`

### 3. [uv.lock](uv.lock)
- Will update automatically when `uv sync --group dev` is run after removing twine from pyproject.toml — no manual edits needed

## Implementation Steps

1. Edit `pyproject.toml`: remove the `"twine>=4.0"` line from the dev dependency group
2. Edit `PUBLISH.md`: remove all twine references entirely; replace upload steps with `uv publish` commands and update credential setup instructions to use `UV_PUBLISH_TOKEN`
3. Run `uv sync --group dev` to regenerate `uv.lock` without twine
4. Save a copy of this plan to [plans/](plans/) as `2026-03-13-remove-twine.md`

## Verification

- `uv sync --group dev` completes without errors and twine is no longer in the lock file
- `grep -r twine .` (excluding `.venv`) returns no results
