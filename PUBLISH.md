# Publishing jotquote to PyPI

## Prerequisites

- PyPI and TestPyPI accounts with API tokens configured in `~/.pypirc` or as environment variables (`TWINE_USERNAME`, `TWINE_PASSWORD`)
- uv installed and dev dependencies synced (`uv sync --group dev`)

---

## Steps

### 1. Update version to release version

Edit `pyproject.toml` and remove the `.dev0` suffix:

```toml
# Before
version = "1.0.0.dev0"

# After
version = "1.0.0"
```

### 2. Merge PR to main

Open a pull request with the version bump and merge it to `master`.

### 3. Build the distribution

Remove any previous build artifacts, then build:

```bash
rm -rf dist/
uv build
```

This creates `dist/jotquote-X.Y.Z-py3-none-any.whl` and `dist/jotquote-X.Y.Z.tar.gz`.

Verify the metadata is valid:

```bash
uv run twine check dist/*
```

### 4. Publish to TestPyPI

```bash
uv run twine upload --repository testpypi dist/*
```

### 5. Install from TestPyPI and test

```bash
uv venv /tmp/jotquote-test
source /tmp/jotquote-test/bin/activate          # Linux/Mac
# or: /tmp/jotquote-test/Scripts/activate       # Windows

uv pip install --index-url https://test.pypi.org/simple/ \
               --extra-index-url https://pypi.org/simple/ \
               jotquote==X.Y.Z

jotquote --version
jotquote random
jotquote info
deactivate
```

### 6. Publish to PyPI

```bash
uv run twine upload dist/*
```

### 7. Install from PyPI and test

```bash
uv venv /tmp/jotquote-prod
source /tmp/jotquote-prod/bin/activate          # Linux/Mac
# or: /tmp/jotquote-prod/Scripts/activate       # Windows

uv pip install jotquote==X.Y.Z

jotquote --version
jotquote random
jotquote info
deactivate
```

### 8. Tag the release in git

```bash
git tag -a X.Y.Z -m "version X.Y.Z"
git push origin X.Y.Z
```

### 9. Update version to next development version

Edit `pyproject.toml` and bump to the next dev version:

```toml
# Before
version = "1.0.0"

# After
version = "1.0.1.dev0"
```

Commit and push directly to `master` (or open a follow-up PR).
