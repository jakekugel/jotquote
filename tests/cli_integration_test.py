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


def test_quotemap_rebuild(tmp_path):
    """jotquote quotemap rebuild produces quotemap output on stdout."""
    quote_file = _copy_quotes(tmp_path)
    qm = tmp_path / 'quotemap.txt'
    qm.write_text('', encoding='utf-8')
    quotemap_file = str(qm)
    env = _make_env(tmp_path, quote_file)

    result = subprocess.run(
        [_script('jotquote'), 'quotemap', 'rebuild', str(quote_file), quotemap_file],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    output = result.stdout.decode('utf-8', errors='replace')
    # Should contain quotemap data lines
    assert '# Quotes for ' in output
    lines = [l for l in output.splitlines() if l and not l.startswith('#')]
    assert len(lines) == 3652


def test_quotemap_rebuild_new_quote_sticky(tmp_path):
    """Rebuild marks the first use of a never-before-seen quote as Sticky."""
    import datetime

    # Copy quotes9.txt (8 quotes) to tmp_path
    quote_file = str(shutil.copy(
        os.path.join(os.path.dirname(__file__), 'testdata', 'quotes9.txt'),
        tmp_path / 'quotes9.txt',
    ))
    env = _make_env(tmp_path, quote_file)

    hashes = _get_hashes(quote_file, env)
    assert len(hashes) == 8

    # Build old quotemap with 5 entries using hashes[0..4]:
    #   2 days ago  -> hashes[0]  (past, not sticky — preserved)
    #   yesterday   -> hashes[1]  (past, sticky — preserved)
    #   today       -> hashes[2]  (today, not sticky — preserved)
    #   tomorrow    -> hashes[3]  (future, sticky — preserved)
    #   day after   -> hashes[4]  (future, not sticky — DISCARDED/reassigned)
    now = datetime.datetime.now()
    dates = [(now + datetime.timedelta(days=d)).strftime('%Y%m%d') for d in [-2, -1, 0, 1, 2]]

    old_qm = tmp_path / 'old_quotemap.txt'
    old_qm.write_text(
        '{d[0]}: {h[0]}\n'
        '{d[1]}: {h[1]}  # Sticky: keep this\n'
        '{d[2]}: {h[2]}\n'
        '{d[3]}: {h[3]}  # Sticky: keep this too\n'
        '{d[4]}: {h[4]}\n'.format(d=dates, h=hashes),
        encoding='utf-8',
    )

    # Run rebuild
    result = subprocess.run(
        [_script('jotquote'), 'quotemap', 'rebuild', str(quote_file), str(old_qm)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0
    output = result.stdout.decode('utf-8', errors='replace')
    data_lines = [l for l in output.splitlines() if l and not l.startswith('#')]

    # hashes[0..3] are preserved (past/today/future-sticky); hashes[4] was
    # non-sticky future so it gets discarded by include_future=False and is
    # treated as a new hash alongside hashes[5..7].
    old_hashes = set(hashes[0:4])
    new_hashes = set(hashes[4:8])

    # (1) The 3 past/today entries are preserved with correct hashes
    past_today_lines = {l.split(':')[0]: l for l in data_lines if l.split(':')[0] in dates[:3]}
    assert hashes[0] in past_today_lines[dates[0]]
    assert hashes[1] in past_today_lines[dates[1]]
    assert hashes[2] in past_today_lines[dates[2]]

    # (2) The future sticky entry (tomorrow) is preserved with correct hash
    tomorrow_lines = [l for l in data_lines if l.startswith(dates[3])]
    assert len(tomorrow_lines) == 1
    assert hashes[3] in tomorrow_lines[0]
    assert '# Sticky:' in tomorrow_lines[0]

    # (3) The day-after-tomorrow entry was reassigned (not necessarily hashes[4])
    day_after_lines = [l for l in data_lines if l.startswith(dates[4])]
    assert len(day_after_lines) == 1
    # It could be any hash — just verify the line exists

    # (4) Each of the 3 never-before-used hashes has exactly 1 Sticky line
    for h in new_hashes:
        sticky_lines = [l for l in data_lines if h in l and '# Sticky:' in l]
        assert len(sticky_lines) == 1, \
            'Expected exactly 1 Sticky line for new hash {}, got {}'.format(h, len(sticky_lines))

    # (5) The 5 old-quotemap hashes have zero auto-Sticky in NEW future assignments
    #     (past preserved lines may contain "# Sticky:" from the old quotemap — exclude those)
    past_today_set = set(dates[:3])
    for h in old_hashes:
        future_sticky = [l for l in data_lines
                         if h in l and '# Sticky:' in l
                         and l.split(':')[0] not in past_today_set
                         and l.split(':')[0] != dates[3]]  # exclude the original sticky entry
        assert len(future_sticky) == 0, \
            'Old hash {} should not be auto-Sticky, got {}'.format(h, len(future_sticky))


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
