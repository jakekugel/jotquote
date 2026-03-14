# -*- coding: utf-8 -*-
# This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os

from flask import g

import tests.test_util
from jotquote import web


def test_charset(flask_client):
    """Both main and unavailable pages declare UTF-8 charset"""
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'<meta charset="UTF-8">' in rv.data
    os.remove(quote_file)
    rv = client.get('/')
    assert b'<meta charset="UTF-8">' in rv.data


def test_page_basics(flask_client):
    """A few sanity tests on web page"""
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'<!DOCTYPE html>' in rv.data
    assert b'<title>jotquote</title>' in rv.data
    assert b'<div class="quote">They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.</div>' in rv.data
    assert b'<div class="author">Ben Franklin</div>' in rv.data


def test_page_tags(flask_client):
    """A few sanity tests on web page"""
    client, quote_file = flask_client
    rv = client.get('/tags')
    assert b'<!DOCTYPE html>' in rv.data
    assert b'<title>jotquote</title>' in rv.data
    assert b'<div class="quote">They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.</div>' in rv.data
    assert b'<div class="author">Ben Franklin</div>' in rv.data
    assert b'<div id=\'settag\' class="command" style="display:none;">$ jotquote settags -s 25382c2519fb23bd U</div>' in rv.data


def test_quote_caching(flask_client):
    """Test that quotes cached but reloaded if quote file changes"""
    client, quote_file = flask_client
    with web.app.app_context():
        client.get('/')
        cached_time_1 = getattr(g, '_cached_mtime', None)
        client.get('/')
        cached_time_2 = getattr(g, '_cached_mtime', None)
        assert cached_time_1 == cached_time_2
        os.utime(quote_file, (cached_time_2 + 1.0, cached_time_2 + 1.0))
        client.get('/')
        cached_time_3 = getattr(g, '_cache_mtime', None)
        assert cached_time_3 != cached_time_1


def test_cache_control_header(flask_client):
    """Cache-Control header is set and max-age is within expected bounds."""
    client, quote_file = flask_client
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    assert cc.startswith('public, max-age=')
    max_age = int(cc.split('=')[1])
    assert 0 < max_age <= 14400


def test_cache_control_header_unavailable(flask_client):
    """Cache-Control header is set even when quote file is unavailable."""
    client, quote_file = flask_client
    os.remove(quote_file)
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    assert cc.startswith('public, max-age=')
    max_age = int(cc.split('=')[1])
    assert 0 < max_age <= 14400


def test_io_errors(flask_client):
    """Test that app responds gracefully to IO errors"""
    client, quote_file = flask_client
    with web.app.app_context():
        client.get('/')
        cached_time = getattr(g, '_cached_mtime', None)
        quotes = getattr(g, '_quotes', None)
        assert cached_time is not None
        assert quotes is not None

        # Delete the test file
        os.remove(quote_file)

        rv = client.get('/')
        assert b'The quotes are not yet available; please try again later.' in rv.data

        cached_time = getattr(g, '_cached_mtime', None)
        quotes = getattr(g, '_quotes', None)
        assert cached_time is None
        assert quotes is None

        # Restore the test file (use the same directory as the original quote_file)
        quote_dir = os.path.dirname(quote_file)
        quote_file = tests.test_util.init_quotefile(quote_dir, "quotes5.txt")

        rv = client.get('/')
        assert b'The quotes are not yet available; please try again later.' not in rv.data

        cached_time = getattr(g, '_cached_mtime', None)
        quotes = getattr(g, '_quotes', None)
        assert cached_time is not None
        assert quotes is not None
