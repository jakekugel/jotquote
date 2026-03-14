# Plan: Switch from flake8 to Ruff

## Context
The project currently uses flake8 for linting, configured via `.flake8` and referenced in `CLAUDE.md`, `pyproject.toml` (dev dependency), and the GitHub Actions CI workflow. Ruff is a faster, modern replacement that supports the same rule codes (E, W, F, N, I) and can be configured entirely in `pyproject.toml`, simplifying the tooling setup.

## Changes

### 1. `pyproject.toml`
- Replace `"flake8>=6.0"` with `"ruff"` in `[dependency-groups] dev`
- Add Ruff config sections that mirror the existing `.flake8` settings:

```toml
[tool.ruff]
line-length = 120
exclude = [".tox", "*.egg", ".git", "venv", "tests", "__pycache__", ".venv"]

[tool.ruff.lint]
select = ["E", "W", "F", "N", "I"]
ignore = ["E501", "E722"]
```

> Notes on rule mapping:
> - `E501` (line too long) — kept ignored to match existing behavior
> - `W503` (line break before binary operator) — not a ruff rule; ruff follows W504 by default, so this can be dropped
> - `E722` (bare `except`) — kept ignored to match existing behavior
> - `N` (pep8-naming) and `I` (isort) are built into ruff; no extra plugins needed

### 2. Delete `.flake8`
Config is now consolidated in `pyproject.toml`. The `.flake8` file is no longer needed.

### 3. `CLAUDE.md`
Update the lint command and the Flake8 rules note:
- Command: `uv run ruff check jotquote/`
- Remove the `python -m` Windows workaround note (not needed for ruff)
- Update the "Flake8 rules" section heading to "Ruff rules" and point to `[tool.ruff]` in `pyproject.toml`

### 4. `.github/workflows/ci.yml`
Update the `Lint` step:
```yaml
- name: Lint
  run: uv run ruff check jotquote/
```

## Files modified
- [pyproject.toml](../pyproject.toml)
- `.flake8` — deleted
- [CLAUDE.md](../CLAUDE.md)
- [.github/workflows/ci.yml](../.github/workflows/ci.yml)

## Additional fixes applied
Running `ruff check --fix` resolved 5 auto-fixable issues that flake8 missed:
- `I001` unsorted imports in `__init__.py`, `api.py`, `cli.py`, `web.py` (ruff has isort built-in)
- `E714` `not ... is` → `is not` in `api.py:366`
