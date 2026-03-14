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
import urllib.error

import pytest


TEST_PORT = 15544
TEST_URL = "http://127.0.0.1:{}/".format(TEST_PORT)

# Derive script paths from the running Python's venv (avoids nested `uv run` buffering).
_SCRIPTS_DIR = os.path.dirname(sys.executable)


def _script(name):
    """Return the absolute path to a script in the current venv's Scripts/bin directory."""
    candidates = [name + ".exe", name] if sys.platform == "win32" else [name]
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
{extra}"""


def _make_env(tmp_path, quote_file, **extra_props):
    """Build a settings.conf in tmp_path and return a subprocess env dict."""
    extra = "\n".join("{} = {}".format(k, v) for k, v in extra_props.items())
    jotquote_dir = tmp_path / ".jotquote"
    jotquote_dir.mkdir()
    conf_path = jotquote_dir / "settings.conf"
    conf_path.write_text(
        SETTINGS_CONF_TEMPLATE.format(quote_file=str(quote_file), port=TEST_PORT, extra=extra),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _copy_quotes(tmp_path):
    """Copy a test quote fixture into tmp_path and return the path."""
    src = os.path.join(os.path.dirname(__file__), "testdata", "quotes1.txt")
    dst = tmp_path / "quotes1.txt"
    shutil.copy(src, dst)
    return dst


def _collect_stderr(proc, lines):
    """Read lines from proc.stderr into lines list (runs in a background thread)."""
    for line in proc.stderr:
        lines.append(line.decode("utf-8", errors="replace").rstrip())


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
        body = resp.read().decode("utf-8")
    assert "<title>jotquote</title>" in body


def _run_server_test(tmp_path, cmd, startup_log):
    """Start a server subprocess, verify it serves and logs correctly, then tear down."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file)

    proc = subprocess.Popen(
        cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), "Server did not start within timeout"
        _assert_response(TEST_URL)
        assert wait_for_log_line(stderr_lines, startup_log), \
            "Expected startup message in stderr; got: {}".format(stderr_lines)
        assert wait_for_log_line(stderr_lines, "GET / 200"), \
            "Expected access log entry in stderr; got: {}".format(stderr_lines)
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_webserver_command(tmp_path):
    """jotquote webserver starts, serves a valid HTML page, and logs to stderr."""
    _run_server_test(
        tmp_path,
        cmd=[_script("jotquote"), "webserver"],
        startup_log="Serving on http://127.0.0.1:{}".format(TEST_PORT),
    )


def test_waitress_serve_command(tmp_path):
    """waitress-serve starts, serves the jotquote WSGI app, and logs to stderr."""
    _run_server_test(
        tmp_path,
        cmd=[
            _script("waitress-serve"),
            "--host", "127.0.0.1",
            "--port", str(TEST_PORT),
            "jotquote.web:app",
        ],
        startup_log="Serving on http://127.0.0.1:{}".format(TEST_PORT),
    )


def test_web_page_title(tmp_path):
    """jotquote webserver uses web_page_title from config as the HTML page title."""
    quote_file = _copy_quotes(tmp_path)
    env = _make_env(tmp_path, quote_file, web_page_title="My Quotes")

    proc = subprocess.Popen(
        [_script("jotquote"), "webserver"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    stderr_lines = []
    reader = threading.Thread(target=_collect_stderr, args=(proc, stderr_lines), daemon=True)
    reader.start()
    try:
        assert wait_for_server(TEST_URL), "Server did not start within timeout"
        with urllib.request.urlopen(TEST_URL, timeout=5) as resp:
            body = resp.read().decode("utf-8")
        assert "<title>My Quotes</title>" in body
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.mark.skipif(sys.platform == "win32", reason="gunicorn not supported on Windows")
def test_gunicorn_launch(tmp_path):
    """gunicorn starts, serves the jotquote WSGI app, and logs to stderr (Linux/Mac only)."""
    _run_server_test(
        tmp_path,
        cmd=[
            _script("gunicorn"),
            "--bind", "127.0.0.1:{}".format(TEST_PORT),
            "jotquote.web:app",
        ],
        startup_log="Listening at: http://127.0.0.1:{}".format(TEST_PORT),
    )
