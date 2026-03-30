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
    cfg.add_section(api.SECTION_GENERAL)
    cfg[api.SECTION_GENERAL]['quote_file'] = 'notset'
    cfg[api.SECTION_GENERAL]['line_separator'] = 'platform'
    cfg.add_section(api.SECTION_LINT)
    cfg[api.SECTION_LINT]['enabled_checks'] = 'ascii, smart-quotes, no-tags, no-author, author-antipatterns'
    cfg[api.SECTION_LINT]['author_antipattern_regex'] = ''
    cfg.add_section(api.SECTION_WEB)
    cfg[api.SECTION_WEB]['port'] = '80'
    cfg[api.SECTION_WEB]['ip'] = '0.0.0.0'
    monkeypatch.setattr(api, 'get_config', Mock(return_value=(cfg, False)))
    return cfg


@pytest.fixture
def flask_client(tmp_path):
    """Provide a Flask test client with a temporary quote file."""
    from jotquote import web_viewer

    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    web_viewer.app.testing = True
    web_viewer.app.config['QUOTE_FILE'] = quote_file
    with web_viewer.app.test_client() as client:
        yield client, quote_file
