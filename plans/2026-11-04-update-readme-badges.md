# Plan: Update README.md Badges

## Context
The current README.md has four badges (Build Status, Coverage, PyPI version, License). The user wants to replace them with four badges matching a specific visual design shown in a screenshot.

## Changes

**File:** [README.md](README.md) — lines 3–6

Replace the current badge block with these four badges (in order):

1. **PyPI version** — uses `img.shields.io/pypi/v/jotquote` (dynamic, auto-updates)
2. **License** — static MIT badge via `img.shields.io`
3. **Python versions** — uses `img.shields.io/pypi/pyversions/jotquote` (dynamic from PyPI classifiers)
4. **CI** — links to the GitHub Actions CI workflow

### Summary of changes
- **Removed**: Coverage badge (codecov)
- **Added**: Python versions badge
- **Kept** (restyled): PyPI version, License, CI

## Verification
- Visually inspect the rendered README on GitHub after pushing, or preview locally with a Markdown renderer
- Confirm all badge images load and all links point to the correct destinations
