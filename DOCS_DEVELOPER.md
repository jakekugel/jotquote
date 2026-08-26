# Development

As an open source project, contributions are welcome.  Examples of
contributions include:

- Code patches
- Documentation improvements
- Bug reports and patch reviews

If you have an idea for jotquote, run it by me before you begin
writing code.  This way, I can get you going in the right direction.

## Contents

- [Quick-start guide](#quick-start-guide)
- [Running unit tests](#running-unit-tests)
- [Running the web server in development mode](#running-the-web-server-in-development-mode)
- [Web server extensions](#web-server-extensions)
  - [Quote resolver](#quote-resolver)
  - [Header provider](#header-provider)
- [Running lint](#running-lint)
- [VS Code integration](#vs-code-integration)
- [Multi-version CI](#multi-version-ci)
- [Testing the built artifact](#testing-the-built-artifact)
- [Submitting changes](#submitting-changes)
- [Publishing to PyPI](#publishing-to-pypi)
  - [Prerequisites](#prerequisites)
  - [Steps](#steps)
- [API reference](#api-reference)
  - [Classes](#classes)
  - [Quote parsing](#quote-parsing)
  - [Configuration](#configuration-2)
  - [Quote storage](#quote-storage)
  - [Quote selection](#quote-selection)
  - [Linting](#linting)
  - [Exceptions](#exceptions)

---

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

## Running the web server in development mode

Use these commands to run the web server using the current code in your project folder.

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

## Web server extensions

The web server exposes several pluggable extension points. Each is a Python module you write and install, wired up via a dotted module path in the `[web]` section of `settings.conf`. The module must be importable by the Python environment running the web server.

### Quote resolver

The quote resolver is a pluggable extension point that allows you to control which quote is displayed on a given date. When configured, the web server calls the resolver before falling back to the default seeded random selection. A resolver also enables permalink URLs (`/<YYYYMMDD>`) so that a specific date's quote can be shared and revisited.

#### How it works

A quote resolver is a Python module that you write and install. The module must define a `resolve` function with this signature:

```python
def resolve(date_str: str) -> str | None:
    """Return a 16-char MD5 hash identifying the quote, or None."""
```

- `date_str` is a date in `YYYYMMDD` format (e.g., `20260319`)
- Return a 16-character MD5 hash string to select a specific quote
- Return `None` to fall back to the default seeded random selection

To find a quote's hash, use `jotquote list -l` or `jotquote list -s <hash>`.

#### Configuration

Add the `quote_resolver_extension` property to `~/.jotquote/settings.conf` with the dotted Python module path:

```ini
[web]
quote_resolver_extension = mypackage.my_resolver
```

The module must be importable by the Python environment running the web server. If you installed jotquote with `pip` or `uv`, install your resolver module into the same environment (e.g., `pip install mypackage` or `uv pip install mypackage`). If your resolver is a standalone script rather than an installed package, add its parent directory to `PYTHONPATH` before starting the server (e.g., `PYTHONPATH=/path/to/mymodules jotquote webserver`).

#### Web server behavior

- `/` — If the resolver returns a hash for today, that quote is shown along with a permalink. If the resolver returns `None` or is not configured, the default seeded random selection is used.
- `/<YYYYMMDD>` — Calls the resolver for that date. If the resolver returns a hash, shows that quote. Returns 404 if the resolver returns `None`, is not configured, or the hash doesn't match any quote.

#### Error handling

- If the resolver module cannot be imported, an error is logged and the server falls back to seeded random selection for all requests.
- If the resolver's `resolve` function raises an exception, the error is logged and the server falls back to seeded random selection on the root route, or returns 404 on date routes.
- The resolver module is loaded once and cached for the lifetime of the server process.

### Header provider

The header provider is a pluggable extension point that controls which HTTP response headers the web server applies to quote page responses. The base package does not set any cache headers by default; configure a header provider to add `Cache-Control` or other headers.

#### How it works

A header provider is a Python module that you write and install. The module must define a `get_headers` function with this signature:

```python
def get_headers(max_age: int) -> dict[str, str]:
    """Return HTTP response headers given the computed max-age value."""
```

- `max_age` is the cache duration in seconds, computed by the web server based on mode (`daily` vs `random`) and the `expiration_seconds` configuration.
- Return a dictionary mapping header names to header values.
- The returned headers are applied to every quote page response.

#### Configuration

Add the `header_provider_extension` property to `~/.jotquote/settings.conf` with the dotted Python module path:

```ini
[web]
header_provider_extension = mypackage.my_headers
```

The module must be importable by the Python environment running the web server. If you installed jotquote with `pip` or `uv`, install your header provider module into the same environment. If your provider is a standalone script rather than an installed package, add its parent directory to `PYTHONPATH` before starting the server (e.g., `PYTHONPATH=/path/to/mymodules jotquote webserver`).

When `header_provider_extension` is not set, no custom HTTP headers are applied to responses.

#### Example

A simple header provider that sets `Cache-Control`:

```python
def get_headers(max_age):
    return {'Cache-Control': f'public, max-age={max_age}'}
```

#### Error handling

- If the provider module cannot be imported, an error is logged and no custom headers are applied.
- If the `get_headers` function raises an exception, the error is logged and no custom headers are applied to the response.
- The provider module is loaded once and cached for the lifetime of the server process.

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

## API reference

This section describes the public Python API of the `jotquote` package.
All symbols documented here are re-exported from `jotquote.api`, which is
the single supported entry point for programmatic use.  Import via:

```python
from jotquote import api

quotes = api.read_quotes('/path/to/quotes.txt')
```

Equivalently:

```python
import jotquote.api

quotes = jotquote.api.read_quotes('/path/to/quotes.txt')
```

Do not import from submodules such as `jotquote.api.store` or
`jotquote.api.quote` directly — those paths are implementation detail and
may change between releases.

---

### Classes

#### `Quote`

A quote with author, optional publication, and tags.  This is the core
data model used throughout the API.

```python
Quote(quote: str, author: str, publication: str | None, tags: list[str] | None)
```

**Attributes:**

| Attribute     | Type             | Description                                                                                     |
|---------------|------------------|-------------------------------------------------------------------------------------------------|
| `quote`       | `str`            | The quote text.                                                                                 |
| `author`      | `str`            | Name of the person the quote is attributed to.                                                  |
| `publication` | `str` \| `None`  | Publication containing the quote, or `None` if not recorded.                                    |
| `tags`        | `list[str]`      | Zero or more tags associated with the quote.                                                    |
| `line_number` | `int`            | 1-based line number of the quote in the quote file it was read from; `0` if not read from file. |

Raises [`QuoteValidationError`](#quotevalidationerror) if any text field
contains a forbidden character (pipe, double quote, newline, carriage
return).  Raises `TypeError` if `tags` is not a list.

**Example:**

```python
from jotquote import api

q = api.Quote(
    'The best way out is always through.',
    'Robert Frost',
    'A Servant to Servants',
    ['motivational', 'poetry'],
)
print(q.quote)
print(q.tags)
```

##### `Quote.has_tag`

```python
has_tag(tag: str) -> bool
```

Return `True` if this quote has the given tag.

**Example:**

```python
from jotquote import api

q = api.Quote('Onward.', 'Anon.', None, ['motivational'])
if q.has_tag('motivational'):
    print('this one is motivational')
```

##### `Quote.has_tags`

```python
has_tags(tags: Iterable[str]) -> bool
```

Return `True` if this quote has every tag in `tags`.

**Example:**

```python
from jotquote import api

q = api.Quote('Onward.', 'Anon.', None, ['motivational', 'short'])
q.has_tags(['motivational', 'short'])   # True
q.has_tags(['motivational', 'funny'])   # False
```

##### `Quote.has_keyword`

```python
has_keyword(keyword: str) -> bool
```

Return `True` if `keyword` is a substring of the quote text, author,
publication, or matches a tag.

**Example:**

```python
from jotquote import api

q = api.Quote('A theory of relativity.', 'Einstein', None, ['physics'])
q.has_keyword('Einstein')   # True
q.has_keyword('music')      # False
```

##### `Quote.set_tags`

```python
set_tags(tags: list[str] | None) -> None
```

Replace this quote's tags with the given list.  Passing `None` clears
all tags.  Raises `TypeError` if `tags` is not `None` and not a list.

**Example:**

```python
from jotquote import api

q = api.Quote('Onward.', 'Anon.', None, ['old_tag'])
q.set_tags(['motivational', 'short'])
print(q.tags)   # ['motivational', 'short']
q.set_tags(None)
print(q.tags)   # []
```

##### `Quote.get_hash`

```python
get_hash() -> str
```

Return a 16-character hex hash for this quote.  The hash is computed
from the lowercased first letter of each alphabetic word in the quote
text, then MD5-hashed.  This makes the hash tolerant of minor edits and
formatting changes.  Since collisions are possible, callers should
verify that only one quote matches.

**Example:**

```python
from jotquote import api

q = api.Quote('The best way out is always through.', 'Robert Frost', None, [])
print(q.get_hash())   # e.g. 'a1b2c3d4e5f67890'
```

##### `Quote.get_num_stars`

```python
get_num_stars() -> int
```

Return a star rating between 0 and 5 derived from the star tags
(`1star`, `2stars`, `3stars`, `4stars`, `5stars`).  If multiple star
tags are present, the lowest one wins.  Returns `0` if no star tag is
present.

**Example:**

```python
from jotquote import api

q = api.Quote('Onward.', 'Anon.', None, ['motivational', '4stars'])
print(q.get_num_stars())   # 4
```

##### `Quote.get_line_number`

```python
get_line_number() -> int
```

Return the 1-based line number of this quote in its quote file, or `0`
if the quote was not read from a file.

**Example:**

```python
from jotquote import api

quotes = api.read_quotes('/home/user/.jotquote/quotes.txt')
first = quotes[0]
print(f'line {first.get_line_number()}: {first.quote}')
```

---

#### `LintIssue`

A single lint finding attached to a specific quote.  `LintIssue` is a
`@dataclass`; instances are usually produced by
[`lint_quotes`](#lint_quotes).

**Fields:**

| Field         | Type             | Description                                                                                 |
|---------------|------------------|---------------------------------------------------------------------------------------------|
| `line_number` | `int`            | 1-based line number of the quote in the source file.                                        |
| `check`       | `str`            | Name of the check that produced the issue (e.g. `'smart-quotes'`).                          |
| `field`       | `str`            | Field the issue applies to — one of `'quote'`, `'author'`, `'publication'`, or `'tags'`.    |
| `message`     | `str`            | Human-readable description of the issue.                                                    |
| `fixable`     | `bool`           | `True` if [`apply_fixes`](#apply_fixes) can auto-correct this issue (default `False`).      |
| `fix_value`   | `str` \| `None`  | Single-issue preview: the value the field would take if this one issue alone were applied to the original text. Useful for dry-run output. `apply_fixes` does not consume this field — applying the fix to multiple issues on the same field requires recomputing against the live attribute, not stacking stored previews — so callers should treat `fix_value` as a preview only. `None` when `fixable` is `False`. |

**Example:**

```python
from jotquote import api

config, _ = api.get_config()
quotes = api.read_quotes(api.get_filename())

issues = api.lint_quotes(quotes, {'smart-quotes', 'no-tags'}, config)
for issue in issues:
    print(f'line {issue.line_number} [{issue.check}] {issue.message}')
```

---

### Quote parsing

#### `parse_quote`

```python
parse_quote(new_quote: str, simple_format: bool = True) -> Quote
```

Parse a single quote string into a [`Quote`](#quote).

If `simple_format` is `True` (the default), the input is parsed as
`<quote> - <author> [(publication)]` — the hyphen separates the quote
from the author, and an optional parenthesized publication may follow.
If `simple_format` is `False`, the input uses the pipe-delimited
quote-file format `<quote>|<author>|[<publication>]|[<tag1>,<tag2>,...]`.

Raises [`QuoteValidationError`](#quotevalidationerror) if the line
cannot be parsed.

**Example:**

```python
from jotquote import api

q = api.parse_quote('The best way out is always through. - Robert Frost')
print(q.author)        # 'Robert Frost'
print(q.publication)   # None

q = api.parse_quote(
    'The best way out is always through. | Robert Frost | A Servant to Servants | motivational',
    simple_format=False,
)
print(q.tags)          # ['motivational']
```

---

#### `parse_tags`

```python
parse_tags(tag_string: str) -> list[str]
```

Parse a comma-separated tag string into a sorted list of unique tags.
Empty segments are dropped.  Raises
[`QuoteValidationError`](#quotevalidationerror) if any tag contains
characters other than ASCII letters, digits, or underscores.

**Example:**

```python
from jotquote import api

api.parse_tags('poetry, motivational, motivational')
# ['motivational', 'poetry']
```

---

### Configuration

#### `get_config`

```python
get_config() -> tuple[configparser.ConfigParser, bool]
```

Load `settings.conf` and return the parsed config plus a flag indicating
whether legacy-format migration occurred.  On first run, the file is
created from the template and the default quote file is copied
alongside it.  The config file location is taken from the
`JOTQUOTE_CONFIG` environment variable if set, otherwise
`~/.jotquote/settings.conf`.  Relative paths in the config (e.g.
`quote_file = ./quotes.txt`) are resolved to absolute paths relative to
the directory containing `settings.conf`.

The second tuple element is `True` when the legacy `[jotquote]` section
was detected and migrated in-memory to `[general]`/`[lint]`/`[web]`;
callers typically surface a deprecation warning in that case.

Raises [`ConfigError`](#configerror) if `quote_file` is missing from the
`[general]` section.

**Example:**

```python
from jotquote import api

config, migrated = api.get_config()
if migrated:
    print('warning: legacy [jotquote] section was migrated in memory')
print(config.get(api.SECTION_GENERAL, 'quote_file'))
```

---

#### `get_filename`

```python
get_filename() -> str
```

Return the resolved absolute path to the quote file from the loaded
config.  Raises [`ConfigError`](#configerror) if the file does not exist.

**Example:**

```python
from jotquote import api

path = api.get_filename()
quotes = api.read_quotes(path)
print(f'{len(quotes)} quotes in {path}')
```

---

### Quote storage

#### `read_quotes`

```python
read_quotes(filename: str) -> list[Quote]
```

Read all quotes from the given quote file, in file order.  Blank lines
and lines beginning with `#` are skipped.  Raises
[`StorageError`](#storageerror) if the file does not exist,
[`DuplicateQuoteError`](#duplicatequoteerror) if the file contains a
duplicate quote, or [`QuoteValidationError`](#quotevalidationerror) if a
line is malformed.

**Example:**

```python
from jotquote import api

quotes = api.read_quotes('/home/user/.jotquote/quotes.txt')
print(f'Loaded {len(quotes)} quotes')
for q in quotes[:3]:
    print(f'- {q.author}: {q.quote}')
```

---

#### `read_quotes_with_hash`

```python
read_quotes_with_hash(filename: str) -> tuple[list[Quote], str]
```

Read quotes and compute the file's SHA-256 hex digest in a single pass.
The hash is used as a cheap concurrency token: pair this with
[`write_quotes`](#write_quotes) (or [`set_quote`](#set_quote)) to detect
modifications by another process between read and write.

**Example — read-modify-write safely:**

```python
from jotquote import api

path = api.get_filename()
quotes, sha = api.read_quotes_with_hash(path)

for q in quotes:
    if q.author == 'Anonymous':
        q.set_tags(q.tags + ['needs_author'])

api.write_quotes(path, quotes, expected_sha256=sha)
```

---

#### `read_tags`

```python
read_tags(quotefile: str) -> list[str]
```

Return a sorted list of every unique tag used in the given quote file.

**Example:**

```python
from jotquote import api

tags = api.read_tags(api.get_filename())
print(f'{len(tags)} distinct tags: {", ".join(tags[:5])}...')
```

---

#### `parse_quotes`

```python
parse_quotes(
    rawlines: Iterable[str] | Iterable[bytes],
    filename: str,
    encoding: str | None = None,
    simple_format: bool = True,
) -> list[Quote]
```

Parse an iterable of raw lines into a list of [`Quote`](#quote) objects.
Blank lines and lines beginning with `#` are skipped.  The `filename`
argument is used only in error messages — it does not have to be a real
file path.  If `encoding` is given, each line is decoded first
(convenient when reading raw bytes).  `simple_format=True` uses the
hyphen format; `simple_format=False` uses the pipe-delimited format.
Each returned `Quote` has `line_number` set to its 1-based line number
in `rawlines`.

**Example:**

```python
from jotquote import api

# Parse quotes from a list of lines (e.g. user input pasted via stdin)
lines = [
    'The best way out is always through. | Robert Frost | A Servant to Servants | motivational',
    '# this is a comment and is skipped',
    '',
    'Onward. | Anonymous | | motivational',
]
quotes = api.parse_quotes(lines, '<stdin>', simple_format=False)
print([q.author for q in quotes])   # ['Robert Frost', 'Anonymous']
```

---

#### `add_quote`

```python
add_quote(filename: str, quote: Quote) -> int
```

Append a single quote to the given quote file.  Returns the total number
of quotes in the file after the add.  Raises
[`StorageError`](#storageerror) if the file does not exist, or
[`DuplicateQuoteError`](#duplicatequoteerror) if the quote is already
present.

**Example:**

```python
from jotquote import api

q = api.parse_quote('Onward. - Anonymous')
total = api.add_quote(api.get_filename(), q)
print(f'now {total} quotes in file')
```

---

#### `add_quotes`

```python
add_quotes(filename: str, newquotes: list[Quote]) -> int
```

Append a list of quotes to the given quote file.  Checks for duplicates
both among `newquotes` and against existing quotes before writing.
Returns the total number of quotes in the file after the append.  If
more than one process calls this function on the same file at the same
time, the results are undefined.

**Example:**

```python
from jotquote import api

new = [
    api.parse_quote('Onward. - Anonymous'),
    api.parse_quote('Carry on. - Anonymous'),
]
total = api.add_quotes(api.get_filename(), new)
print(f'added {len(new)}; file now contains {total} quotes')
```

---

#### `set_quote`

```python
set_quote(quotefile: str, line_num: int, quote: Quote, sha256: str) -> None
```

Replace the quote at `line_num` with `quote`.  Verifies the current
file's SHA-256 matches `sha256` before writing, to detect concurrent
modifications.  Raises
[`ConcurrentModificationError`](#concurrentmodificationerror) if the
checksum does not match, or
[`QuoteNotFoundError`](#quotenotfounderror) if `line_num` does not
identify an existing quote.  Typically used together with
[`read_quotes_with_hash`](#read_quotes_with_hash).

**Example:**

```python
from jotquote import api

path = api.get_filename()
quotes, sha = api.read_quotes_with_hash(path)

target = quotes[4]
updated = api.Quote(target.quote, 'Updated Author', target.publication, target.tags)
api.set_quote(path, target.line_number, updated, sha)
```

---

#### `settags`

```python
settags(
    quotefile: str,
    n: int | None,
    hash: str | None,
    newtags: list[str],
) -> None
```

Set the tags on the quote identified by 1-based position (`n`) or by
16-character hash (`hash`).  Exactly one of `n`/`hash` must be provided.
Pass `newtags=[]` to clear all tags.  Uses SHA-256 concurrency control
internally.  Raises `ValueError` if neither or both of `n`/`hash` are
provided, [`QuoteNotFoundError`](#quotenotfounderror) if the selector
does not match an existing quote, or
[`ConcurrentModificationError`](#concurrentmodificationerror) if the
file was modified concurrently.

**Example:**

```python
from jotquote import api

# Tag quote number 42 as motivational + short
api.settags(api.get_filename(), n=42, hash=None, newtags=['motivational', 'short'])

# Or by hash
api.settags(api.get_filename(), n=None, hash='a1b2c3d4e5f67890', newtags=['funny'])
```

---

#### `get_sha256`

```python
get_sha256(filename: str) -> str
```

Return the hex SHA-256 digest of the given file.

**Example:**

```python
from jotquote import api

print(api.get_sha256(api.get_filename()))
```

---

#### `write_quotes`

```python
write_quotes(
    quote_path: str,
    quotes: list[Quote],
    expected_sha256: str | None = None,
) -> None
```

Atomically overwrite `quote_path` with the given quotes.  The file is
written to a temporary file, sanity-checked against the existing
backup, backed up, then swapped in with `os.replace`.  If
`expected_sha256` is provided, the current file's SHA-256 is verified
to match it before writing.  If more than one process calls this
function on the same file at the same time, the results are undefined.

**Example — optimistic concurrency:**

```python
from jotquote import api

path = api.get_filename()
quotes, sha = api.read_quotes_with_hash(path)

# Drop every quote tagged 'draft'
quotes = [q for q in quotes if not q.has_tag('draft')]

api.write_quotes(path, quotes, expected_sha256=sha)
```

---

#### `format_quote`

```python
format_quote(quote: Quote) -> str
```

Format a [`Quote`](#quote) as a single pipe-delimited line — the exact
representation written to the quote file, minus the trailing newline.
Raises `TypeError` if the argument is not a `Quote`.

**Example:**

```python
from jotquote import api

q = api.Quote('Onward.', 'Anonymous', None, ['motivational'])
print(api.format_quote(q))
# Onward. | Anonymous |  | motivational
```

---

### Quote selection

#### `get_first_match`

```python
get_first_match(
    quotes: list[Quote],
    tags: str | None = None,
    keyword: str | None = None,
    number: int | None = None,
    hash_arg: str | None = None,
    rand: bool = False,
    excluded_tags: str | None = None,
) -> Quote | None
```

Filter `quotes` by the given criteria (AND logic) and return the first
match, or a random match if `rand=True`.  Returns `None` if no quote
matches.  `tags` and `excluded_tags` are comma-separated strings;
`hash_arg` is a 16-character hash prefix; `number` is a 1-based index
into `quotes`.

**Example:**

```python
from jotquote import api

quotes = api.read_quotes(api.get_filename())

# First motivational quote containing "journey"
q = api.get_first_match(quotes, tags='motivational', keyword='journey')
if q is not None:
    print(q.quote)

# A random quote with the 'poetry' tag, excluding anything tagged 'draft'
q = api.get_first_match(quotes, tags='poetry', excluded_tags='draft', rand=True)
```

---

#### `get_random_choice`

```python
get_random_choice(numquotes: int) -> int
```

Return a deterministic quote index for today's date, in the range
`[0, numquotes - 1]`.  The same value is returned for any call on the
same day; after 11:45 PM local time the value advances to the next day
so caches expiring at midnight already contain the next day's quote.

**Example:**

```python
from jotquote import api

quotes = api.read_quotes(api.get_filename())
index = api.get_random_choice(len(quotes))
print('today\'s quote:', quotes[index].quote)
```

---

### Linting

#### `lint_quotes`

```python
lint_quotes(
    quotes: list[Quote],
    checks: Iterable[str],
    config: configparser.ConfigParser,
) -> list[LintIssue]
```

Run the named lint checks against `quotes` and return every
[`LintIssue`](#lintissue) found.  Unknown check names in `checks` are
silently ignored.  Per-check options are read from the `[lint]` section
of `config`.

Available checks: `smart-quotes`, `smart-dashes`, `double-spaces`,
`quote-too-long`, `no-tags`, `no-author`, `required-tag-group`.
The full set is available as `api.ALL_CHECKS`.

**Example:**

```python
from jotquote import api

config, _ = api.get_config()
quotes = api.read_quotes(api.get_filename())

issues = api.lint_quotes(quotes, ['smart-quotes', 'smart-dashes'], config)
print(f'{len(issues)} issues found')
for issue in issues:
    print(f'  line {issue.line_number} [{issue.check}/{issue.field}] {issue.message}')
```

---

#### `apply_fixes`

```python
apply_fixes(
    quotes: list[Quote],
    issues: list[LintIssue],
) -> tuple[list[Quote], int]
```

Apply every auto-fixable issue to the matching quote, in place.
Non-fixable issues are ignored.  Returns `(quotes, fix_count)` where
`quotes` is the same list passed in (now mutated) and `fix_count` is
the number of fixes that were applied.

**Example — fix smart quotes / dashes / double spaces and save:**

```python
from jotquote import api

config, _ = api.get_config()
path = api.get_filename()
quotes, sha = api.read_quotes_with_hash(path)

issues = api.lint_quotes(quotes, ['smart-quotes', 'smart-dashes', 'double-spaces'], config)
quotes, fixed = api.apply_fixes(quotes, issues)
print(f'applied {fixed} fixes')

if fixed:
    api.write_quotes(path, quotes, expected_sha256=sha)
```

---

### Exceptions

All user-facing errors raised by `jotquote.api` are subclasses of a
single base class, [`ApiException`](#apiexception).  Callers that want to
handle any API error uniformly can catch the base class; callers that
need to react to a specific condition can catch one of the concrete
subclasses.

```
ApiException
├── ConfigError
├── QuoteValidationError
├── QuoteNotFoundError
├── DuplicateQuoteError
├── ConcurrentModificationError
└── StorageError
```

Programmer-misuse conditions (passing the wrong type for an argument,
calling a function with mutually exclusive options) raise standard
`TypeError` or `ValueError` and are not part of `ApiException` — they
indicate a bug in the caller rather than a condition to recover from.

**Example — react specifically to a concurrent modification:**

```python
from jotquote import api

path = api.get_filename()
quotes, sha = api.read_quotes_with_hash(path)

target = quotes[0]
updated = api.Quote(target.quote, 'Updated Author', target.publication, target.tags)

try:
    api.set_quote(path, target.line_number, updated, sha)
except api.ConcurrentModificationError as e:
    print(f'file was changed on disk (expected {e.expected_sha256}, got {e.current_sha256}); reload and retry')
except api.ApiException as e:
    print(f'save failed: {e}')
```

---

#### `ApiException`

Base class for all user-facing errors raised by `jotquote.api`.
Subclasses `Exception`.

Use this when you want to catch any API error without caring which
specific condition triggered it:

```python
from jotquote import api

try:
    api.add_quote(api.get_filename(), api.parse_quote('Onward. - Anon.'))
except api.ApiException as e:
    print(f'could not add quote: {e}')
```

---

#### `ConfigError`

Raised for problems loading or interpreting `settings.conf`.  Subclasses
[`ApiException`](#apiexception).

Raised by [`get_config`](#get_config) when required properties are
missing, by [`get_filename`](#get_filename) when the configured quote
file does not exist, and by [`write_quotes`](#write_quotes) when the
configured `line_separator` value is invalid.

---

#### `QuoteValidationError`

Raised when parsing a quote, tag, or field fails validation.  Subclasses
[`ApiException`](#apiexception).

**Attributes:**

| Attribute | Type             | Description                                                                                             |
|-----------|------------------|---------------------------------------------------------------------------------------------------------|
| `field`   | `str` \| `None`  | The field that failed validation — one of `'quote'`, `'author'`, `'publication'`, `'tags'`, or `None`.  |

`field` is `None` for structural errors that aren't tied to a single
field (e.g. wrong number of pipe separators).

Raised by [`parse_quote`](#parse_quote), [`parse_tags`](#parse_tags),
[`Quote`](#quote) construction (for forbidden characters), and
[`read_quotes`](#read_quotes) / [`parse_quotes`](#parse_quotes) when a
line is malformed.

---

#### `QuoteNotFoundError`

Raised when a quote selector (line number, hash) matches no quote.
Subclasses [`ApiException`](#apiexception).

Raised by [`settags`](#settags) when the selector is out of range or the
hash is unknown, and by [`set_quote`](#set_quote) when `line_num` does
not identify an existing quote.

---

#### `DuplicateQuoteError`

Raised when adding a quote that is already present in the file.
Subclasses [`ApiException`](#apiexception).

Raised by [`add_quote`](#add_quote), [`add_quotes`](#add_quotes), and
[`read_quotes`](#read_quotes).

---

#### `ConcurrentModificationError`

Raised when the quote file's SHA-256 on disk no longer matches the hash
the caller passed in.  Subclasses [`ApiException`](#apiexception).

**Attributes:**

| Attribute         | Type             | Description                                                                        |
|-------------------|------------------|------------------------------------------------------------------------------------|
| `expected_sha256` | `str`            | The SHA-256 the caller expected the file to have.                                  |
| `current_sha256`  | `str` \| `None`  | The current SHA-256 of the file on disk, or `None` if it could not be determined.  |

Raised by [`set_quote`](#set_quote) and [`write_quotes`](#write_quotes)
when the SHA-256 check fails.  Callers should re-read the file and
re-apply their changes.

---

#### `StorageError`

Raised for I/O failures, missing quote files, and backup sanity
failures.  Subclasses [`ApiException`](#apiexception).

Raised by [`read_quotes`](#read_quotes),
[`read_quotes_with_hash`](#read_quotes_with_hash),
[`add_quotes`](#add_quotes), and [`write_quotes`](#write_quotes).
