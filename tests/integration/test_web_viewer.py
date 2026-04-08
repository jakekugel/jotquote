# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

TEST_PORT = 15544
TEST_URL = 'http://127.0.0.1:{}/'.format(TEST_PORT)

# Derive script paths from the running Python's venv (avoids nested `uv run` buffering).
_SCRIPTS_DIR = os.path.dirname(sys.executable)


def _script(name):
    """Return the absolute path to a script in the current venv's Scripts/bin directory."""
    candidates = [name + '.exe', name] if sys.platform == 'win32' else [name]
    for candidate in candidates:
        path = os.path.join(_SCRIPTS_DIR, candidate)
        if os.path.exists(path):
            return path
    return name  # fall back to PATH lookup


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
_WEB_NO_PREFIX = {'quotemap_file'}


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


def _assert_response(url):
    with urllib.request.urlopen(url, timeout=5) as resp:
        assert resp.status == 200
        body = resp.read().decode('utf-8')
    assert '<title>jotquote</title>' in body


def _run_server_test(tmp_path, cmd, startup_log):
    """Start a server subprocess, verify it serves and logs correctly, then tear down."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), 'Server did not start within timeout'
        _assert_response(TEST_URL)
        assert wait_for_log_line(stderr_lines, startup_log), 'Expected startup message in stderr; got: {}'.format(
            stderr_lines
        )
        assert wait_for_log_line(stderr_lines, 'GET / 200'), 'Expected access log entry in stderr; got: {}'.format(
            stderr_lines
        )
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_webserver_command(tmp_path):
    """jotquote webserver starts, serves a valid HTML page, and logs to stderr."""
    _run_server_test(
        tmp_path,
        cmd=[_script('jotquote'), 'webserver'],
        startup_log='Serving on http://127.0.0.1:{}'.format(TEST_PORT),
    )


def test_waitress_serve_command(tmp_path):
    """waitress-serve starts, serves the jotquote WSGI app, and logs to stderr."""
    _run_server_test(
        tmp_path,
        cmd=[
            _script('waitress-serve'),
            '--host',
            '127.0.0.1',
            '--port',
            str(TEST_PORT),
            'jotquote.web_viewer:app',
        ],
        startup_log='Serving on http://127.0.0.1:{}'.format(TEST_PORT),
    )


def test_web_page_title(tmp_path):
    """jotquote webserver uses web_page_title from config as the HTML page title."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, web_page_title='My Quotes')

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), 'Server did not start within timeout'
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')
        assert '<title>My Quotes</title>' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_stars_displayed(tmp_path):
    """Stars are rendered in the HTML when the daily quote has a star tag."""
    quote_file = tmp_path / 'quotes_stars.txt'
    quote_file.write_text('A great quote | Famous Author | | 3stars\n', encoding='utf-8')
    env = _make_env(tmp_path, quote_file, web_show_stars='true')

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), 'Server did not start within timeout'
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode('utf-8')
        assert '\u2605\u2605\u2605\u2606\u2606' in body  # ★★★☆☆
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_static_asset_cache_header(tmp_path):
    """Static assets served by the webserver include a long Cache-Control max-age."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), 'Server did not start within timeout'
        url = TEST_URL.rstrip('/') + '/static/fonts/OpenSans-Regular.ttf'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            cc = resp.headers.get('Cache-Control', '')
        assert 'max-age=86400' in cc
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.mark.skipif(sys.platform == 'win32', reason='gunicorn not supported on Windows')
def test_gunicorn_launch(tmp_path):
    """gunicorn starts, serves the jotquote WSGI app, and logs to stderr (Linux/Mac only)."""
    _run_server_test(
        tmp_path,
        cmd=[
            _script('gunicorn'),
            '--bind',
            '127.0.0.1:{}'.format(TEST_PORT),
            'jotquote.web_viewer:app',
        ],
        startup_log='Listening at: http://127.0.0.1:{}'.format(TEST_PORT),
    )


def test_quotemap_date_route(tmp_path):
    """Webserver with quotemap configured serves the mapped quote for /<date>."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = tmp_path / 'quotemap.txt'
    # 25382c2519fb23bd is the hash for the Ben Franklin quote in quotes1.txt
    quotemap_file.write_text('20260319: 25382c2519fb23bd\n', encoding='utf-8')
    env = _make_env(tmp_path, quote_file, quotemap_file=str(quotemap_file))

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), 'Server did not start within timeout'
        url = TEST_URL.rstrip('/') + '/20260319'
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode('utf-8')
        assert 'Ben Franklin' in body
        assert 'March 19, 2026' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_quotemap_root_permalink(tmp_path):
    """Webserver with quotemap containing today's date shows permalink on /."""
    quote_file = _copy_quotes(tmp_path)
    today = datetime.datetime.now().strftime('%Y%m%d')
    quotemap_file = tmp_path / 'quotemap.txt'
    quotemap_file.write_text('{}: 25382c2519fb23bd\n'.format(today), encoding='utf-8')
    env = _make_env(tmp_path, quote_file, quotemap_file=str(quotemap_file))

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), 'Server did not start within timeout'
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode('utf-8')
        assert 'Ben Franklin' in body
        assert 'permalink' in body
        assert '/{}'.format(today) in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


_LEGACY_TEST_PORT = 5544
_LEGACY_TEST_URL = 'http://127.0.0.1:{}/'.format(_LEGACY_TEST_PORT)


def test_legacy_jotquote_section_warns_on_web_start(tmp_path):
    """Web server with legacy [jotquote] config starts successfully and logs a deprecation warning."""
    # Copy the legacy config template to the jotquote config directory
    jotquote_dir = tmp_path / '.jotquote'
    jotquote_dir.mkdir()
    templates_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'jotquote', 'templates'))
    shutil.copy(os.path.join(templates_dir, 'settings.legacy.conf'), jotquote_dir / 'settings.conf')

    # Copy the quote fixture so the relative quote_file path resolves correctly
    src = os.path.join(os.path.dirname(__file__), '..', 'testdata', 'quotes1.txt')
    shutil.copy(src, jotquote_dir / 'quotes.txt')

    env = os.environ.copy()
    env['HOME'] = str(tmp_path)
    env['USERPROFILE'] = str(tmp_path)
    env['PYTHONUNBUFFERED'] = '1'

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(_LEGACY_TEST_URL), 'Server did not start within timeout'
        with urllib.request.urlopen(_LEGACY_TEST_URL, timeout=5) as resp:
            assert resp.status == 200
        assert wait_for_log_line(stderr_lines, 'deprecated', timeout=5), (
            'Expected deprecation warning in stderr; got: {}'.format(stderr_lines)
        )
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_web_theme_colors_config(tmp_path):
    """Custom theme colors from settings.conf appear in the rendered HTML."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(
        tmp_path,
        quote_file,
        web_dark_foreground_color='#aabbcc',
        web_dark_background_color='#112233',
        web_light_foreground_color='#334455',
        web_light_background_color='#eeddcc',
    )

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), 'Server did not start within timeout'
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode('utf-8')
        assert '#aabbcc' in body
        assert '#112233' in body
        assert '#334455' in body
        assert '#eeddcc' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_expires_at_in_server_log(tmp_path):
    """Server access log includes expires_at= for root route requests."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), 'Server did not start within timeout'
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            assert resp.status == 200
        assert wait_for_log_line(stderr_lines, 'expires_at='), 'Expected expires_at in stderr; got: {}'.format(
            stderr_lines
        )
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_about_page(tmp_path):
    """jotquote webserver serves the /about page when the about property is configured."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, web_about='Test about text')

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), 'Server did not start within timeout'

        # About page should return 200 and contain the configured text
        about_url = TEST_URL.rstrip('/') + '/about'
        with urllib.request.urlopen(about_url, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode('utf-8')
        assert 'Test about text' in body

        # Root page should contain the @ button linking to /about
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode('utf-8')
        assert 'href="/about"' in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)
