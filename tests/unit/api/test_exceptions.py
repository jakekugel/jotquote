# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import pytest

import tests.test_util
from jotquote import api


def test_api_exception_subclass_of_exception():
    """ApiException is a subclass of Exception."""
    assert issubclass(api.ApiException, Exception)


def test_all_concrete_classes_inherit_from_api_exception():
    """All 6 concrete exception classes inherit from ApiException."""
    assert issubclass(api.ConfigError, api.ApiException)
    assert issubclass(api.QuoteValidationError, api.ApiException)
    assert issubclass(api.QuoteNotFoundError, api.ApiException)
    assert issubclass(api.DuplicateQuoteError, api.ApiException)
    assert issubclass(api.ConcurrentModificationError, api.ApiException)
    assert issubclass(api.StorageError, api.ApiException)


def test_quote_validation_error_field_set_on_invalid_author_char():
    """parse_quote() raises QuoteValidationError with field='author' for invalid char in author."""
    with pytest.raises(api.QuoteValidationError) as excinfo:
        api.parse_quote('Quote | Auth\ror | Publication |', simple_format=False)
    assert excinfo.value.field == 'author'


def test_quote_validation_error_field_set_on_invalid_quote_char():
    """parse_quote() raises QuoteValidationError with field='quote' for invalid char in quote text."""
    with pytest.raises(api.QuoteValidationError) as excinfo:
        api.parse_quote('Quote with " in it | Author | Publication |', simple_format=False)
    assert excinfo.value.field == 'quote'


def test_quote_validation_error_field_set_on_invalid_tags():
    """parse_quote() raises QuoteValidationError with field='tags' for invalid tag chars."""
    with pytest.raises(api.QuoteValidationError) as excinfo:
        api.parse_quote('Quote | Author | Publication | tag1, tag!', simple_format=False)
    assert excinfo.value.field == 'tags'


def test_quote_validation_error_no_field_for_structural_error():
    """parse_quote() raises QuoteValidationError with field=None for wrong pipe count."""
    with pytest.raises(api.QuoteValidationError) as excinfo:
        api.parse_quote('This is a quote||', simple_format=False)
    assert excinfo.value.field is None


def test_concurrent_modification_error_carries_sha_attrs(tmp_path):
    """set_quote raises ConcurrentModificationError with expected + current sha populated."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(quote_file)
    line_num = quotes[0].get_line_number()
    actual_sha = api.get_sha256(quote_file)

    new_quote = api.Quote('New text', 'New Author', None, [])
    with pytest.raises(api.ConcurrentModificationError) as excinfo:
        api.set_quote(quote_file, line_num, new_quote, 'bogus_sha256')

    assert excinfo.value.expected_sha256 == 'bogus_sha256'
    assert excinfo.value.current_sha256 == actual_sha


def test_duplicate_quote_error_message_contains_quote_text(config, tmp_path):
    """DuplicateQuoteError message preserves the duplicate quote text."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quote = api.Quote('This is an added quote.', 'Author', None, [])
    api.add_quote(path, quote)

    with pytest.raises(api.DuplicateQuoteError) as excinfo:
        api.add_quote(path, quote)

    assert 'This is an added quote.' in str(excinfo.value)


def test_config_error_raised_when_quote_file_missing(tmp_path, monkeypatch):
    """get_config() raises ConfigError when [general] has no quote_file."""
    config_file = tmp_path / 'settings.conf'
    config_file.write_text('[general]\nline_separator = platform\n', encoding='utf-8')
    monkeypatch.setenv('JOTQUOTE_CONFIG', str(config_file))

    with pytest.raises(api.ConfigError, match='quote_file'):
        api.get_config()
