# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import logging
import re
from configparser import ConfigParser

import pytest

from jotquote import api
from jotquote.web.helpers import LOG_FORMAT, TimestampFormatter, get_color_config, sanitize_for_log

# ---------------------------------------------------------------------------
# TimestampFormatter
# ---------------------------------------------------------------------------


def test_timestamp_formatter_format():
    """TimestampFormatter produces YYYY/MM/DD HH:MM:SS.mmm AM/PM TZ prefix."""
    formatter = TimestampFormatter(LOG_FORMAT)
    record = logging.LogRecord('test.logger', logging.INFO, '', 0, 'hello', [], None)
    record.msecs = 42.0
    formatted = formatter.format(record)
    # e.g. "2026/04/07 06:21:42.042 AM CDT INFO test.logger:hello"
    assert re.match(r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3} [AP]M \S+ ', formatted)


# ---------------------------------------------------------------------------
# sanitize_for_log
# ---------------------------------------------------------------------------


def test_sanitize_for_log_no_change():
    """Plain strings pass through unchanged."""
    assert sanitize_for_log('GET /foo 200') == 'GET /foo 200'


def test_sanitize_for_log_strips_newline():
    """Newline characters are removed."""
    assert sanitize_for_log('line1\nline2') == 'line1line2'


def test_sanitize_for_log_strips_carriage_return():
    """Carriage return characters are removed."""
    assert sanitize_for_log('line1\rline2') == 'line1line2'


def test_sanitize_for_log_strips_crlf():
    """CRLF sequences are both removed."""
    assert sanitize_for_log('line1\r\nline2') == 'line1line2'


def test_sanitize_for_log_empty_string():
    """Empty string returns empty string."""
    assert sanitize_for_log('') == ''


def test_sanitize_for_log_only_control_chars():
    """String of only control characters becomes empty."""
    assert sanitize_for_log('\r\n\r\n') == ''


# ---------------------------------------------------------------------------
# get_color_config
# ---------------------------------------------------------------------------


@pytest.fixture
def web_config():
    """Minimal ConfigParser with a [web] section and no color overrides."""
    cfg = ConfigParser()
    cfg.add_section(api.SECTION_WEB)
    return cfg


def test_get_color_config_defaults(web_config):
    """Returns hard-coded defaults when no color keys are present in config."""
    colors = get_color_config(web_config)
    assert colors['light_fg'] == '#000000'
    assert colors['light_bg'] == '#ffffff'
    assert colors['dark_fg'] == '#ffffff'
    assert colors['dark_bg'] == '#000000'


def test_get_color_config_returns_all_four_keys(web_config):
    """Return value always contains exactly the four expected keys."""
    colors = get_color_config(web_config)
    assert set(colors.keys()) == {'light_fg', 'light_bg', 'dark_fg', 'dark_bg'}


def test_get_color_config_custom_light_fg(web_config):
    """light_foreground_color config value overrides the default."""
    web_config[api.SECTION_WEB]['light_foreground_color'] = '#112233'
    colors = get_color_config(web_config)
    assert colors['light_fg'] == '#112233'


def test_get_color_config_custom_light_bg(web_config):
    """light_background_color config value overrides the default."""
    web_config[api.SECTION_WEB]['light_background_color'] = '#aabbcc'
    colors = get_color_config(web_config)
    assert colors['light_bg'] == '#aabbcc'


def test_get_color_config_custom_dark_fg(web_config):
    """dark_foreground_color config value overrides the default."""
    web_config[api.SECTION_WEB]['dark_foreground_color'] = '#ddeeff'
    colors = get_color_config(web_config)
    assert colors['dark_fg'] == '#ddeeff'


def test_get_color_config_custom_dark_bg(web_config):
    """dark_background_color config value overrides the default."""
    web_config[api.SECTION_WEB]['dark_background_color'] = '#010101'
    colors = get_color_config(web_config)
    assert colors['dark_bg'] == '#010101'


def test_get_color_config_all_custom(web_config):
    """All four colors can be overridden simultaneously."""
    web_config[api.SECTION_WEB]['light_foreground_color'] = '#111111'
    web_config[api.SECTION_WEB]['light_background_color'] = '#222222'
    web_config[api.SECTION_WEB]['dark_foreground_color'] = '#333333'
    web_config[api.SECTION_WEB]['dark_background_color'] = '#444444'
    colors = get_color_config(web_config)
    assert colors == {
        'light_fg': '#111111',
        'light_bg': '#222222',
        'dark_fg': '#333333',
        'dark_bg': '#444444',
    }
