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


def _get_hashes(quote_file, env):
    """Use `jotquote list -l` to obtain quote hashes from the given quote file."""
    result = subprocess.run(
        [_script('jotquote'), 'list', '-l'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0
    list_output = result.stdout.decode('utf-8', errors='replace')
    hashes = []
    for line in list_output.splitlines():
        stripped = line.strip()
        if stripped.startswith('hash:'):
            hashes.append(stripped.split(':')[1].strip())
    return hashes


def _rebuild(tmp_path, quote_file, new_quotemap, oldquotemap=None, days=None, env=None):
    """Run `jotquote quotemap rebuild` and return the CompletedProcess."""
    if env is None:
        env = _make_env(tmp_path, quote_file)
    cmd = [_script('jotquote'), 'quotemap', 'rebuild', str(quote_file), str(new_quotemap)]
    if oldquotemap is not None:
        cmd += ['--oldquotemap', str(oldquotemap)]
    if days is not None:
        cmd += ['--days', str(days)]
    return subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _read_data_lines_from_file(path):
    """Return non-blank, non-comment lines from a file."""
    with open(path, encoding='utf-8') as f:
        return [line for line in f.read().splitlines() if line and not line.startswith('#')]


def test_quotemap_rebuild_no_oldquotemap(tmp_path):
    """Rebuild without --oldquotemap generates entries from scratch."""
    quote_file = _copy_quotes(tmp_path)
    new_qm = tmp_path / 'new_quotemap.txt'
    result = _rebuild(tmp_path, quote_file, new_qm, days=10)
    assert result.returncode == 0
    assert new_qm.exists()
    data_lines = _read_data_lines_from_file(new_qm)
    assert len(data_lines) == 11  # today + 10 future days


def test_quotemap_rebuild_with_oldquotemap(tmp_path):
    """Rebuild with --oldquotemap preserves existing entries."""
    import datetime
    quote_file = _copy_quotes(tmp_path)
    quotes = _get_hashes(str(quote_file), _make_env(tmp_path, quote_file))
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')
    old_qm = tmp_path / 'old_quotemap.txt'
    old_qm.write_text('{}: {}  # preserved entry\n'.format(yesterday, quotes[0]), encoding='utf-8')
    new_qm = tmp_path / 'new_quotemap.txt'
    result = _rebuild(tmp_path, quote_file, new_qm, oldquotemap=old_qm, days=5)
    assert result.returncode == 0
    data_lines = _read_data_lines_from_file(new_qm)
    # Yesterday's entry should be preserved verbatim
    assert any(yesterday in line and quotes[0] in line for line in data_lines)


def test_quotemap_rebuild_days_option(tmp_path):
    """--days controls the number of future entries generated."""
    quote_file = _copy_quotes(tmp_path)
    new_qm = tmp_path / 'new_quotemap.txt'
    result = _rebuild(tmp_path, quote_file, new_qm, days=30)
    assert result.returncode == 0
    data_lines = _read_data_lines_from_file(new_qm)
    assert len(data_lines) == 31  # today + 30 future days


def test_quotemap_rebuild_newquotemap_already_exists(tmp_path):
    """NEWQUOTEMAP that already exists produces an error."""
    quote_file = _copy_quotes(tmp_path)
    existing = tmp_path / 'existing.txt'
    existing.write_text('', encoding='utf-8')
    result = _rebuild(tmp_path, quote_file, existing, days=5)
    assert result.returncode != 0
    assert b'already exists' in result.stderr


def test_quotemap_rebuild_oldquotemap_not_found(tmp_path):
    """--oldquotemap pointing to a missing file produces an error."""
    quote_file = _copy_quotes(tmp_path)
    new_qm = tmp_path / 'new_quotemap.txt'
    result = _rebuild(tmp_path, quote_file, new_qm,
                      oldquotemap=tmp_path / 'does_not_exist.txt', days=5)
    assert result.returncode != 0
    assert b'not found' in result.stderr


def test_quotemap_rebuild_newquotemap_required(tmp_path):
    """Omitting NEWQUOTEMAP produces a usage error."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)
    result = subprocess.run(
        [_script('jotquote'), 'quotemap', 'rebuild', str(quote_file)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode != 0


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
