# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

TEST_PORT = 15545
TEST_URL = 'http://127.0.0.1:{}/'.format(TEST_PORT)


SETTINGS_CONF_TEMPLATE = """\
[general]
quote_file = {quote_file}
line_separator = platform
{general_extra}

[lint]
{lint_extra}

[web]
port = {port}
ip = 127.0.0.1
{web_extra}"""

_GENERAL_KEYS = {'show_author_count'}
_WEB_NO_PREFIX = {'header_provider', 'quote_resolver'}


def _make_env(tmp_path, quote_file, **extra_props):
    """Build a settings.conf in tmp_path and return a subprocess env dict."""
    general_lines = []
    lint_lines = []
    web_lines = []
    for k, v in extra_props.items():
        if k in _GENERAL_KEYS:
            general_lines.append('{} = {}'.format(k, v))
        elif k in _WEB_NO_PREFIX:
            web_lines.append('{} = {}'.format(k, v))
        elif k.startswith('lint_'):
            lint_lines.append('{} = {}'.format(k[5:], v))
        elif k.startswith('web_'):
            web_lines.append('{} = {}'.format(k[4:], v))
        else:
            general_lines.append('{} = {}'.format(k, v))
    jotquote_dir = tmp_path / '.jotquote'
    jotquote_dir.mkdir()
    conf_path = jotquote_dir / 'settings.conf'
    conf_path.write_text(
        SETTINGS_CONF_TEMPLATE.format(
            quote_file=str(quote_file),
            port=TEST_PORT,
            general_extra='\n'.join(general_lines),
            lint_extra='\n'.join(lint_lines),
            web_extra='\n'.join(web_lines),
        ),
        encoding='utf-8',
    )
    env = os.environ.copy()
    env['HOME'] = str(tmp_path)
    env['USERPROFILE'] = str(tmp_path)
    env['PYTHONUNBUFFERED'] = '1'
    return env


def _copy_quotes(tmp_path):
    """Copy a test quote fixture into tmp_path and return the path."""
    src = os.path.join(os.path.dirname(__file__), '..', 'testdata', 'quotes1.txt')
    dst = tmp_path / 'quotes1.txt'
    shutil.copy(src, dst)
    return dst


def _collect_stderr(proc, lines):
    """Read lines from proc.stderr into lines list (runs in a background thread)."""
    for line in proc.stderr:
        lines.append(line.decode('utf-8', errors='replace').rstrip())


def wait_for_server(url, timeout=15):
    """Poll url until it returns HTTP 200 or timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def wait_for_log_line(lines, expected, timeout=5):
    """Poll lines list until a line containing expected is found or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(expected in line for line in lines):
            return True
        time.sleep(0.1)
    return False


def _start_editor_server(tmp_path, quote_file, env):
    """Launch the web_editor server and return (proc, stderr_lines)."""
    cmd = [
        sys.executable,
        '-c',
        "from waitress import serve; from jotquote.web_editor import app; serve(app, host='127.0.0.1', port={})".format(
            TEST_PORT
        ),
    ]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    return proc, stderr_lines


def _assert_server_started(proc, stderr_lines):
    """Wait for the server to start and provide diagnostic output on failure."""
    if not wait_for_server(TEST_URL):
        time.sleep(1)  # let stderr accumulate
        exit_code = proc.poll()
        stderr_dump = '\n'.join(stderr_lines) or '(no stderr captured)'
        pytest.fail(
            'Server did not start within timeout.\nProcess exit code: {}\nServer stderr:\n{}'.format(
                exit_code, stderr_dump
            )
        )


def test_get_index(tmp_path):
    """GET / returns HTTP 200 with the jotquote page title."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_editor_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode('utf-8')
        assert '<title>jotquote</title>' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_tags_displayed(tmp_path):
    """GET / response contains a tags textarea with the tag value."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_editor_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')
        assert 'name="tags"' in body
        assert '>U<' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_page_title_config(tmp_path):
    """web_page_title config value appears in the HTML <title> tag."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, web_page_title='My Editor')
    proc, stderr_lines = _start_editor_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')
        assert '<title>My Editor</title>' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_post_save_quote(tmp_path):
    """POST /<line_num> updates the quote in the file and redirects to /."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_editor_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)

        # Get the page to find line_number and sha256
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')

        line_num_match = re.search(r'action="/(\d+)"', body)
        assert line_num_match, 'Could not find form action with line number'
        line_num = line_num_match.group(1)

        sha256_match = re.search(r'name="sha256" value="([0-9a-f]+)"', body)
        assert sha256_match, 'Could not find sha256 hidden input'
        sha256 = sha256_match.group(1)

        # POST to save updated quote
        post_data = urllib.parse.urlencode(
            {
                'quote': 'Updated integration quote',
                'author': 'Test Author',
                'publication': '',
                'tags': 'newtag',
                'sha256': sha256,
            }
        ).encode('utf-8')
        req = urllib.request.Request(
            'http://127.0.0.1:{}/{}'.format(TEST_PORT, line_num),
            data=post_data,
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200  # follows redirect to /

        # Verify file was updated
        from jotquote import api

        quotes = api.read_quotes(str(quote_file))
        updated = [q for q in quotes if q.quote == 'Updated integration quote']
        assert updated, 'Updated quote not found in file'
        assert 'newtag' in updated[0].tags
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_no_matching_quote(tmp_path):
    """GET / with an empty quote file returns 200 with 'No matching quote found'."""
    quote_file = tmp_path / 'empty_quotes.txt'
    quote_file.write_text('', encoding='utf-8')
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_editor_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode('utf-8')
        assert 'No matching quote found' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_editor_table_structure(tmp_path):
    """GET / renders a three-column editor table."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_editor_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')
        assert 'class="editor-table"' in body
        assert 'name="quote"' in body
        assert 'name="author"' in body
        assert 'name="publication"' in body
        assert 'name="tags"' in body
        assert 'id="save-btn"' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_sha256_mismatch_error(tmp_path):
    """POST with a stale SHA256 displays an error message."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_editor_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)

        # Get the page to find line_number
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')

        line_num_match = re.search(r'action="/(\d+)"', body)
        assert line_num_match, 'Could not find form action with line number'
        line_num = line_num_match.group(1)

        # POST with bogus sha256
        post_data = urllib.parse.urlencode(
            {
                'quote': 'Some quote',
                'author': 'Some Author',
                'publication': '',
                'tags': '',
                'sha256': 'bogus_sha256',
            }
        ).encode('utf-8')
        req = urllib.request.Request(
            'http://127.0.0.1:{}/{}'.format(TEST_PORT, line_num),
            data=post_data,
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode('utf-8')
        assert 'modified since it was last read' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_lint_issues_displayed(tmp_path):
    """Lint issues appear in the editor page."""
    # Create a quote file with a tagless quote to trigger no-tags check
    quote_file = tmp_path / 'quotes.txt'
    quote_file.write_text('A test quote|Test Author||\n', encoding='utf-8')
    env = _make_env(tmp_path, quote_file, lint_enabled_checks='no-tags')
    proc, stderr_lines = _start_editor_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')
        assert 'lint-error' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)
