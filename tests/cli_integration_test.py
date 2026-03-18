# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

# Derive script paths from the running Python's venv (avoids nested `uv run` buffering).
_SCRIPTS_DIR = os.path.dirname(sys.executable)

CLI_TEST_PORT = 15545


def _script(name):
    """Return the absolute path to a script in the current venv's Scripts/bin directory."""
    candidates = [name + '.exe', name] if sys.platform == 'win32' else [name]
    for candidate in candidates:
        path = os.path.join(_SCRIPTS_DIR, candidate)
        if os.path.exists(path):
            return path
    return name  # fall back to PATH lookup


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
    jotquote_dir.mkdir(exist_ok=True)
    conf_path = jotquote_dir / 'settings.conf'
    conf_path.write_text(
        SETTINGS_CONF_TEMPLATE.format(quote_file=str(quote_file), port=CLI_TEST_PORT, extra=extra),
        encoding='utf-8',
    )
    env = os.environ.copy()
    env['HOME'] = str(tmp_path)
    env['USERPROFILE'] = str(tmp_path)
    env['PYTHONUNBUFFERED'] = '1'
    return env


def _copy_quotes(tmp_path):
    """Copy quotes1.txt fixture into tmp_path and return the path."""
    src = os.path.join(os.path.dirname(__file__), 'testdata', 'quotes1.txt')
    dst = tmp_path / 'quotes1.txt'
    shutil.copy(src, dst)
    return dst


def _wait_for_server(url, timeout=15):
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


def _collect_stderr(proc, lines):
    """Read lines from proc.stderr into lines list (runs in a background thread)."""
    for line in proc.stderr:
        lines.append(line.decode('utf-8', errors='replace').rstrip())


def test_ascii_only(tmp_path):
    """jotquote add fails with non-zero exit when ascii_only=true and quote has non-ASCII char."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, ascii_only='true')

    result = subprocess.run(
        [_script('jotquote'), 'add', 'Hello\u200aWorld - Some Author'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode != 0
    output = result.stdout.decode('utf-8', errors='replace') + result.stderr.decode('utf-8', errors='replace')
    assert 'non-ASCII' in output


def test_web_cache_minutes(tmp_path):
    """jotquote webserver respects web_cache_minutes config: max-age capped at 1 minute."""
    url = 'http://127.0.0.1:{}/'.format(CLI_TEST_PORT)
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, web_cache_minutes='1')

    proc = subprocess.Popen(
        [_script('jotquote'), 'webserver'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert _wait_for_server(url), 'Server did not start within timeout'
        with urllib.request.urlopen(url, timeout=5) as resp:
            cc = resp.headers.get('Cache-Control', '')
        max_age = int(cc.split('=')[1])
        assert max_age <= 60
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_show_author_count(tmp_path):
    """jotquote add prints author count when show_author_count=true."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, show_author_count='true')

    result = subprocess.run(
        [_script('jotquote'), 'add', 'New wisdom - Ben Franklin'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    output = result.stdout.decode('utf-8', errors='replace')
    assert 'quotes by Ben Franklin' in output


def test_default_settings_conf_written(tmp_path):
    """jotquote writes a new settings.conf with all four new properties on first run."""
    # Use a fresh home dir with no .jotquote directory
    env = os.environ.copy()
    env['HOME'] = str(tmp_path)
    env['USERPROFILE'] = str(tmp_path)
    env['PYTHONUNBUFFERED'] = '1'

    subprocess.run(
        [_script('jotquote'), 'info'],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    conf_path = tmp_path / '.jotquote' / 'settings.conf'
    assert conf_path.exists(), 'settings.conf was not created'
    contents = conf_path.read_text(encoding='utf-8')

    assert 'ascii_only' in contents
    assert 'web_cache_minutes' in contents
    assert 'show_author_count' in contents
    assert 'web_page_title' in contents
