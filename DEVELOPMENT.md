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

## Running lint

```bash
$ uv run python -m flake8 jotquote/
```

On Windows, using `python -m flake8` avoids Application Control policy
restrictions that may block the `flake8` wrapper executable directly.

## Multi-version CI

Multi-version testing (Python 3.9–3.14 on Linux, Mac, and Windows) is
handled automatically by GitHub Actions on push and pull request.

## Submitting changes

1. Open an issue or discuss your idea before writing code.
2. Fork the repository and create a branch for your change.
3. Ensure `uv run pytest` and `uv run python -m flake8 jotquote/` both pass.
4. Submit a pull request — CI must be green before merging.
