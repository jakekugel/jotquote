# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
import sys
import tests
import click
import pytest

from jotquote import api

my_args = ()
def test__write_quotes__should_write_to_temp_filename(monkeypatch, tmp_path):
    # Given a quote file with a few quotes in it
    quotefile = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    quotes = api.read_quotes(quotefile)

    # And given the open_file() function wrapped with function that tracks args
    original_open_file = click.open_file
    def mock_open_file(*args, **kwargs):
        global my_args
        my_args = args
        return original_open_file(*args, **kwargs)
    monkeypatch.setattr(click, "open_file", mock_open_file)

    # When write_quotes() called
    api.write_quotes(quotefile, quotes)

    # Then check open_file() called with temporary filename
    assert my_args[0] != quotefile


def test__write_quotes__should_create_backup_file(tmp_path):
    # Given a quote file with a few quotes in it
    quotefile = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    quotes = api.read_quotes(quotefile)

    # When write_quotes() called
    api.write_quotes(quotefile, quotes)

    # Then check open_file() called with temporary filename
    assert os.path.exists(os.path.join(str(tmp_path), '.quotes1.txt.jotquote.bak'))


def test__write_quotes__should_replace_backup_file(tmp_path):
    # Given a quote file with a few quotes in it
    quote_path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    quotes = api.read_quotes(quote_path)
    quote_path_2 = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    quotes2 = api.read_quotes(quote_path_2)

    # When write_quotes() called twice
    api.write_quotes(quote_path, quotes2)
    api.write_quotes(quote_path, quotes)

    # Then backup file has quotes2 content
    backup_quotes = api.read_quotes(os.path.join(str(tmp_path), '.quotes1.txt.jotquote.bak'))
    assert len(backup_quotes) == len(quotes2)
    assert backup_quotes[0] == quotes2[0]


def test__write_quotes__should_not_modify_quote_file_on_write_error(monkeypatch, tmp_path):
    # Given two quote files with a few quotes in each
    quote_path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    quotes = api.read_quotes(quote_path)
    quote_path_2 = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    quotes2 = api.read_quotes(quote_path_2)

    # And given fake writer
    class FakeWriter:
        def __init__(self, path):
            with open(path, 'w') as file:
                file.write('bad contents')

        def __enter__(self):
            return self

        def __exit__(self, arg1, arg2, arg3):
            pass

        def write(self, bytes):
            raise IOError("Fake write error")

    # And given the open_file() function wrapped with function that tracks args
    def fake_open_file(*args, **kwargs):
        return FakeWriter(args[0])
    original_open_file = click.open_file
    monkeypatch.setattr(click, "open_file", fake_open_file)

    # When write_quotes() called
    with pytest.raises(click.ClickException) as excinfo:
        api.write_quotes(quote_path, quotes2)

    # Then check quote_path was not modified
    monkeypatch.setattr(click, "open_file", original_open_file)
    assert "an error occurred writing the quotes.  The file '{0}' was not modified.".format(quote_path) == str(excinfo.value)
    assert tests.test_util.compare_quotes(quotes, api.read_quotes(quote_path))


def test__write_quotes__should_return_good_exception_when_backup_larger_than_quote_file(monkeypatch, tmp_path):
    # Given a quote file quotes5.txt with a single quote in it
    quote_path = tests.test_util.init_quotefile(str(tmp_path), "quotes5.txt")
    quotes = api.read_quotes(quote_path)

    # And given a backup file .quotes5.txt.jotquote.bak with 4 quotes in it
    quotes_path_2 = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    backup_path = os.path.join(str(tmp_path), '.quotes5.txt.jotquote.bak')
    os.rename(quotes_path_2, backup_path)

    # When write_quotes() called to write quotes to quotes5.txt
    with pytest.raises(click.ClickException) as excinfo:
        api.write_quotes(quote_path, quotes)

    # Then an error message returned indicating backup file larger than new quotes5.txt
    assert "the backup file '.quotes5.txt.jotquote.bak' is larger than the quote file 'quotes5.txt' would be after this operation.  This is suspicious, the quote file was not modified.  If this was expected, delete the backup file and try again." == str(excinfo.value)
    assert tests.test_util.compare_quotes(quotes, api.read_quotes(quote_path))
