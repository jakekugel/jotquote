# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
from configparser import ConfigParser

import pytest

from jotquote import api
from jotquote.api import config as config_mod


def test_get_config_creates_from_template(tmp_path, monkeypatch):
    """First run creates settings.conf from the template and copies quotes.txt."""
    config_file = tmp_path / 'settings.conf'
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    config = api.get_config()

    assert config_file.exists()
    contents = config_file.read_text(encoding='utf-8')
    assert 'quote_file' in contents
    assert 'line_separator' in contents
    assert 'show_author_count' in contents
    assert 'page_title' in contents
    # quotes.txt should have been copied alongside settings.conf
    assert (tmp_path / 'quotes.txt').exists()
    # quote_file should be resolved to an absolute path in the returned config
    quote_file = config.get(api.SECTION_GENERAL, 'quote_file')
    assert os.path.isabs(quote_file)


def test_get_config_env_var_overrides_default(tmp_path, monkeypatch):
    """JOTQUOTE_CONFIG env var is used in preference to the default config location."""
    config_file = tmp_path / 'custom.conf'
    config_file.write_text(
        '[general]\nquote_file = /some/path/quotes.txt\n\n[web]\npage_title = Custom Title\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    config = api.get_config()

    assert config.get(api.SECTION_WEB, 'page_title') == 'Custom Title'


def test_get_config_resolves_relative_quote_file(tmp_path, monkeypatch):
    """A relative quote_file path is resolved to an absolute path."""
    quotes_file = tmp_path / 'myquotes.txt'
    quotes_file.write_text('', encoding='utf-8')
    config_file = tmp_path / 'settings.conf'
    config_file.write_text(
        '[general]\nquote_file = ./myquotes.txt\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    config = api.get_config()

    resolved = config.get(api.SECTION_GENERAL, 'quote_file')
    assert os.path.isabs(resolved)
    assert resolved == str(quotes_file)


def test_get_config_new_format(tmp_path, monkeypatch):
    """get_config() reads the new three-section format correctly."""
    config_file = tmp_path / 'settings.conf'
    config_file.write_text(
        '[general]\n'
        'quote_file = /some/path/quotes.txt\n'
        'line_separator = unix\n'
        '\n'
        '[lint]\n'
        'lint_on_add = true\n'
        'max_quote_length = 200\n'
        '\n'
        '[web]\n'
        'port = 8080\n'
        'page_title = Test Quotes\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    config = api.get_config()

    assert os.path.isabs(config.get(api.SECTION_GENERAL, 'quote_file'))
    assert config.get(api.SECTION_GENERAL, 'line_separator') == 'unix'
    assert config.get(api.SECTION_LINT, 'lint_on_add') == 'true'
    assert config.get(api.SECTION_LINT, 'max_quote_length') == '200'
    assert config.get(api.SECTION_WEB, 'port') == '8080'
    assert config.get(api.SECTION_WEB, 'page_title') == 'Test Quotes'


def test_get_config_legacy_format_migrates(tmp_path, monkeypatch):
    """get_config() migrates old [jotquote] section to new sections."""
    config_file = tmp_path / 'settings.conf'
    config_file.write_text(
        '[jotquote]\n'
        'quote_file = /some/path/quotes.txt\n'
        'lint_on_add = true\n'
        'lint_max_quote_length = 150\n'
        'web_port = 9090\n'
        'web_page_title = Legacy Title\n'
        'quote_resolver_extension = mypackage.resolver\n'
        'show_author_count = true\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    with pytest.warns(UserWarning, match=r'\[jotquote\]'):
        config = api.get_config()

    # General properties
    assert os.path.isabs(config.get(api.SECTION_GENERAL, 'quote_file'))
    assert config.get(api.SECTION_GENERAL, 'show_author_count') == 'true'
    # Lint properties (lint_on_add retains prefix; others have prefix stripped)
    assert config.get(api.SECTION_LINT, 'lint_on_add') == 'true'
    assert config.get(api.SECTION_LINT, 'max_quote_length') == '150'
    # Web properties (prefix stripped)
    assert config.get(api.SECTION_WEB, 'port') == '9090'
    assert config.get(api.SECTION_WEB, 'page_title') == 'Legacy Title'
    # quote_resolver_extension has no web_ prefix but goes to [web]
    assert config.get(api.SECTION_WEB, 'quote_resolver_extension') == 'mypackage.resolver'
    # Old section should be removed
    assert not config.has_section('jotquote')


def test_get_config_legacy_format_warns(tmp_path, monkeypatch):
    """get_config() emits a DeprecationWarning for legacy [jotquote] format."""
    config_file = tmp_path / 'settings.conf'
    config_file.write_text(
        '[jotquote]\nquote_file = /some/path/quotes.txt\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    with pytest.warns(UserWarning, match=r'\[jotquote\]'):
        api.get_config()


def test_get_config_missing_quote_file_raises_config_error(tmp_path, monkeypatch):
    """get_config() raises ConfigError with friendly message when quote_file is missing."""
    config_file = tmp_path / 'settings.conf'
    config_file.write_text(
        '[general]\nline_separator = platform\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    with pytest.raises(api.ConfigError, match='quote_file'):
        api.get_config()


def test_get_config_reads_timezone_from_general(tmp_path, monkeypatch):
    """A timezone property in [general] is exposed via the loaded config."""
    quotes_file = tmp_path / 'quotes.txt'
    quotes_file.write_text('', encoding='utf-8')
    config_file = tmp_path / 'settings.conf'
    config_file.write_text(
        '[general]\nquote_file = ./quotes.txt\ntimezone = America/Chicago\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    config = api.get_config()

    assert config.get(api.SECTION_GENERAL, 'timezone') == 'America/Chicago'


def test_get_config_timezone_absent_by_default(tmp_path, monkeypatch):
    """A fresh default config has no timezone option (opt-in)."""
    config_file = tmp_path / 'settings.conf'
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    config = api.get_config()

    assert not config.has_option(api.SECTION_GENERAL, 'timezone')


def test_get_config_legacy_jotquote_timezone_migrates(tmp_path, monkeypatch):
    """Legacy [jotquote] timezone property migrates into [general]."""
    config_file = tmp_path / 'settings.conf'
    config_file.write_text(
        '[jotquote]\nquote_file = /some/path/quotes.txt\ntimezone = America/Chicago\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    with pytest.warns(UserWarning, match=r'\[jotquote\]'):
        config = api.get_config()

    assert config.get(api.SECTION_GENERAL, 'timezone') == 'America/Chicago'


def test_migrate_legacy_section_prefix_stripping():
    """_migrate_legacy_section() strips lint_ and web_ prefixes correctly."""
    config = ConfigParser()
    config.add_section('jotquote')
    config['jotquote']['quote_file'] = '/path/quotes.txt'
    config['jotquote']['line_separator'] = 'unix'
    config['jotquote']['lint_max_quote_length'] = '100'
    config['jotquote']['lint_required_group_stars'] = '1star, 2stars'
    config['jotquote']['web_port'] = '8080'
    config['jotquote']['web_ip'] = '0.0.0.0'
    config['jotquote']['web_expiration_seconds'] = '3600'
    config['jotquote']['quote_resolver_extension'] = 'mypackage.resolver'
    config['jotquote']['show_author_count'] = 'true'

    config_mod._migrate_legacy_section(config)

    # General section
    assert config.get(api.SECTION_GENERAL, 'quote_file') == '/path/quotes.txt'
    assert config.get(api.SECTION_GENERAL, 'line_separator') == 'unix'
    assert config.get(api.SECTION_GENERAL, 'show_author_count') == 'true'
    # Lint section (prefix stripped)
    assert config.get(api.SECTION_LINT, 'max_quote_length') == '100'
    assert config.get(api.SECTION_LINT, 'required_group_stars') == '1star, 2stars'
    # Web section (prefix stripped)
    assert config.get(api.SECTION_WEB, 'port') == '8080'
    assert config.get(api.SECTION_WEB, 'ip') == '0.0.0.0'
    assert config.get(api.SECTION_WEB, 'expiration_seconds') == '3600'
    assert config.get(api.SECTION_WEB, 'quote_resolver_extension') == 'mypackage.resolver'
    # Old section removed
    assert not config.has_section('jotquote')


def _write_conf(tmp_path, monkeypatch, body):
    """Write a settings.conf for the test and point JOTQUOTE_CONFIG at it."""
    conf = tmp_path / 'settings.conf'
    conf.write_text(body, encoding='utf-8')
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(conf))
    return conf


def test_unknown_key_in_web_section_warns(tmp_path, monkeypatch):
    """A typo'd property in [web] (e.g. cache_seconds) raises a UserWarning."""
    _write_conf(
        tmp_path,
        monkeypatch,
        '[general]\nquote_file = /q.txt\n\n[web]\ncache_seconds = 10\n',
    )
    with pytest.warns(UserWarning, match=r"unrecognized key 'cache_seconds' in \[web\]"):
        api.get_config()


def test_unknown_key_in_general_section_warns(tmp_path, monkeypatch):
    """A typo'd property in [general] raises a UserWarning."""
    _write_conf(
        tmp_path,
        monkeypatch,
        '[general]\nquote_file = /q.txt\ntimezon = America/Chicago\n',
    )
    with pytest.warns(UserWarning, match=r"unrecognized key 'timezon' in \[general\]"):
        api.get_config()


def test_unknown_key_in_lint_section_warns(tmp_path, monkeypatch):
    """A typo'd property in [lint] raises a UserWarning."""
    _write_conf(
        tmp_path,
        monkeypatch,
        '[general]\nquote_file = /q.txt\n\n[lint]\nmax_qoute_length = 100\n',
    )
    with pytest.warns(UserWarning, match=r"unrecognized key 'max_qoute_length' in \[lint\]"):
        api.get_config()


def test_required_group_keys_not_warned(tmp_path, monkeypatch, recwarn):
    """required_group_<name> keys in [lint] are accepted (dynamic naming)."""
    _write_conf(
        tmp_path,
        monkeypatch,
        '[general]\nquote_file = /q.txt\n\n[lint]\nrequired_group_stars = 1star, 2stars\n',
    )
    api.get_config()
    assert not any('required_group_stars' in str(w.message) for w in recwarn.list)


def test_all_known_keys_no_warning(tmp_path, monkeypatch, recwarn):
    """A config containing only documented keys raises no unrecognized-key warning."""
    body = (
        '[general]\n'
        'quote_file = /q.txt\n'
        'line_separator = platform\n'
        'show_author_count = false\n'
        'timezone = America/Chicago\n'
        '\n'
        '[lint]\n'
        'enabled_checks = smart-quotes\n'
        'lint_on_add = false\n'
        'max_quote_length = 0\n'
        '\n'
        '[web]\n'
        'mode = daily\n'
        'port = 5544\n'
        'ip = 127.0.0.1\n'
        'editor_port = 5545\n'
        'editor_ip = 127.0.0.1\n'
        'expiration_seconds = 14400\n'
        'page_title = jotquote\n'
        'about = Some text\n'
        'about_content_provider_extension =\n'
        'header_provider_extension =\n'
        'quote_resolver_extension =\n'
        'favicon_file =\n'
        'show_stars = false\n'
        'light_foreground_color = #000000\n'
        'light_background_color = #ffffff\n'
        'dark_foreground_color = #ffffff\n'
        'dark_background_color = #000000\n'
    )
    _write_conf(tmp_path, monkeypatch, body)
    api.get_config()
    assert not any('unrecognized key' in str(w.message) for w in recwarn.list)
