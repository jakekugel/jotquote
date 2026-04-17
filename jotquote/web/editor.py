# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import logging

import click
from flask import Flask, abort, redirect, render_template, request

from jotquote import api
from jotquote.api import lint
from jotquote.web import helpers as web_helpers

app = Flask(__name__)

# Configure the root logger at module load time so the format applies regardless
# of whether the app is launched via 'jotquote webeditor' or a WSGI server directly.
web_helpers.configure_logging()

# Named logger for HTTP access lines; propagates to the root handler configured above.
_access_logger = logging.getLogger('jotquote.access')
_access_logger.setLevel(logging.INFO)

_lint_cache = {'sha256': None, 'checks': None, 'issues': []}


@app.after_request
def log_request(response):
    """Log the HTTP method, path, and status code for each request.

    Args:
        response (flask.wrappers.Response): The Flask response object.

    Returns:
        flask.wrappers.Response: The unmodified response object.
    """
    _access_logger.info(
        '%s %s %s',
        request.method,
        web_helpers.sanitize_for_log(request.full_path.rstrip('?')),
        response.status_code,
    )
    return response


@app.route('/', methods=['GET'])
def index():
    """Render the editor page for the first quote in the collection.

    Returns:
        str: Rendered HTML for the editor page, or a fallback message if no quotes exist.
    """
    config, quotes = _load_quotes()
    quote = api.get_first_match(quotes, excluded_tags=None, rand=False)
    if quote is None:
        return '<p>No matching quote found.</p>', 200
    return _render_editor(config, quotes, quote)


@app.route('/<int:line_num>', methods=['GET'])
def show_quote(line_num):
    """Render the editor page for the quote at the given line number.

    Args:
        line_num (int): Line number identifying the quote in the quote file.

    Returns:
        str: Rendered HTML for the editor page, or 404 if no quote matches.
    """
    config, quotes = _load_quotes()
    matched = [q for q in quotes if q.get_line_number() == line_num]
    if not matched:
        abort(404)
    return _render_editor(config, quotes, matched[0])


@app.route('/<int:line_num>', methods=['POST'])
def save_quote(line_num):
    """Save an edited quote and redirect to the index, or re-render with errors.

    Reads form data, constructs a Quote, and attempts to write it to the quote
    file.  On success, redirects to ``/``.  On failure, re-renders the editor
    with the validation error and the user's unsaved edits.

    Args:
        line_num (int): Line number of the quote being edited.

    Returns:
        werkzeug.wrappers.Response: A redirect on success, or rendered HTML on error.
    """
    # Load config and determine the quote file path
    config, _ = _load_quotes()
    quotefile = config.get(api.SECTION_GENERAL, 'quote_file')

    # Read form fields from the POST body
    quote_text = request.form.get('quote', '')
    author = request.form.get('author', '')
    publication = request.form.get('publication', '')
    tags_raw = request.form.get('tags', '')
    sha256 = request.form.get('sha256', '')

    # Parse the comma-separated tags string into a list
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()]

    # Attempt to save; redirect back to the quote on success
    try:
        quote_obj = api.Quote(quote_text, author, publication if publication else None, tags)
        api.set_quote(quotefile, line_num, quote_obj, sha256)
        return redirect(f'/{line_num}')
    # Save failed — re-render using the cached lint issues for this quote
    except click.ClickException as e:
        checks = web_helpers.get_enabled_checks(config)
        quotes = api.read_quotes(quotefile)
        all_issues = _get_lint_issues(quotes, checks, config, sha256)
        lint_issues = [issue for issue in all_issues if issue.line_number == line_num]
        return _render_editor(
            config,
            quotes,
            quote_obj,
            line_number=line_num,
            error=e.format_message(),
            lint_issues=lint_issues,
        )


def run_server():
    """Start the web editor using Waitress as the WSGI server.

    This function is called when the 'jotquote webeditor' command is used.
    Waitress is used as the WSGI server, which is suitable for local use.
    The host and port are read from the [web] section of settings.conf
    (editor_ip and editor_port properties).

    Alternatively, any WSGI server can be pointed directly at the 'app' object
    exported from this module.  For example:

        waitress-serve --host 127.0.0.1 --port 5545 jotquote.web.editor:app
        gunicorn --bind 127.0.0.1:5545 jotquote.web.editor:app  (Linux/Mac only)

    When using a WSGI server directly, this function is not called and the
    WSGI server determines the host and port.  Logging is configured at module
    load time, so the format applies regardless of launch method.

    Returns:
        None
    """

    # Read host and port from config, applying defaults if not set
    config, _ = api.get_config()
    listen_port = config.get(api.SECTION_WEB, 'editor_port', fallback='')
    listen_ip = config.get(api.SECTION_WEB, 'editor_ip', fallback='')

    if not listen_port:
        listen_port = 5545

    if not listen_ip:
        listen_ip = '127.0.0.1'

    # Start the Waitress WSGI server
    from waitress import serve

    serve(app, host=listen_ip, port=int(listen_port))


def _load_quotes():
    """Load config and quotes from the quote file.

    Returns:
        tuple[configparser.ConfigParser, list[api.Quote]]: The config object and list of quotes.
    """
    config, _ = api.get_config()
    quotefile = config.get(api.SECTION_GENERAL, 'quote_file')
    quotes = api.read_quotes(quotefile)
    return config, quotes


def _get_lint_issues(quotes, checks, config, sha256):
    """Return cached lint issues if SHA-256 and checks match, else re-lint.

    Args:
        quotes (list[api.Quote]): All quotes to lint.
        checks (frozenset[str]): The set of lint checks to run.
        config (configparser.ConfigParser): Application config.
        sha256 (str): SHA-256 hash of the quote file for cache invalidation.

    Returns:
        list[lint.LintIssue]: Lint issues found across all quotes.
    """
    # Return cached result if the file content and checks haven't changed
    frozen_checks = frozenset(checks)
    if _lint_cache['sha256'] == sha256 and _lint_cache['checks'] == frozen_checks:
        return _lint_cache['issues']

    # Cache miss — re-lint all quotes and store the updated result
    issues = lint.lint_quotes(quotes, checks, config)
    _lint_cache['sha256'] = sha256
    _lint_cache['checks'] = frozen_checks
    _lint_cache['issues'] = issues
    return issues


def _error_nav(quotes, idx, all_issues):
    """Return (prev_error_line_num, next_error_line_num) for quotes around position idx.

    Args:
        quotes (list[api.Quote]): All quotes in the collection.
        idx (int): Index of the current quote in the list.
        all_issues (list[lint.LintIssue]): All lint issues across quotes.

    Returns:
        tuple[int | None, int | None]: Line numbers of the previous and next quotes with
            lint errors, or None if there is no such quote in that direction.
    """
    # Find the indices of all quotes that have lint errors
    error_line_nums = {issue.line_number for issue in all_issues}
    error_indices = [i for i, q in enumerate(quotes) if q.get_line_number() in error_line_nums]

    # Find the nearest error before and after the current position
    prev_error_idx = next((i for i in reversed(error_indices) if i < idx), None)
    next_error_idx = next((i for i in error_indices if i > idx), None)

    # Resolve indices to line numbers for the template
    prev = quotes[prev_error_idx].get_line_number() if prev_error_idx is not None else None
    nxt = quotes[next_error_idx].get_line_number() if next_error_idx is not None else None
    return prev, nxt


def _render_editor(config, quotes, quote, line_number=None, error=None, lint_issues=None):
    """Render the editor page for the given quote.

    Args:
        config (configparser.ConfigParser): Application config.
        quotes (list[api.Quote]): All quotes in the collection (used for navigation).
        quote (api.Quote): The quote to display in the editor.
        line_number (int | None): Explicit line number override.  When None, uses
            ``quote.get_line_number()``.  Needed when the quote was constructed from
            form data and does not carry a file line number.
        error (str | None): An error message to display, or None for no error.
        lint_issues (list[lint.LintIssue] | None): Pre-computed lint issues for the
            current quote.  When None, issues are computed from the full quote list.

    Returns:
        str: Rendered HTML for the editor page.
    """
    # Resolve line number from the quote object if not provided explicitly
    if line_number is None:
        line_number = quote.get_line_number()

    # Read page config: title, theme colors, enabled checks, and file hash
    page_title = config.get(api.SECTION_WEB, 'page_title', fallback='jotquote')
    colors = web_helpers.get_color_config(config)
    quotefile = config.get(api.SECTION_GENERAL, 'quote_file')
    checks = web_helpers.get_enabled_checks(config)
    sha256 = api.get_sha256(quotefile)

    # Determine the current quote's position and adjacent quote line numbers
    matched = [i for i, q in enumerate(quotes) if q.get_line_number() == line_number]
    idx = matched[0] if matched else None
    totalquotes = len(quotes)
    quotenum = idx + 1 if idx is not None else None
    prev_line_num = quotes[idx - 1].get_line_number() if idx is not None and idx > 0 else None
    next_line_num = quotes[idx + 1].get_line_number() if idx is not None and idx < totalquotes - 1 else None

    # Compute lint issues for the current quote and error-navigation targets
    all_issues = _get_lint_issues(quotes, checks, config, sha256)
    if lint_issues is None:
        lint_issues = [issue for issue in all_issues if issue.line_number == line_number]
    prev_error_line_num, next_error_line_num = _error_nav(quotes, idx if idx is not None else 0, all_issues)

    # Render the editor template with all computed values
    return render_template(
        'editor.html',
        quote=quote.quote,
        author=quote.author,
        publication=quote.publication,
        tags=quote.tags,
        line_number=line_number,
        page_title=page_title,
        lint_issues=lint_issues,
        sha256=sha256,
        quotenum=quotenum,
        totalquotes=totalquotes,
        prev_line_num=prev_line_num,
        next_line_num=next_line_num,
        prev_error_line_num=prev_error_line_num,
        next_error_line_num=next_error_line_num,
        error=error,
        **colors,
    )
