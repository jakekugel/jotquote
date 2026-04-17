# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
from configparser import ConfigParser

import click
import pytest

from jotquote import api
from jotquote.api import config as config_mod


def test_get_config_creates_from_template(tmp_path, monkeypatch):
    """First run creates settings.conf from the template and copies quotes.txt."""
    config_file = tmp_path / 'settings.conf'
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    config, _ = api.get_config()

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

    config, _ = api.get_config()

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

    config, _ = api.get_config()

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

    config, _ = api.get_config()

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

    config, migrated = api.get_config()

    assert migrated is True
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
    """get_config() returns migrated=True for legacy [jotquote] format."""
    config_file = tmp_path / 'settings.conf'
    config_file.write_text(
        '[jotquote]\nquote_file = /some/path/quotes.txt\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    _, migrated = api.get_config()

    assert migrated is True


def test_get_config_missing_quote_file_raises_click_exception(tmp_path, monkeypatch):
    """get_config() raises ClickException with friendly message when quote_file is missing."""
    config_file = tmp_path / 'settings.conf'
    config_file.write_text(
        '[general]\nline_separator = platform\n',
        encoding='utf-8',
    )
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    with pytest.raises(click.ClickException, match='quote_file'):
        api.get_config()


def test_migrate_legacy_section_prefix_stripping():
    """_migrate_legacy_section() strips lint_ and web_ prefixes correctly."""
    config = ConfigParser()
    config.add_section('jotquote')
    config['jotquote']['quote_file'] = '/path/quotes.txt'
    config['jotquote']['line_separator'] = 'unix'
    config['jotquote']['lint_max_quote_length'] = '100'
    config['jotquote']['lint_author_antipattern_regex'] = r'^\d'
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
    assert config.get(api.SECTION_LINT, 'author_antipattern_regex') == r'^\d'
    assert config.get(api.SECTION_LINT, 'required_group_stars') == '1star, 2stars'
    # Web section (prefix stripped)
    assert config.get(api.SECTION_WEB, 'port') == '8080'
    assert config.get(api.SECTION_WEB, 'ip') == '0.0.0.0'
    assert config.get(api.SECTION_WEB, 'expiration_seconds') == '3600'
    assert config.get(api.SECTION_WEB, 'quote_resolver_extension') == 'mypackage.resolver'
    # Old section removed
    assert not config.has_section('jotquote')
