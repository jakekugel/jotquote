# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
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
[jotquote]
quote_file = {quote_file}
web_port = {port}
web_ip = 127.0.0.1
line_separator = platform
{extra}"""


def _make_env(tmp_path, quote_file, **extra_props):
    """Build a settings.conf in tmp_path and return a subprocess env dict."""
    extra = '\n'.join('{} = {}'.format(k, v) for k, v in extra_props.items())
    jotquote_dir = tmp_path / '.jotquote'
    jotquote_dir.mkdir()
    conf_path = jotquote_dir / 'settings.conf'
    conf_path.write_text(
        SETTINGS_CONF_TEMPLATE.format(quote_file=str(quote_file), port=TEST_PORT, extra=extra),
        encoding='utf-8',
    )
    env = os.environ.copy()
    env['HOME'] = str(tmp_path)
    env['USERPROFILE'] = str(tmp_path)
    env['PYTHONUNBUFFERED'] = '1'
    return env


def _copy_quotes(tmp_path):
    """Copy a test quote fixture into tmp_path and return the path."""
    src = os.path.join(os.path.dirname(__file__), 'testdata', 'quotes1.txt')
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


def _start_review_server(tmp_path, quote_file, env):
    """Launch the web_review server and return (proc, stderr_lines)."""
    cmd = [sys.executable, '-c',
           "from waitress import serve; from jotquote.web_review import app; "
           "serve(app, host='127.0.0.1', port={})".format(TEST_PORT)]
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
            'Server did not start within timeout.\n'
            'Process exit code: {}\n'
            'Server stderr:\n{}'.format(exit_code, stderr_dump)
        )


def test_get_index(tmp_path):
    """GET / returns HTTP 200 with the jotquote page title."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_review_server(tmp_path, quote_file, env)
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
    """GET / response contains radio groups for stars/visibility and a textarea for other tags."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_review_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')
        # Star rating radio group
        assert 'name="star_tag"' in body
        assert 'value="1star"' in body
        assert 'value="5stars"' in body
        # Visibility radio group
        assert 'name="visibility_tag"' in body
        assert 'value="personal"' in body
        assert 'value="public"' in body
        # Other tags textarea — quotes1.txt has the "U" tag on all quotes
        assert 'name="other_tags"' in body
        assert '>U<' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_page_title_config(tmp_path):
    """web_page_title config value appears in the HTML <title> tag."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, web_page_title='My Review')
    proc, stderr_lines = _start_review_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')
        assert '<title>My Review</title>' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_post_settags(tmp_path):
    """POST /settags updates tags on the quote and redirects to /."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_review_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)

        # Get the page first to find the hidden hash field
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')

        # Extract the hash value from the hidden input
        import re
        match = re.search(r'<input type="hidden" name="hash" value="([0-9a-f]+)">', body)
        assert match, 'Could not find hash hidden input in response body'
        hash_val = match.group(1)

        # POST to /settags with a new tag via the other_tags textarea
        post_data = urllib.parse.urlencode({'hash': hash_val, 'other_tags': 'newtag'}).encode('utf-8')
        req = urllib.request.Request(
            'http://127.0.0.1:{}/settags'.format(TEST_PORT),
            data=post_data,
            method='POST',
        )
        # urllib follows redirects by default (302 → GET /), so we get the final page
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200

        # Verify the quote file was updated
        from jotquote import api
        quotes = api.read_quotes(str(quote_file))
        updated = [q for q in quotes if q.get_hash() == hash_val]
        assert updated, 'Quote with hash {} not found after POST'.format(hash_val)
        assert 'newtag' in updated[0].tags
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_no_matching_quote(tmp_path):
    """GET / with an empty quote file returns 200 with 'No matching quote found'."""
    quote_file = tmp_path / 'empty_quotes.txt'
    quote_file.write_text('', encoding='utf-8')
    env = _make_env(tmp_path, quote_file)
    proc, stderr_lines = _start_review_server(tmp_path, quote_file, env)
    try:
        _assert_server_started(proc, stderr_lines)
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode('utf-8')
        assert 'No matching quote found' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)
