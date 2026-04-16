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
_WEB_NO_PREFIX = {'header_provider_extension', 'quote_resolver_extension'}


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
            # lint_on_add retains its prefix in [lint]; other lint_ keys have it stripped
            new_key = k if k == 'lint_on_add' else k[5:]
            lint_lines.append('{} = {}'.format(new_key, v))
        elif k.startswith('web_'):
            web_lines.append('{} = {}'.format(k[4:], v))
        else:
            general_lines.append('{} = {}'.format(k, v))
    jotquote_dir = tmp_path / '.jotquote'
    jotquote_dir.mkdir(exist_ok=True)
    conf_path = jotquote_dir / 'settings.conf'
    conf_path.write_text(
        SETTINGS_CONF_TEMPLATE.format(
            quote_file=str(quote_file),
            port=CLI_TEST_PORT,
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
    """Copy quotes1.txt fixture into tmp_path and return the path."""
    src = os.path.join(os.path.dirname(__file__), '..', 'testdata', 'quotes1.txt')
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


def test_web_cache_seconds(tmp_path):
    """jotquote webserver respects web_cache_seconds config: max-age capped at 60 seconds."""
    url = 'http://127.0.0.1:{}/'.format(CLI_TEST_PORT)
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, web_expiration_seconds='60', header_provider_extension='tests.fixtures.test_header_provider')

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
        [_script('jotquote'), 'add', '--no-lint', 'New wisdom - Ben Franklin'],
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


def test_default_settings_conf_written(tmp_path):
    """jotquote writes settings.conf from the template on first run."""
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

    assert 'quote_file' in contents
    assert 'show_author_count' in contents
    assert 'page_title' in contents


def test_add_shows_lint_warnings_integration(tmp_path):
    """jotquote add shows lint warnings for a quote with smart quotes and adds after confirmation."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, lint_on_add='true')

    result = subprocess.run(
        [_script('jotquote'), 'add', '\u201cSmart quote test\u201d - Test Author'],
        env=env,
        input=b'y\n',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    output = result.stdout.decode('utf-8', errors='replace')
    assert result.returncode == 0
    assert 'Warning:' in output
    assert '1 quote added' in output


def test_lint_required_tag_group_integration(tmp_path):
    """jotquote lint flags quotes missing a tag from a configured required-tag-group."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, lint_required_group_stars='1star, 2stars, 3stars, 4stars, 5stars')

    result = subprocess.run(
        [_script('jotquote'), 'lint', '--select', 'required-tag-group'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    output = result.stdout.decode('utf-8', errors='replace')
    assert result.returncode != 0
    assert 'required-tag-group' in output
    assert 'stars' in output


def test_add_stdin_multiple_quotes_with_lint_errors(tmp_path):
    """jotquote add - reads multiple quotes from stdin and shows lint warnings when errors are found."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, lint_on_add='true')

    # Two quotes with double-spaces (lint errors); stdin ends at EOF so the
    # confirmation prompt defaults to 'no', causing a non-zero exit.
    stdin_input = ('First  double  space quote - Author One\nSecond  double  space quote - Author Two\n').encode(
        'utf-8'
    )

    result = subprocess.run(
        [_script('jotquote'), 'add', '-'],
        env=env,
        input=stdin_input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout = result.stdout.decode('utf-8', errors='replace')
    assert result.returncode != 0
    assert 'Warning:' in stdout
    assert 'double-spaces' in stdout
    # Two quotes means at least two warnings (one per quote)
    assert stdout.count('Warning:') >= 2


def test_lint_on_add_false_skips_lint_integration(tmp_path):
    """jotquote add does not run lint when lint_on_add is false."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, lint_on_add='false')

    result = subprocess.run(
        [_script('jotquote'), 'add', '\u201cSmart quote test\u201d - Test Author'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    output = result.stdout.decode('utf-8', errors='replace')
    assert result.returncode == 0
    assert 'Warning:' not in output
    assert '1 quote added' in output


def test_legacy_jotquote_section_still_works(tmp_path):
    """jotquote list works with the legacy [jotquote] section and emits a deprecation warning."""
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

    result = subprocess.run(
        [_script('jotquote'), 'list'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    stderr = result.stderr.decode('utf-8', errors='replace')
    assert 'deprecated' in stderr.lower()
    assert '[jotquote]' in stderr


def test_missing_quote_file_friendly_error(tmp_path):
    """Missing quote_file in settings.conf shows a friendly error, not a stack trace."""
    jotquote_dir = tmp_path / '.jotquote'
    jotquote_dir.mkdir(exist_ok=True)
    conf_path = jotquote_dir / 'settings.conf'
    conf_path.write_text(
        '[general]\nline_separator = platform\n',
        encoding='utf-8',
    )
    env = os.environ.copy()
    env['HOME'] = str(tmp_path)
    env['USERPROFILE'] = str(tmp_path)
    env['JOTQUOTE_CONFIG'] = str(conf_path)
    env['PYTHONUNBUFFERED'] = '1'

    result = subprocess.run(
        [_script('jotquote'), 'list'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode != 0
    stderr = result.stderr.decode('utf-8', errors='replace')
    assert 'quote_file' in stderr
    assert 'NoOptionError' not in stderr
    assert 'Traceback' not in stderr


def _acronym_from_index(i):
    """Return a 5-letter string that uniquely encodes integer i in base-26.

    Maps i=0 -> 'aaaaa', i=1 -> 'aaaab', ..., ensuring each index produces a
    distinct string for i in [0, 26^5).
    """
    letters = []
    for _ in range(5):
        letters.append(chr(ord('a') + i % 26))
        i //= 26
    return ''.join(reversed(letters))


def test_hash_stress(tmp_path):
    """Generate 10,000 quotes with unique acronyms and verify zero hash collisions.

    Each quote's 5 words have first letters that uniquely encode the quote index
    in base-26, guaranteeing distinct acronyms and therefore distinct hashes.
    """
    lines = []
    for i in range(10_000):
        acronym = _acronym_from_index(i)
        # Build 5 words whose first letters spell out the unique acronym
        words = [letter + 'xample' for letter in acronym]
        quote_text = ' '.join(words)
        lines.append('{} | Author {} | | stress'.format(quote_text, i))

    quote_file = tmp_path / 'stress.txt'
    quote_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    env = _make_env(tmp_path, quote_file)

    # Collect all hashes via the CLI
    hashes = _get_hashes(quote_file, env)

    assert len(hashes) == 10_000, 'Expected 10,000 hashes, got {}'.format(len(hashes))
    assert len(set(hashes)) == 10_000, 'Hash collisions detected: {} unique out of 10,000'.format(len(set(hashes)))
