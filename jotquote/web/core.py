# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from jotquote import api

LOG_FORMAT = '%(levelname)s %(name)s:%(message)s'


def sanitize_for_log(value):
    """Remove newline and carriage return characters to prevent log injection."""
    return value.replace('\r', '').replace('\n', '')


def get_enabled_checks(config):
    """Return the set of lint checks to run, from config or all checks if unset."""
    raw = config.get(api.SECTION_LINT, 'enabled_checks', fallback='')
    return {c.strip() for c in raw.split(',') if c.strip()} if raw.strip() else api.ALL_CHECKS


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
