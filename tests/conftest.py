# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import tempfile
from configparser import ConfigParser
from unittest.mock import Mock

import pytest

import tests.test_util
from jotquote import api


@pytest.fixture
def config(monkeypatch):
    """Provide a test Config object and patch api.get_config to return it."""
    cfg = ConfigParser()
    cfg.add_section('general')
    cfg['general']['quote_file'] = 'notset'
    cfg['general']['line_separator'] = 'platform'
    cfg['general']['web_page_title'] = 'Test Quotes'
    cfg['general']['quotemap_file'] = ''

    cfg.add_section('lint')
    cfg['lint']['lint_on_add'] = 'false'
    cfg['lint']['lint_author_antipattern_regex'] = ''
    cfg['lint']['lint_enabled_checks'] = 'ascii, smart-quotes, no-tags, no-author, author-antipatterns'
    cfg['lint']['lint_max_quote_length'] = '0'

    cfg.add_section('web')
    cfg['web']['web_port'] = '80'
    cfg['web']['web_ip'] = '0.0.0.0'
    cfg['web']['web_cache_minutes'] = '240'
    cfg['web']['web_show_stars'] = 'false'
    cfg['web']['web_light_foreground_color'] = '#000000'
    cfg['web']['web_light_background_color'] = '#ffffff'
    cfg['web']['web_dark_foreground_color'] = '#ffffff'
    cfg['web']['web_dark_background_color'] = '#000000'

    with tempfile.TemporaryDirectory() as tmpdir:
        config_obj = api.Config(cfg, tmpdir)
        monkeypatch.setattr(api, 'get_config', Mock(return_value=config_obj))
        yield config_obj


@pytest.fixture
def flask_client(tmp_path):
    """Provide a Flask test client with a temporary quote file."""
    from jotquote import web

    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    web.app.testing = True
    web.app.config['QUOTE_FILE'] = quote_file
    with web.app.test_client() as client:
        yield client, quote_file
