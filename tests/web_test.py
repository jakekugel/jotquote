# -*- coding: utf-8 -*-
# This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import os

from flask import g

import tests.test_util
from jotquote import api, web


def test_charset(flask_client):
    """Both main and unavailable pages declare UTF-8 charset"""
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'<meta charset="UTF-8">' in rv.data
    os.remove(quote_file)
    rv = client.get('/')
    assert b'<meta charset="UTF-8">' in rv.data


def test_page_basics(flask_client, config):
    """A few sanity tests on web page"""
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'<!DOCTYPE html>' in rv.data
    assert b'<title>jotquote</title>' in rv.data
    assert (
        b'<div class="quote">They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.</div>'
        in rv.data
    )
    assert b'<div class="author">Ben Franklin</div>' in rv.data


def test_tags_route_removed(flask_client):
    """/tags route no longer exists and returns 404."""
    client, quote_file = flask_client
    rv = client.get('/tags')
    assert rv.status_code == 404


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
        quote_file = tests.test_util.init_quotefile(quote_dir, 'quotes5.txt')

        rv = client.get('/')
        assert b'The quotes are not yet available; please try again later.' not in rv.data

        cached_time = getattr(g, '_cached_mtime', None)
        quotes = getattr(g, '_quotes', None)
        assert cached_time is not None
        assert quotes is not None


def test_web_cache_minutes(flask_client, config):
    """Cache-Control max-age respects web_cache_minutes config property."""
    config[api.SECTION_WEB]['cache_minutes'] = '1'
    client, quote_file = flask_client
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    max_age = int(cc.split('=')[1])
    assert max_age <= 60


def test_web_cache_minutes_default(flask_client, config):
    """Cache-Control max-age uses 240-minute default when web_cache_minutes is not set."""
    client, quote_file = flask_client
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    max_age = int(cc.split('=')[1])
    assert max_age <= 14400


def test_web_page_title_custom(flask_client, config):
    """Page title reflects web_page_title config property."""
    config[api.SECTION_WEB]['page_title'] = 'My Quotes'
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'<title>My Quotes</title>' in rv.data


def test_web_page_title_custom_unavailable(flask_client, config):
    """Unavailable page title also reflects web_page_title config property."""
    config[api.SECTION_WEB]['page_title'] = 'My Quotes'
    client, quote_file = flask_client
    os.remove(quote_file)
    rv = client.get('/')
    assert b'<title>My Quotes</title>' in rv.data


def test_web_page_title_default(flask_client, config):
    """Page title defaults to 'jotquote' when web_page_title is not set."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'<title>jotquote</title>' in rv.data


def test_stars_displayed(flask_client, config, monkeypatch):
    """Star tag causes the correct number of star characters to appear when web_show_stars is true."""
    config[api.SECTION_WEB]['show_stars'] = 'true'
    client, quote_file = flask_client
    with open(quote_file, 'w', encoding='utf-8') as f:
        f.write('Some quote | Some Author | | 3stars\n')
    monkeypatch.setattr(api, 'get_random_choice', lambda _: 0)
    web.app.config['QUOTE_FILE'] = quote_file
    rv = client.get('/')
    assert '\u2605\u2605\u2605\u2606\u2606'.encode('utf-8') in rv.data  # ★★★☆☆


def test_stars_hidden_when_show_stars_false(flask_client, config, monkeypatch):
    """Stars are not rendered when web_show_stars is false."""
    config[api.SECTION_WEB]['show_stars'] = 'false'
    client, quote_file = flask_client
    with open(quote_file, 'w', encoding='utf-8') as f:
        f.write('Some quote | Some Author | | 3stars\n')
    monkeypatch.setattr(api, 'get_random_choice', lambda _: 0)
    web.app.config['QUOTE_FILE'] = quote_file
    rv = client.get('/')
    assert '\u2605'.encode('utf-8') not in rv.data


def test_static_asset_cache_control(flask_client):
    """Static assets have a long Cache-Control max-age."""
    client, quote_file = flask_client
    rv = client.get('/static/fonts/OpenSans-Regular.ttf')
    cc = rv.headers.get('Cache-Control', '')
    assert 'max-age=86400' in cc


def test_no_stars_when_untagged(flask_client, config):
    """Quotes without a star tag don't render any star characters."""
    config[api.SECTION_WEB]['show_stars'] = 'true'
    client, quote_file = flask_client
    rv = client.get('/')
    assert '\u2605'.encode('utf-8') not in rv.data


def test_date_route_with_quotemap(flask_client, config, tmp_path):
    """/<date> with quotemap entry returns the mapped quote."""
    client, quote_file = flask_client
    quotemap_file = tmp_path / 'quotemap.txt'
    quotemap_file.write_text('20260319: 25382c2519fb23bd\n', encoding='utf-8')
    config[api.SECTION_WEB]['quotemap_file'] = str(quotemap_file)
    rv = client.get('/20260319')
    assert rv.status_code == 200
    assert b'Ben Franklin' in rv.data
    assert b'March 19, 2026' in rv.data


def test_date_route_without_quotemap(flask_client, config):
    """/<date> with no quotemap configured returns 404."""
    client, quote_file = flask_client
    rv = client.get('/20260319')
    assert rv.status_code == 404


def test_date_route_invalid_format(flask_client):
    """Non-8-digit date returns 404."""
    client, quote_file = flask_client
    rv = client.get('/not-a-date')
    assert rv.status_code == 404
    rv = client.get('/1234567')
    assert rv.status_code == 404
    rv = client.get('/123456789')
    assert rv.status_code == 404


def test_date_route_invalid_calendar_date(flask_client):
    """8-digit string that isn't a valid calendar date returns 404, not 500."""
    client, quote_file = flask_client
    rv = client.get('/99991399')  # month 13
    assert rv.status_code == 404
    rv = client.get('/20260230')  # Feb 30
    assert rv.status_code == 404


def test_root_with_quotemap_today(flask_client, config, tmp_path, monkeypatch):
    """/ with today in quotemap returns mapped quote and permalink button."""
    client, quote_file = flask_client
    today = datetime.datetime.now().strftime('%Y%m%d')
    quotemap_file = tmp_path / 'quotemap.txt'
    quotemap_file.write_text(f'{today}: 25382c2519fb23bd\n', encoding='utf-8')
    config[api.SECTION_WEB]['quotemap_file'] = str(quotemap_file)
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Ben Franklin' in rv.data
    assert f"copyPermalink('/{today}')".encode() in rv.data
    assert b'permalink-btn' in rv.data


def test_root_without_quotemap(flask_client, config):
    """/ without quotemap returns RNG quote, no permalink link."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'>permalink</a>' not in rv.data


def test_date_route_no_permalink(flask_client, config, tmp_path):
    """/<date> does not show permalink link (already on permalink)."""
    client, quote_file = flask_client
    quotemap_file = tmp_path / 'quotemap.txt'
    quotemap_file.write_text('20260319: 25382c2519fb23bd\n', encoding='utf-8')
    config[api.SECTION_WEB]['quotemap_file'] = str(quotemap_file)
    rv = client.get('/20260319')
    assert rv.status_code == 200
    assert b'>permalink</a>' not in rv.data


def test_quotemap_hash_not_found_date_route(flask_client, config, tmp_path):
    """Quotemap entry with hash that doesn't match any quote returns 404 on date route."""
    client, quote_file = flask_client
    quotemap_file = tmp_path / 'quotemap.txt'
    quotemap_file.write_text('20260319: aaaaaaaaaaaaaaaa\n', encoding='utf-8')
    config[api.SECTION_WEB]['quotemap_file'] = str(quotemap_file)
    rv = client.get('/20260319')
    assert rv.status_code == 404


def test_quotemap_hash_not_found_root(flask_client, config, tmp_path, monkeypatch):
    """Quotemap entry with hash that doesn't match any quote falls back to RNG on root."""
    client, quote_file = flask_client
    today = datetime.datetime.now().strftime('%Y%m%d')
    quotemap_file = tmp_path / 'quotemap.txt'
    quotemap_file.write_text(f'{today}: aaaaaaaaaaaaaaaa\n', encoding='utf-8')
    config[api.SECTION_WEB]['quotemap_file'] = str(quotemap_file)
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'<!DOCTYPE html>' in rv.data


def test_web_theme_colors_default(flask_client, config):
    """Default dark-mode color values appear in rendered HTML when no color config is set."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'--fg:           #ffffff' in rv.data
    assert b'--bg:           #000000' in rv.data


def test_web_theme_colors_custom(flask_client, config):
    """Custom dark colors from config appear in rendered HTML."""
    config[api.SECTION_WEB]['dark_foreground_color'] = '#cccccc'
    config[api.SECTION_WEB]['dark_background_color'] = '#111111'
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'--fg:           #cccccc' in rv.data
    assert b'--bg:           #111111' in rv.data


def test_theme_toggle_button_present(flask_client):
    """Theme toggle button is rendered in quote.html."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'id="theme-toggle"' in rv.data


def test_permalink_button_present(flask_client, config, tmp_path):
    """Permalink clipboard button appears when quotemap has an entry for today."""
    client, quote_file = flask_client
    today = datetime.datetime.now().strftime('%Y%m%d')
    quotemap_file = tmp_path / 'quotemap.txt'
    quotemap_file.write_text(f'{today}: 25382c2519fb23bd\n', encoding='utf-8')
    config[api.SECTION_WEB]['quotemap_file'] = str(quotemap_file)
    rv = client.get('/')
    assert b'id="permalink-btn"' in rv.data
    assert b'copyPermalink' in rv.data
