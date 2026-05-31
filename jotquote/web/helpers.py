# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import logging
import os
import time

from jotquote import api

LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'

_logger = logging.getLogger(__name__)

_BUNDLED_FAVICON = os.path.join(os.path.dirname(__file__), 'static', 'favicon.ico')


def abbreviate_timezone(name):
    """Return an abbreviation for a timezone name by taking the first letter of each word.

    If the name is already short (e.g. 'CDT', 'EST'), it is returned unchanged.
    Multi-word names like 'Central Daylight Time' become 'CDT'.

    :param name: str timezone name
    :return: str abbreviated timezone name
    """
    if not name:
        return name
    words = name.split()
    if len(words) <= 1:
        return name
    return ''.join(w[0] for w in words)


class TimestampFormatter(logging.Formatter):
    """Formatter that produces timestamps like '2026/04/07 06:21:42.023 AM CDT'."""

    def formatTime(self, record, datefmt=None):  # noqa: N802
        """Return a formatted timestamp string with milliseconds, AM/PM, and timezone."""
        ct = self.converter(record.created)
        t = time.strftime('%Y/%m/%d %I:%M:%S', ct)
        tz = abbreviate_timezone(time.strftime('%Z', ct))
        return '{}.{:03d} {} {}'.format(t, int(record.msecs), time.strftime('%p', ct), tz)


def configure_logging():
    """Set up the root logger with TimestampFormatter if not already configured."""
    if not logging.root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(TimestampFormatter(LOG_FORMAT))
        logging.root.setLevel(logging.INFO)
        logging.root.addHandler(handler)


def log_paths_and_version(logger):
    """Log settings.conf path, quote file path, and jotquote package version.

    Shared by the viewer and editor startup paths so both surface the same
    diagnostic information when launched.  The settings file path is read from
    the ``JOTQUOTE_CONFIG`` environment variable when set, otherwise from
    ``api.CONFIG_FILE``.  The quote file path is read from the resolved config.

    logger (logging.Logger) -- the logger to emit the INFO messages on.
    """
    import jotquote

    config_file = os.environ.get('JOTQUOTE_CONFIG') or api.CONFIG_FILE
    config = api.get_config()
    quote_file = config.get(api.SECTION_GENERAL, 'quote_file')
    logger.info('path to settings.conf file: %s', config_file)
    logger.info('path to the quote file: %s', quote_file)
    logger.info('jotquote package version: %s', jotquote.__version__)


def sanitize_for_log(value):
    """Remove newline and carriage return characters to prevent log injection."""
    return value.replace('\r', '').replace('\n', '')


def get_enabled_checks(config):
    """Return the set of lint checks to run, from config or all checks if unset."""
    raw = config.get(api.SECTION_LINT, 'enabled_checks', fallback='')
    return {c.strip() for c in raw.split(',') if c.strip()} if raw.strip() else api.ALL_CHECKS


def resolve_favicon_path(config):
    """Return the absolute path of the favicon to serve.

    Reads the ``favicon_file`` property from the ``[web]`` section.  When the
    property is empty or absent, returns the path to the bundled default
    favicon.  When it is set but points to a non-existent file, logs an error
    and returns the bundled default so the page still loads.

    config (ConfigParser) -- the application configuration object.
    Returns str (absolute path to a favicon file).
    """
    configured = config[api.SECTION_WEB].get('favicon_file', '').strip()
    if not configured:
        return _BUNDLED_FAVICON
    if not os.path.isfile(configured):
        _logger.error('favicon_file %r does not exist; serving bundled favicon', configured)
        return _BUNDLED_FAVICON
    return configured


def get_color_config(config):
    """Return a dict of light/dark theme color values from the [web] config section.

    Keys: light_fg, light_bg, dark_fg, dark_bg.
    """
    section = config[api.SECTION_WEB]
    return {
        'light_fg': section.get('light_foreground_color', '#000000'),
        'light_bg': section.get('light_background_color', '#ffffff'),
        'dark_fg': section.get('dark_foreground_color', '#ffffff'),
        'dark_bg': section.get('dark_background_color', '#000000'),
    }
