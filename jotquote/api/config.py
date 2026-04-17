# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
import shutil
from configparser import ConfigParser

import click

APP_NAME = 'jotquote'
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.jotquote', 'settings.conf')

ALL_CHECKS = frozenset(
    {
        'ascii',  # Flag non-ASCII characters in quote, author, or publication
        'smart-quotes',  # Flag (and fix) typographic/smart quote characters
        'smart-dashes',  # Flag (and fix) unicode dash/hyphen variants
        'double-spaces',  # Flag (and fix) runs of multiple spaces in any field
        'quote-too-long',  # Flag quotes exceeding a configurable max length (max_quote_length)
        'no-tags',  # Flag quotes with no tags
        'no-author',  # Flag quotes with no author
        'author-antipatterns',  # Flag author fields matching known bad patterns (anonymous, all-caps, source-type words)
        'required-tag-group',  # Flag quotes missing a tag from any user-defined required tag group
    }
)

SECTION_GENERAL = 'general'
SECTION_LINT = 'lint'
SECTION_WEB = 'web'
# Retained for backwards compatibility with the old single-section [jotquote] config format
_SECTION_LEGACY = 'jotquote'

_GENERAL_KEYS = frozenset(
    {
        'quote_file',
        'line_separator',
        'show_author_count',
    }
)

_LINT_KEYS = frozenset(
    {
        'lint_on_add',
        'lint_author_antipattern_regex',
    }
)

_WEB_KEYS = frozenset(
    {
        'header_provider_extension',
        'quote_resolver_extension',
        'web_port',
        'web_ip',
        'web_expiration_seconds',
        'web_page_title',
        'web_show_stars',
        'web_light_foreground_color',
        'web_light_background_color',
        'web_dark_foreground_color',
        'web_dark_background_color',
    }
)


def get_config():
    """Load settings.conf and return the parsed config plus a migration flag.

    On first run, the file is created from ``jotquote/resources/settings.conf``
    and the default quote file is copied alongside it.  The config file
    location is taken from the ``JOTQUOTE_CONFIG`` environment variable if
    set, otherwise defaults to ``~/.jotquote/settings.conf``.  Relative paths
    in the config (e.g. ``quote_file = ./quotes.txt``) are resolved to
    absolute paths relative to the directory containing settings.conf.

    Returns:
        tuple[configparser.ConfigParser, bool]: The loaded config and a flag
            that is ``True`` when the legacy ``[jotquote]`` section was
            detected and migrated in-memory to ``[general]``/``[lint]``/``[web]``.
            Callers should surface a deprecation warning to the user in that
            case.

    Raises:
        click.ClickException: If ``quote_file`` is not set in the ``[general]``
            section of the loaded config file.
    """
    config_file = os.environ.get('JOTQUOTE_CONFIG') or CONFIG_FILE
    config_dir = os.path.dirname(os.path.abspath(config_file))

    if not os.path.exists(config_file):
        os.makedirs(config_dir, exist_ok=True)

        # Read template and write to config_file with OS-default line endings
        template_conf = os.path.normpath(os.path.join(__file__, '../../resources/settings.conf'))
        config = ConfigParser()
        config.read(template_conf)
        with open(config_file, 'w') as f:
            config.write(f)

        # If the quote file doesn't exist, copy the template quotes.txt to the configuration directory, usually ~/.jotquote/quotes.txt
        quote_file_raw = config.get(SECTION_GENERAL, 'quote_file')
        if not os.path.isabs(quote_file_raw):
            quote_file = os.path.normpath(os.path.join(config_dir, quote_file_raw))
        else:
            quote_file = quote_file_raw
        if not os.path.exists(quote_file):
            template_quotes = os.path.normpath(os.path.join(__file__, '../../resources/quotes.txt'))
            shutil.copyfile(template_quotes, quote_file)

    config = ConfigParser()
    config.read(config_file)

    # Migrate legacy [jotquote] section to [general]/[lint]/[web]
    migrated = _migrate_legacy_section(config)

    # Ensure optional sections exist
    for section in (SECTION_LINT, SECTION_WEB):
        if not config.has_section(section):
            config.add_section(section)

    _resolve_config_paths(config, config_dir)

    # Validate required property
    if not config.has_option(SECTION_GENERAL, 'quote_file'):
        raise click.ClickException(
            "'quote_file' is not set in [general] section of {}. Please add it to your settings.conf file.".format(
                config_file
            )
        )

    # Add lint defaults in memory if not present
    if not config.has_option(SECTION_LINT, 'enabled_checks'):
        config[SECTION_LINT]['enabled_checks'] = ', '.join(sorted(ALL_CHECKS))

    return config, migrated


def get_filename():
    """Return the resolved quote file path from the loaded config.

    Returns:
        str: Absolute path to the quote file referenced by the
            ``quote_file`` property of the ``[general]`` section.

    Raises:
        click.ClickException: If the resolved quote file does not exist.
    """
    config, _ = get_config()
    filename = config.get(SECTION_GENERAL, 'quote_file')
    if not os.path.exists(filename):
        raise click.ClickException("The quote file specified in settings.conf, '{}', was not found.".format(filename))
    return filename


def _migrate_legacy_section(config):
    """Migrate in-memory config from old [jotquote] section to [general]/[lint]/[web].

    Detects the legacy format (has [jotquote] but no [general]), routes each key
    to the correct new section, strips lint_/web_ prefixes (except lint_on_add which
    retains its prefix), removes [jotquote], and returns True if migration occurred.
    """
    if not config.has_section(_SECTION_LEGACY) or config.has_section(SECTION_GENERAL):
        return False

    for section in (SECTION_GENERAL, SECTION_LINT, SECTION_WEB):
        if not config.has_section(section):
            config.add_section(section)

    for key, value in config.items(_SECTION_LEGACY):
        if key in _LINT_KEYS:
            new_key = key if key == 'lint_on_add' else key[len('lint_') :]
            config[SECTION_LINT][new_key] = value
        elif key.startswith('lint_'):
            config[SECTION_LINT][key[len('lint_') :]] = value
        elif key in _WEB_KEYS:
            new_key = key[len('web_') :] if key.startswith('web_') else key
            config[SECTION_WEB][new_key] = value
        else:
            config[SECTION_GENERAL][key] = value

    config.remove_section(_SECTION_LEGACY)
    return True


def _resolve_config_paths(config, config_dir):
    """Resolve relative path values in config in-place, relative to config_dir."""
    path_lookups = [
        (SECTION_GENERAL, 'quote_file'),
    ]
    for section, key in path_lookups:
        if config.has_option(section, key):
            value = config.get(section, key)
            if value and not os.path.isabs(value):
                config[section][key] = os.path.normpath(os.path.join(config_dir, value))
