# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import pytest

import tests.test_util
from jotquote import api


def test_ascii_only_blocks_non_ascii(config, tmp_path):
    """add_quote() should raise ClickException when ascii_only=true and quote has non-ASCII char."""
    config[api.APP_NAME]['ascii_only'] = 'true'
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")

    non_ascii_quote = api.Quote("Hello\u200aWorld", "Author", None, [])
    with pytest.raises(Exception, match="non-ASCII character"):
        api.add_quote(path, non_ascii_quote)


def test_ascii_only_blocks_non_ascii_in_author(config, tmp_path):
    """add_quote() should raise ClickException when ascii_only=true and author has non-ASCII char."""
    config[api.APP_NAME]['ascii_only'] = 'true'
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")

    non_ascii_quote = api.Quote("A perfectly fine quote", "Ren\u00e9 Author", None, [])
    with pytest.raises(Exception, match="non-ASCII character"):
        api.add_quote(path, non_ascii_quote)


def test_ascii_only_allows_ascii(config, tmp_path):
    """add_quote() should succeed when ascii_only=true and quote is pure ASCII."""
    config[api.APP_NAME]['ascii_only'] = 'true'
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")

    ascii_quote = api.Quote("A perfectly fine ASCII quote", "Plain Author", None, [])
    total = api.add_quote(path, ascii_quote)
    assert total == 5


def test_ascii_only_false_allows_non_ascii(config, tmp_path):
    """add_quote() should succeed when ascii_only=false even if quote has non-ASCII chars."""
    config[api.APP_NAME]['ascii_only'] = 'false'
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")

    non_ascii_quote = api.Quote("Hello\u200aWorld", "Author", None, [])
    total = api.add_quote(path, non_ascii_quote)
    assert total == 5
