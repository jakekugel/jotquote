# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from configparser import ConfigParser
from unittest.mock import Mock

import pytest

import tests.test_util
from jotquote import api


@pytest.fixture
def config(monkeypatch):
    """Provide a test ConfigParser and patch api.get_config to return it."""
    cfg = ConfigParser()
    cfg.add_section(api.APP_NAME)
    cfg[api.APP_NAME]['quote_file'] = 'notset'
    cfg[api.APP_NAME]['line_separator'] = 'platform'
    cfg[api.APP_NAME]['web_port'] = '80'
    cfg[api.APP_NAME]['web_ip'] = '0.0.0.0'
    cfg.add_section('jotquote.lint')
    cfg['jotquote.lint']['enabled_checks'] = (
        'ascii, smart-quotes, spelling, no-tags, no-author, '
        'author-antipatterns, multiple-stars, no-star, no-visibility'
    )
    cfg['jotquote.lint']['visibility_tags'] = ''
    cfg['jotquote.lint']['spell_ignore'] = ''
    cfg['jotquote.lint']['author_antipattern_regex'] = ''
    monkeypatch.setattr(api, 'get_config', Mock(return_value=cfg))
    return cfg


@pytest.fixture
def flask_client(tmp_path):
    """Provide a Flask test client with a temporary quote file."""
    from jotquote import web
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    web.app.testing = True
    web.app.config['QUOTE_FILE'] = quote_file
    with web.app.test_client() as client:
        yield client, quote_file
