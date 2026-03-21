# Development

As an open source project, contributions are welcome.  Examples of
contributions include:

- Code patches
- Documentation improvements
- Bug reports and patch reviews

If you have an idea for jotquote, run it by me before you begin
writing code.  This way, I can get you going in the right direction.

## Development environment setup

1. (Optional, but recommended) Install [uv](https://docs.astral.sh/uv/).

2. Install jotquote and all development dependencies:

```bash
$ uv sync --group dev
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

**Method 1 — `jotquote webserver` command (all platforms)**

```bash
$ uv run jotquote webserver
```

This reads the host and port from `~/.jotquote/settings.conf` and starts the server.

**Method 2 — WSGI server directly (Linux/Mac)**

```bash
$ uv run gunicorn --bind 127.0.0.1:5544 jotquote.web:app
```

This bypasses the `jotquote webserver` command and lets the WSGI server control the
host, port, and worker configuration.  Waitress can be used as a cross-platform
alternative:

```bash
$ uv run waitress-serve --host 127.0.0.1 --port 5544 jotquote.web:app
```

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
3. Ensure `uv run pytest` and `uv run python -m flake8 jotquote/` both pass.
4. Submit a pull request — CI must be green before merging.
