# Development

As an open source project, contributions are welcome.  Examples of
contributions include:

- Code patches
- Documentation improvements
- Bug reports and patch reviews

If you have an idea for jotquote, run it by me before you begin
writing code.  This way, I can get you going in the right direction.

## Quick-start guide
Use the following steps for the first-time setup of your development environment.

1. Install a recent version of Python.

2. Install [uv](https://docs.astral.sh/uv/).

3. Use uv to install all project dependencies.

```bash
$ uv sync --group dev
```

4. Test your environment by running all unit and integration tests.

```bash
$ uv run pytest
```

5. Test your environment by running the jotquote command under development.

```bash
$ uv run jotquote
```

## Running unit tests

Once the development environment has been configured as described above,
the unit tests can be run with this command:

```bash
$ uv run pytest
```

Or to run a single test file or individual test:

```bash
$ uv run pytest tests/api_test.py
$ uv run pytest tests/api_test.py::TestClassName::test_method_name
```

Or to run and measure code coverage:

```bash
$ uv run coverage run -m pytest
$ uv run coverage report
```

## Running the web server

```bash
$ uv run jotquote webserver
```

This reads the host and port from `~/.jotquote/settings.conf` and starts the server.

## Running lint

```bash
$ uv run ruff check jotquote/
```

## VS Code integration

Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) (`charliermarsh.ruff`), then add the following to your `settings.json` to enable format-on-save and lint auto-fixes:

```json
"[python]": {
  "editor.defaultFormatter": "charliermarsh.ruff",
  "editor.formatOnSave": true
},
"editor.codeActionsOnSave": {
  "source.fixAll.ruff": "explicit",
  "source.organizeImports.ruff": "explicit"
}
```

This runs the Ruff formatter (style/quotes/spacing) and linter auto-fixes each time a Python file is saved. Quote style and other rules are read from `pyproject.toml` automatically.

## Multi-version CI

Multi-version testing (Python 3.9–3.14 on Linux, Mac, and Windows) is
handled automatically by GitHub Actions on push and pull request.

## Testing the built artifact

Before uploading to PyPI, you can build the package and install it directly
into a Python installation to verify it works end-to-end:

1. Build the wheel and sdist:

```bash
$ uv build
```

This produces files in the `dist/` directory, e.g. `dist/jotquote-1.2.3-py3-none-any.whl`.

2. Install the wheel into a Python environment with pip:

```bash
$ pip install dist/jotquote-1.2.3-py3-none-any.whl
```

To reinstall over an existing version, add `--force-reinstall`:

```bash
$ pip install --force-reinstall dist/jotquote-1.2.3-py3-none-any.whl
```

3. Verify the installed version:

```bash
$ jotquote --version
```

4. When done testing, uninstall with:

```bash
$ pip uninstall jotquote
```

## Submitting changes

1. Open an issue or discuss your idea before writing code.
2. Fork the repository and create a branch for your change.
3. Ensure `uv run pytest` and `uv run ruff check jotquote/` both pass.
4. Submit a pull request — CI must be green before merging.

## Publishing to PyPI

### Prerequisites

- PyPI and TestPyPI accounts with API tokens
- uv installed and dev dependencies synced (`uv sync --group dev`)

---

### Steps

#### 1. Update version to release version

Edit `pyproject.toml` and remove the `.dev0` suffix:

```toml
# Before
version = "1.0.0.dev0"

# After
version = "1.0.0"
```

#### 2. Merge PR to main

Open a pull request with the version bump and merge it to `main`.

#### 3. Build the distribution

Remove any previous build artifacts, then build:

```bash
rm -rf dist/
uv build
```

This creates `dist/jotquote-X.Y.Z-py3-none-any.whl` and `dist/jotquote-X.Y.Z.tar.gz`.

#### 4. Publish to TestPyPI

```bash
uv publish --publish-url https://test.pypi.org/legacy/ dist/*
```

Authenticate with a TestPyPI API token via the `UV_PUBLISH_TOKEN` environment variable or the `--token` flag.

#### 5. Install from TestPyPI and test

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

#### 6. Publish to PyPI

```bash
uv publish dist/*
```

Authenticate with a PyPI API token via the `UV_PUBLISH_TOKEN` environment variable or the `--token` flag.

#### 7. Install from PyPI and test

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

#### 8. Tag the release in git

```bash
git tag -a X.Y.Z -m "version X.Y.Z"
git push origin X.Y.Z
```

#### 9. Update version to next development version

Edit `pyproject.toml` and bump to the next dev version:

```toml
# Before
version = "1.0.0"

# After
version = "1.0.1.dev0"
```

Commit and push directly to `main` (or open a follow-up PR).
