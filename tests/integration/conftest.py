# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import pytest

import tests.test_util
from jotquote.web import viewer as web


@pytest.fixture
def flask_client(tmp_path):
    """Provide a Flask test client with a temporary quote file."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    web.app.testing = True
    web.app.config['QUOTE_FILE'] = quote_file
    with web.app.test_client() as client:
        yield client, quote_file
