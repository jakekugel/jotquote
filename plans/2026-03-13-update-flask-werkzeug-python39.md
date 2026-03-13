# Plan: Update Flask/Werkzeug minimum to Python 3.9 baseline

## Context
The project currently requires `flask>=3.0`, which resolves werkzeug to two different versions in uv.lock:
- Werkzeug 3.0.6 for Python <3.9
- Werkzeug 3.1.6 for Python ≥3.9

Flask 3.1 is the first Flask release to drop Python 3.8 support and require werkzeug ≥3.1.0 — the lowest werkzeug series that targets Python 3.9 as its minimum. Bumping the Flask floor to `flask>=3.1` collapses the split resolution, sets werkzeug's effective minimum to 3.1.x, and aligns the project's Python floor with that baseline.

## Files to Modify

### 1. [pyproject.toml](pyproject.toml)
- `flask>=3.0` → `flask>=3.1` (pulls in werkzeug ≥3.1 transitively)
- `requires-python = ">=3.8.1"` → `requires-python = ">=3.9"` (Flask 3.1 requires Python ≥3.9)
- Remove `"Programming Language :: Python :: 3.8"` classifier (line 22)

### 2. [.github/workflows/ci.yml](.github/workflows/ci.yml)
- Remove `"3.8"` from the `python-version` test matrix (line 14)

### 3. [README.md](README.md)
- Update "tested on Python 3.8 through 3.14" → "Python 3.9 through 3.14" (line 100)

### 4. [DEVELOPMENT.md](DEVELOPMENT.md)
- Update "Python 3.8–3.14" → "Python 3.9–3.14" (line 57)

### 5. [uv.lock](uv.lock)
- Regenerated automatically by `uv sync --group dev` — no manual edits needed

## Implementation Steps

1. Edit `pyproject.toml`: `flask>=3.0` → `flask>=3.1`
2. Edit `pyproject.toml`: `requires-python = ">=3.8.1"` → `requires-python = ">=3.9"`
3. Edit `pyproject.toml`: remove the `"Programming Language :: Python :: 3.8"` classifier
4. Edit `.github/workflows/ci.yml`: remove `"3.8"` from the python-version matrix
5. Edit `README.md`: update Python version range from 3.8–3.14 to 3.9–3.14
6. Edit `DEVELOPMENT.md`: update Python version range from 3.8–3.14 to 3.9–3.14
7. Run `uv sync --group dev` to regenerate `uv.lock`
8. Save a copy of this plan to [plans/](plans/) as `2026-03-13-update-flask-werkzeug-python39.md`

## Verification

- `uv sync --group dev` completes without errors
- `uv lock --check` passes (lock is consistent)
- `uv run pytest` passes
- In `uv.lock`, confirm only a single Flask and single Werkzeug entry remains (no Python <3.9 split)
