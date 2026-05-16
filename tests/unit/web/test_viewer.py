# -*- coding: utf-8 -*-
# This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import os

from flask import g

import tests.test_util
from jotquote import api
from jotquote.web import viewer as web


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


def _cache_control_provider(max_age):
    return {'Cache-Control': f'public, max-age={max_age}'}


def test_cache_control_header(flask_client, monkeypatch):
    """Cache-Control header is set and max-age is within expected bounds."""
    monkeypatch.setattr(web, '_header_fn', _cache_control_provider)
    monkeypatch.setattr(web, '_header_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    assert cc.startswith('public, max-age=')
    max_age = int(cc.split('=')[1])
    assert 0 < max_age <= 14400


def test_cache_control_header_unavailable(flask_client, monkeypatch):
    """Cache-Control header is set even when quote file is unavailable."""
    monkeypatch.setattr(web, '_header_fn', _cache_control_provider)
    monkeypatch.setattr(web, '_header_loaded', True)
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


def test_web_cache_seconds(flask_client, config, monkeypatch):
    """Cache-Control max-age respects expiration_seconds config property."""
    monkeypatch.setattr(web, '_header_fn', _cache_control_provider)
    monkeypatch.setattr(web, '_header_loaded', True)
    config[api.SECTION_WEB]['expiration_seconds'] = '60'
    client, quote_file = flask_client
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    max_age = int(cc.split('=')[1])
    assert max_age <= 60


def test_web_cache_seconds_default(flask_client, config, monkeypatch):
    """Cache-Control max-age uses 14400-second default when web_cache_seconds is not set."""
    monkeypatch.setattr(web, '_header_fn', _cache_control_provider)
    monkeypatch.setattr(web, '_header_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    max_age = int(cc.split('=')[1])
    assert max_age <= 14400


# ---------------------------------------------------------------------------
# Header provider extension point
# ---------------------------------------------------------------------------


def test_no_header_provider_no_cache_control(flask_client, config, monkeypatch):
    """No Cache-Control header when header_provider is not configured."""
    monkeypatch.setattr(web, '_header_fn', None)
    monkeypatch.setattr(web, '_header_loaded', False)
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert 'Cache-Control' not in rv.headers


def test_custom_header_provider(flask_client, config, monkeypatch):
    """Custom header provider headers appear on the response."""
    monkeypatch.setattr(
        web, '_header_fn', lambda max_age: {'X-Custom': 'test', 'Cache-Control': f'public, max-age={max_age}'}
    )
    monkeypatch.setattr(web, '_header_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert rv.headers.get('X-Custom') == 'test'
    assert 'max-age=' in rv.headers.get('Cache-Control', '')


def test_header_provider_error_no_crash(flask_client, config, monkeypatch):
    """Header provider that raises does not crash the server."""

    def _bad_provider(max_age):
        raise RuntimeError('provider error')

    monkeypatch.setattr(web, '_header_fn', _bad_provider)
    monkeypatch.setattr(web, '_header_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert 'X-Custom' not in rv.headers


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


def test_date_route_with_resolver(flask_client, config, monkeypatch):
    """/<date> with resolver returning a hash serves the mapped quote."""
    client, quote_file = flask_client
    monkeypatch.setattr(web, '_resolver_fn', lambda d: 'd4a5c5a909517953' if d == '20260319' else None)
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/20260319')
    assert rv.status_code == 200
    assert b'Ben Franklin' in rv.data
    assert b'March 19, 2026' in rv.data


def test_date_route_without_resolver(flask_client, config):
    """/<date> with no resolver configured returns 404."""
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


def test_root_with_resolver_today(flask_client, config, monkeypatch):
    """/ with resolver returning hash for today shows mapped quote and permalink."""
    client, quote_file = flask_client
    today = datetime.datetime.now().strftime('%Y%m%d')
    monkeypatch.setattr(web, '_resolver_fn', lambda d: 'd4a5c5a909517953')
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Ben Franklin' in rv.data
    assert f"copyPermalink('/{today}')".encode() in rv.data
    assert b'permalink-btn' in rv.data


def test_root_without_resolver(flask_client, config):
    """/ without resolver returns RNG quote, no permalink link."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'>permalink</a>' not in rv.data


def test_date_route_no_permalink(flask_client, config, monkeypatch):
    """/<date> does not show permalink link (already on permalink)."""
    client, quote_file = flask_client
    monkeypatch.setattr(web, '_resolver_fn', lambda d: 'd4a5c5a909517953' if d == '20260319' else None)
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/20260319')
    assert rv.status_code == 200
    assert b'>permalink</a>' not in rv.data


def test_resolver_hash_not_found_date_route(flask_client, config, monkeypatch):
    """Resolver returning a hash that doesn't match any quote returns 404 on date route."""
    client, quote_file = flask_client
    monkeypatch.setattr(web, '_resolver_fn', lambda d: 'aaaaaaaaaaaaaaaa')
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/20260319')
    assert rv.status_code == 404


def test_resolver_hash_not_found_root(flask_client, config, monkeypatch):
    """Resolver returning a hash that doesn't match any quote falls back to RNG on root."""
    client, quote_file = flask_client
    monkeypatch.setattr(web, '_resolver_fn', lambda d: 'aaaaaaaaaaaaaaaa')
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'<!DOCTYPE html>' in rv.data


def test_resolver_returns_none_root(flask_client, config, monkeypatch):
    """Resolver returning None on root falls back to seeded RNG."""
    client, quote_file = flask_client
    monkeypatch.setattr(web, '_resolver_fn', lambda d: None)
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'<!DOCTYPE html>' in rv.data


def test_resolver_returns_none_date_route(flask_client, config, monkeypatch):
    """Resolver returning None on date route returns 404."""
    client, quote_file = flask_client
    monkeypatch.setattr(web, '_resolver_fn', lambda d: None)
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/20260319')
    assert rv.status_code == 404


def test_resolver_exception_root(flask_client, config, monkeypatch):
    """Resolver raising an exception on root falls back to seeded RNG."""
    client, quote_file = flask_client

    def bad_resolver(d):
        raise RuntimeError('boom')

    monkeypatch.setattr(web, '_resolver_fn', bad_resolver)
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'<!DOCTYPE html>' in rv.data


def test_resolver_exception_date_route(flask_client, config, monkeypatch):
    """Resolver raising an exception on date route returns 404."""
    client, quote_file = flask_client

    def bad_resolver(d):
        raise RuntimeError('boom')

    monkeypatch.setattr(web, '_resolver_fn', bad_resolver)
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/20260319')
    assert rv.status_code == 404


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


def test_permalink_button_present(flask_client, config, monkeypatch):
    """Permalink clipboard button appears when resolver returns a hash for today."""
    client, quote_file = flask_client
    monkeypatch.setattr(web, '_resolver_fn', lambda d: 'd4a5c5a909517953')
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/')
    assert b'id="permalink-btn"' in rv.data
    assert b'copyPermalink' in rv.data


# ---------------------------------------------------------------------------
# Auto-refresh and expires_at
# ---------------------------------------------------------------------------


def test_expires_at_present_on_root(flask_client, config):
    """Root page includes expires_at value for auto-refresh scheduling."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'scheduleAutoRefresh' in rv.data
    # expires_at should be a non-null ISO 8601 string in the JS
    assert b'const expiresAt = null' not in rv.data
    assert b'expires_at' not in rv.data or b'T' in rv.data  # contains ISO 8601 timestamp


def test_expires_at_null_on_date_route(flask_client, config, monkeypatch):
    """Date route pages have null expires_at (no auto-refresh)."""
    client, quote_file = flask_client
    monkeypatch.setattr(web, '_resolver_fn', lambda d: 'd4a5c5a909517953' if d == '20260319' else None)
    monkeypatch.setattr(web, '_resolver_loaded', True)
    rv = client.get('/20260319')
    assert rv.status_code == 200
    assert b'const expiresAt = null' in rv.data


def test_view_transition_css(flask_client):
    """View Transitions CSS rule is present in the page."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert b'@view-transition' in rv.data


# ---------------------------------------------------------------------------
# Mode config property
# ---------------------------------------------------------------------------


def test_mode_random_returns_quote(flask_client, config):
    """mode=random on root returns 200 with a quote."""
    config[api.SECTION_WEB]['mode'] = 'random'
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'<!DOCTYPE html>' in rv.data
    assert b'<div class="quote">' in rv.data


def test_mode_random_no_permalink(flask_client, config, monkeypatch):
    """mode=random suppresses permalink even when resolver returns a hash for today."""
    monkeypatch.setattr(web, '_resolver_fn', lambda d: 'd4a5c5a909517953')
    monkeypatch.setattr(web, '_resolver_loaded', True)
    config[api.SECTION_WEB]['mode'] = 'random'
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'id="permalink-btn"' not in rv.data


def test_mode_random_no_midnight_cap(flask_client, config, monkeypatch):
    """mode=random uses expiration_seconds directly without midnight cap."""
    monkeypatch.setattr(web, '_header_fn', _cache_control_provider)
    monkeypatch.setattr(web, '_header_loaded', True)
    config[api.SECTION_WEB]['mode'] = 'random'
    config[api.SECTION_WEB]['expiration_seconds'] = '60'
    client, quote_file = flask_client
    rv = client.get('/')
    cc = rv.headers.get('Cache-Control', '')
    max_age = int(cc.split('=')[1])
    assert max_age == 60


def test_mode_daily_default(flask_client, config):
    """Default mode (daily) returns a quote without permalink (no resolver)."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'id="permalink-btn"' not in rv.data


# ---------------------------------------------------------------------------
# About page
# ---------------------------------------------------------------------------


def test_about_route_returns_about_page(flask_client, config):
    """GET /about with about property set returns 200 and displays the about text."""
    config[api.SECTION_WEB]['about'] = 'Hello world'
    client, quote_file = flask_client
    rv = client.get('/about')
    assert rv.status_code == 200
    assert b'Hello world' in rv.data


def test_about_route_404_when_empty(flask_client, config):
    """GET /about with no about property returns 404."""
    client, quote_file = flask_client
    rv = client.get('/about')
    assert rv.status_code == 404


def test_about_page_has_page_title(flask_client, config):
    """About page uses page_title from config."""
    config[api.SECTION_WEB]['about'] = 'Some about text'
    config[api.SECTION_WEB]['page_title'] = 'My Quotes'
    client, quote_file = flask_client
    rv = client.get('/about')
    assert rv.status_code == 200
    assert b'<title>My Quotes</title>' in rv.data


def test_about_button_present_on_quote_page(flask_client, config):
    """Quote page shows about icon linking to /about when about property is set."""
    config[api.SECTION_WEB]['about'] = 'Some about text'
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'href="/about"' in rv.data
    assert b'about-icon' in rv.data


def test_about_button_absent_when_no_about(flask_client, config):
    """Quote page does not show @ button when about property is not set."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'href="/about"' not in rv.data


# ---------------------------------------------------------------------------
# About page provider extension point
# ---------------------------------------------------------------------------


def test_about_provider_returns_html(flask_client, config, monkeypatch):
    """About content provider fragment is injected into the rendered /about page."""
    monkeypatch.setattr(web, '_about_provider_fn', lambda: '<p>custom about</p>')
    monkeypatch.setattr(web, '_about_provider_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/about')
    assert rv.status_code == 200
    assert b'<p>custom about</p>' in rv.data


def test_about_provider_renders_through_about_template(flask_client, config, monkeypatch):
    """Provider's fragment is wrapped by the built-in about.html chrome (page_title, footer)."""
    config[api.SECTION_WEB]['page_title'] = 'My Test Title'
    monkeypatch.setattr(web, '_about_provider_fn', lambda: '<p>fragment</p>')
    monkeypatch.setattr(web, '_about_provider_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/about')
    assert rv.status_code == 200
    assert b'<title>My Test Title</title>' in rv.data
    assert b'<p>fragment</p>' in rv.data
    assert b'theme-icon' in rv.data


def test_about_provider_takes_priority_over_about_text(flask_client, config, monkeypatch):
    """Extension fragment is rendered when both provider and about text are configured."""
    config[api.SECTION_WEB]['about'] = 'config about text'
    monkeypatch.setattr(web, '_about_provider_fn', lambda: '<p>extension fragment</p>')
    monkeypatch.setattr(web, '_about_provider_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/about')
    assert rv.status_code == 200
    assert b'<p>extension fragment</p>' in rv.data
    assert b'config about text' not in rv.data


def test_about_provider_exception_returns_500(flask_client, config, monkeypatch):
    """About content provider that raises returns 500."""

    def _bad_provider():
        raise RuntimeError('provider error')

    monkeypatch.setattr(web, '_about_provider_fn', _bad_provider)
    monkeypatch.setattr(web, '_about_provider_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/about')
    assert rv.status_code == 500


def test_no_provider_falls_back_to_about_text(flask_client, config, monkeypatch):
    """When no extension is configured, about text config is rendered."""
    monkeypatch.setattr(web, '_about_provider_fn', None)
    monkeypatch.setattr(web, '_about_provider_loaded', True)
    config[api.SECTION_WEB]['about'] = 'Fallback text'
    client, quote_file = flask_client
    rv = client.get('/about')
    assert rv.status_code == 200
    assert b'Fallback text' in rv.data


def test_no_provider_no_about_text_returns_404(flask_client, config, monkeypatch):
    """When neither extension nor about text is configured, /about returns 404."""
    monkeypatch.setattr(web, '_about_provider_fn', None)
    monkeypatch.setattr(web, '_about_provider_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/about')
    assert rv.status_code == 404


def test_about_button_shown_with_provider(flask_client, config, monkeypatch):
    """About button appears on viewer when extension is configured, even without about text."""
    monkeypatch.setattr(web, '_about_provider_fn', lambda: '<p>x</p>')
    monkeypatch.setattr(web, '_about_provider_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'href="/about"' in rv.data
    assert b'about-icon' in rv.data


def test_about_button_shown_with_about_text(flask_client, config, monkeypatch):
    """About button appears on viewer when about text is set (backward-compat regression guard)."""
    monkeypatch.setattr(web, '_about_provider_fn', None)
    monkeypatch.setattr(web, '_about_provider_loaded', True)
    config[api.SECTION_WEB]['about'] = 'Some text'
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'href="/about"' in rv.data


def test_about_button_hidden_with_neither(flask_client, config, monkeypatch):
    """About button is absent when neither extension nor about text is configured."""
    monkeypatch.setattr(web, '_about_provider_fn', None)
    monkeypatch.setattr(web, '_about_provider_loaded', True)
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'href="/about"' not in rv.data


def test_get_about_provider_caches_result(config, monkeypatch):
    """_get_about_provider returns None and sets loaded flag when no extension configured."""
    web._reset_about_provider()
    with web.app.app_context():
        result1 = web._get_about_provider(config)
        assert result1 is None
        assert web._about_provider_loaded is True
        result2 = web._get_about_provider(config)
        assert result2 is None


def test_get_about_provider_import_error(config, monkeypatch):
    """_get_about_provider returns None and logs error when module cannot be imported."""
    web._reset_about_provider()
    config[api.SECTION_WEB]['about_content_provider_extension'] = 'nonexistent.module.path'
    with web.app.app_context():
        result = web._get_about_provider(config)
    assert result is None
    assert web._about_provider_loaded is True


# ---------------------------------------------------------------------------
# Favicon
# ---------------------------------------------------------------------------


def test_favicon_default(flask_client, config):
    """/favicon.ico returns the bundled favicon when favicon_file is unset."""
    client, _ = flask_client
    rv = client.get('/favicon.ico')
    assert rv.status_code == 200
    bundled = os.path.join(os.path.dirname(web.__file__), 'static', 'favicon.ico')
    with open(bundled, 'rb') as f:
        assert rv.data == f.read()


def test_favicon_custom(flask_client, config, tmp_path):
    """/favicon.ico returns the user-configured file when favicon_file is set."""
    custom = tmp_path / 'my-favicon.svg'
    custom.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"/>')
    config[api.SECTION_WEB]['favicon_file'] = str(custom)
    client, _ = flask_client
    rv = client.get('/favicon.ico')
    assert rv.status_code == 200
    assert rv.data == b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    assert 'svg' in rv.headers.get('Content-Type', '')


def test_favicon_missing_falls_back(flask_client, config, tmp_path):
    """Missing favicon_file → bundled default is served (no 500)."""
    config[api.SECTION_WEB]['favicon_file'] = str(tmp_path / 'nope.ico')
    client, _ = flask_client
    rv = client.get('/favicon.ico')
    assert rv.status_code == 200
    bundled = os.path.join(os.path.dirname(web.__file__), 'static', 'favicon.ico')
    with open(bundled, 'rb') as f:
        assert rv.data == f.read()


def test_favicon_link_uses_route(flask_client, config):
    """Templates point <link rel=icon> at the /favicon.ico route, not /static/."""
    client, _ = flask_client
    rv = client.get('/')
    assert b'<link rel="icon" href="/favicon.ico">' in rv.data


# ---------------------------------------------------------------------------
# Fullscreen button
# ---------------------------------------------------------------------------


def test_fullscreen_button_present(flask_client, config):
    """Quote page always shows the fullscreen toggle button."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'id="fullscreen-btn"' in rv.data
    assert b'toggleFullscreen' in rv.data
    assert b'fullscreen-icon' in rv.data


# ---------------------------------------------------------------------------
# Expand/collapse buttons
# ---------------------------------------------------------------------------


def test_toggle_btn_present(flask_client):
    """Quote page renders the toggle button with the right-chevron icon in its initial collapsed state."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'id="toggle-btn"' in rv.data
    assert b'expand-icon' in rv.data
    assert b'collapse-icon' in rv.data


def test_expandable_btns_container_present(flask_client):
    """Quote page renders the expandable buttons container."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'id="expandable-btns"' in rv.data


def test_toggle_buttons_function_present(flask_client):
    """Quote page includes the toggleButtons JavaScript function."""
    client, quote_file = flask_client
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'toggleButtons' in rv.data
