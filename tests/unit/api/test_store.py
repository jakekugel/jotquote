# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import hashlib
import os
import re

import click
import pytest

import tests.test_util
from jotquote import api
from jotquote.api import store as store_mod


def test_read_quotes(tmp_path):
    """Test read_quotes() basic functionality"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(path)
    assert len(quotes) == 4


def test_read_quotes_fnf(tmp_path):
    """read_quotes() should raise exception if file not found."""
    path = os.path.join(str(tmp_path), 'fakename.txt')
    with pytest.raises(Exception, match=re.escape("The quote file '{0}' was not found.".format(path))):
        api.read_quotes(path)


def test_read_quotes_empty_file(tmp_path):
    """read_quotes() should work if empty file."""
    path = os.path.join(str(tmp_path), 'emptyfile.txt')
    open(path, 'a').close()
    quotes = api.read_quotes(path)
    assert len(quotes) == 0


def test_read_quotes_no_final_newline(tmp_path):
    """read_quotes() should work even if no final newline"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    quotes = api.read_quotes(path)
    assert len(quotes) == 4


def test_read_quotes_blank_lines(tmp_path):
    """read_quotes() should allow blank lines"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes3.txt')
    quotes = api.read_quotes(path)
    assert len(quotes) == 4


def test_read_quotes_commented_lines(tmp_path):
    """read_quotes() should allow lines commented with #"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes4.txt')
    quotes = api.read_quotes(path)
    assert len(quotes) == 4


def test_read_quotes_with_extra_pipe_character_in_quotefile(tmp_path):
    """read_quotes() should raise exception if there is extra pipe character on line."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes6.txt')
    with pytest.raises(
        Exception,
        match=re.escape(
            'syntax error on line 1 of {0}: did not find 3 \'|\' characters.  Line with error: "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.|Ben Franklin||U|"'.format(
                path
            )
        ),
    ):
        api.read_quotes(path)


def test_read_quotes_with_double_quote_in_quotefile(tmp_path):
    """read_quotes() should raise exception if there is a double-quote character in the quote."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes7.txt')
    with pytest.raises(
        Exception,
        match=re.escape(
            'syntax error on line 2 of {0}: the quote included a (") character.  Line with error: "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor " safety.|Ben Franklin||U"'.format(
                path
            )
        ),
    ):
        api.read_quotes(path)


def test_add_quote(config, tmp_path):
    """add_quote() method should add single quote to end of quote file."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    quote = api.Quote('  This is an added quote.', 'Another author', 'Publication', ['tag1, tag2'])

    api.add_quote(path, quote)

    with open(path, 'rb') as file:
        data = file.read()
    text_data = data.decode('utf-8')
    expected = (
        'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U'
        + os.linesep
        + 'This is an added quote. | Another author | Publication | tag1, tag2'
        + os.linesep
    )
    assert text_data == expected


def test_add_quote_but_file_not_found(config, tmp_path):
    """Test that add_quote() raises exception if quote file does not exist."""
    quote = api.Quote('  This is an added quote.', 'Another author', 'Publication', ['tag1, tag2'])
    quotefile = os.path.join(str(tmp_path), 'fakename.txt')
    with pytest.raises(Exception, match=re.escape("The quote file '{0}' does not exist.".format(quotefile))):
        api.add_quote(quotefile, quote)


def test_add_quote_but_quote_object_not_passed(config, tmp_path):
    """Test that add_quote() raises exception if object passed is not Quote object."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    with pytest.raises(Exception, match=re.escape('The quote parameter must be type class Quote.')):
        api.add_quote(path, None)


def test_add_quote_but_file_contains_quote_already(config, tmp_path):
    """Test that add_quote() raises exception if new quote already in quote file."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quote = api.Quote('  This is an added quote.', 'Another author', 'Publication', ['tag1, tag2'])
    api.add_quote(path, quote)

    with pytest.raises(
        Exception, match=re.escape('the quote "This is an added quote." is already in the quote file {0}.'.format(path))
    ):
        api.add_quote(path, quote)


def test_check_for_duplicates_with_duplicates():
    """The _check_for_duplicates function should raise exception if there are duplicate quotes."""
    quotes = [
        api.Quote('  This is an added quote.', 'Another author', 'Publication', ['tag1, tag2']),
        api.Quote('  This is an added quote.', 'Another author2', 'Publication', ['tag1, tag2']),
        api.Quote('  This is an added quote.', 'Another author3', 'Publication', ['tag1, tag2']),
    ]

    with pytest.raises(
        Exception,
        match=re.escape('a duplicate quote was found on line 2 of \'stdin\'.  Quote: "This is an added quote."'),
    ):
        store_mod._check_for_duplicates(quotes, 'stdin')


def test_check_for_duplicates():
    quotes = [
        api.Quote('  This is an added quote.', 'Another author', 'Publication', ['tag1, tag2']),
        api.Quote('  This is a different added quote.', 'Another author2', 'Publication', ['tag1, tag2']),
        api.Quote('  This is yet another added quote.', 'Another author3', 'Publication', ['tag1, tag2']),
    ]

    store_mod._check_for_duplicates(quotes, 'testcase')


def test_write_quotes(config, tmp_path):
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(path)
    quote = api.Quote('Another new quote', 'author', None, [])
    quotes.append(quote)

    api.write_quotes(path, quotes)

    quotes = api.read_quotes(path)
    assert quotes[-1].quote == 'Another new quote'
    assert quotes[-1].author == 'author'


def test_write_quotes_unix(config, tmp_path):
    """If property line_separator = unix, then line separator should be \\n."""
    config[api.SECTION_GENERAL]['line_separator'] = 'unix'

    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(path)
    api.write_quotes(path, quotes)

    with open(path, 'rb') as openfile:
        whole_file = openfile.read().decode('utf-8')
    expected = (
        "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it. | Linus Torvalds |  | U\n"
        + "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. | Mitch Hedberg |  | U\n"
        + 'Ask for what you want and be prepared to get it. | Maya Angelou |  | U\n'
        + 'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n'
    )
    assert whole_file == expected


def test_write_quotes_windows(config, tmp_path):
    """If line_separator = windows, then line separator should be \\r\\n."""
    config[api.SECTION_GENERAL]['line_separator'] = 'windows'

    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(path)
    api.write_quotes(path, quotes)

    with open(path, 'rb') as binfile:
        whole_file = binfile.read()
    expected = (
        b"The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. "
        + b"Yes, that's it. | Linus Torvalds |  | U\r\n"
        + b"The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. | Mitch Hedberg |  | U\r\n"
        + b'Ask for what you want and be prepared to get it. | Maya Angelou |  | U\r\n'
        + b'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\r\n'
    )
    assert whole_file == expected


def test_write_quotes_invalid(config, tmp_path):
    """The write_quotes() function should raise exception if invalid line_separator config property."""
    config[api.SECTION_GENERAL]['line_separator'] = 'VAX-VMS'

    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(path)

    with pytest.raises(
        Exception,
        match=re.escape(
            "the value 'VAX-VMS' is not valid value for the line_separator property.  Valid "
            "values are 'platform', 'windows', or 'unix'."
        ),
    ):
        api.write_quotes(path, quotes)


def test_write_quotes_fnf(config, tmp_path):
    """write_quotes() should raise exception if quote file does not exist."""
    path = os.path.join(str(tmp_path), 'fakename.txt')
    quote = api.Quote('Another new quote', 'author', None, [])
    quotes = [quote]

    with pytest.raises(Exception, match=re.escape("the quote file '{0}' was not found.".format(path))):
        api.write_quotes(path, quotes)


def test__write_quotes__should_write_to_temp_filename(config, monkeypatch, tmp_path):
    # Given a quote file with a few quotes in it
    quotefile = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(quotefile)

    # And given the open_file() function wrapped with function that tracks args
    original_open_file = click.open_file
    captured_args = []

    def mock_open_file(*args, **kwargs):
        captured_args.append(args)
        return original_open_file(*args, **kwargs)

    monkeypatch.setattr(click, 'open_file', mock_open_file)

    # When write_quotes() called
    api.write_quotes(quotefile, quotes)

    # Then check open_file() called with temporary filename
    assert captured_args[0][0] != quotefile


def test__write_quotes__should_create_backup_file(config, tmp_path):
    # Given a quote file with a few quotes in it
    quotefile = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(quotefile)

    # When write_quotes() called
    api.write_quotes(quotefile, quotes)

    # Then check backup file created
    assert os.path.exists(os.path.join(str(tmp_path), '.quotes1.txt.jotquote.bak'))


def test__write_quotes__should_replace_backup_file(config, tmp_path):
    # Given a quote file with a few quotes in it
    quote_path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(quote_path)
    quote_path_2 = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes2 = api.read_quotes(quote_path_2)

    # When write_quotes() called twice
    api.write_quotes(quote_path, quotes2)
    api.write_quotes(quote_path, quotes)

    # Then backup file has quotes2 content
    backup_quotes = api.read_quotes(os.path.join(str(tmp_path), '.quotes1.txt.jotquote.bak'))
    assert len(backup_quotes) == len(quotes2)
    assert backup_quotes[0] == quotes2[0]


def test__write_quotes__should_not_modify_quote_file_on_write_error(config, monkeypatch, tmp_path):
    # Given two quote files with a few quotes in each
    quote_path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(quote_path)
    quote_path_2 = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
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
            raise IOError('Fake write error')

    # And given the open_file() function replaced with fake writer
    def fake_open_file(*args, **kwargs):
        return FakeWriter(args[0])

    original_open_file = click.open_file
    monkeypatch.setattr(click, 'open_file', fake_open_file)

    # When write_quotes() called
    with pytest.raises(click.ClickException) as excinfo:
        api.write_quotes(quote_path, quotes2)

    # Then check quote_path was not modified
    monkeypatch.setattr(click, 'open_file', original_open_file)
    assert "an error occurred writing the quotes.  The file '{0}' was not modified.".format(quote_path) == str(
        excinfo.value
    )
    assert tests.test_util.compare_quotes(quotes, api.read_quotes(quote_path))


def test__write_quotes__should_return_good_exception_when_backup_larger_than_quote_file(config, tmp_path):
    # Given a quote file quotes5.txt with a single quote in it
    quote_path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    quotes = api.read_quotes(quote_path)

    # And given a backup file .quotes5.txt.jotquote.bak with 4 quotes in it
    quotes_path_2 = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    backup_path = os.path.join(str(tmp_path), '.quotes5.txt.jotquote.bak')
    os.rename(quotes_path_2, backup_path)

    # When write_quotes() called to write quotes to quotes5.txt
    with pytest.raises(click.ClickException) as excinfo:
        api.write_quotes(quote_path, quotes)

    # Then an error message returned indicating backup has more lines than new quotes5.txt
    assert "the backup file '.quotes5.txt.jotquote.bak' has" in str(excinfo.value)
    assert 'lines but the quote file' in str(excinfo.value)
    assert 'This is suspicious' in str(excinfo.value)
    assert tests.test_util.compare_quotes(quotes, api.read_quotes(quote_path))


def test_duplicate_quotes(tmp_path):
    """The read_quotes() function should raise exception if there are duplicate quotes."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes8.txt')
    with pytest.raises(
        Exception,
        match=re.escape(
            "a duplicate quote was found on line 5 of '{}'.  Quote: \"The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall.\"".format(
                path
            )
        ),
    ):
        api.read_quotes(path)


# --- settags() tests ---


def test_settags_by_hash(config, tmp_path):
    """settags() should update tags on a quote identified by hash."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')

    # Hash for "Ask for what you want and be prepared to get it." (quote 3)
    api.settags(path, n=None, hash='a3bff52cabf7e859', newtags=['newtag1', 'newtag2'])

    quotes = api.read_quotes(path)
    assert quotes[2].tags == ['newtag1', 'newtag2']
    # Other quotes unchanged
    assert quotes[0].tags == ['U']
    assert quotes[1].tags == ['U']


def test_settags_by_number(config, tmp_path):
    """settags() should update tags on a quote identified by 1-based number."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')

    api.settags(path, n=1, hash=None, newtags=['firsttag'])

    quotes = api.read_quotes(path)
    assert quotes[0].tags == ['firsttag']
    # Other quotes unchanged
    assert quotes[1].tags == ['U']


def test_settags_clears_tags(config, tmp_path):
    """settags() with newtags=[] should clear all tags from the quote."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')

    api.settags(path, n=1, hash=None, newtags=[])

    quotes = api.read_quotes(path)
    assert quotes[0].tags == []


def test_settags_both_n_and_hash_raises(config, tmp_path):
    """settags() should raise ClickException if both n and hash are provided."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')

    with pytest.raises(
        click.ClickException, match=re.escape('both the -s and -n option were included, but only one allowed.')
    ):
        api.settags(path, n=1, hash='a3bff52cabf7e859', newtags=['tag1'])


def test_settags_neither_n_nor_hash_raises(config, tmp_path):
    """settags() should raise ClickException if neither n nor hash is provided."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')

    with pytest.raises(click.ClickException, match=re.escape('either the -n or the -s argument must be included.')):
        api.settags(path, n=None, hash=None, newtags=['tag1'])


def test_settags_hash_not_found_raises(config, tmp_path):
    """settags() should raise ClickException if the given hash matches no quote."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')

    with pytest.raises(click.ClickException, match=re.escape("no quote found with hash 'deadbeefdeadbeef'.")):
        api.settags(path, n=None, hash='deadbeefdeadbeef', newtags=['tag1'])


def test_settags_n_out_of_range_raises(config, tmp_path):
    """settags() should raise ClickException if n is out of range."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')

    with pytest.raises(click.ClickException, match=re.escape('quote number 99 is out of range (1-4).')):
        api.settags(path, n=99, hash=None, newtags=['tag1'])


class TestGetSha256:
    def test_get_sha256(self, tmp_path):
        """get_sha256 returns correct hex digest for a known file."""
        f = tmp_path / 'test.txt'
        f.write_bytes(b'hello world\n')
        expected = hashlib.sha256(b'hello world\n').hexdigest()
        assert api.get_sha256(str(f)) == expected

    def test_get_sha256_changes_after_write(self, tmp_path):
        """Checksum changes after the file is modified."""
        f = tmp_path / 'test.txt'
        f.write_bytes(b'original')
        sha1 = api.get_sha256(str(f))
        f.write_bytes(b'modified')
        sha2 = api.get_sha256(str(f))
        assert sha1 != sha2


class TestSetQuote:
    def test_set_quote_success(self, tmp_path):
        """set_quote updates the quote at the given line number."""
        quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
        quotes = api.read_quotes(quote_file)
        original_quote = quotes[0]
        line_num = original_quote.get_line_number()
        sha256 = api.get_sha256(quote_file)

        new_quote = api.Quote('New text', 'New Author', None, ['newtag'])
        api.set_quote(quote_file, line_num, new_quote, sha256)

        updated_quotes = api.read_quotes(quote_file)
        updated = updated_quotes[0]
        assert updated.quote == 'New text'
        assert updated.author == 'New Author'
        assert updated.publication in (None, '')
        assert updated.tags == ['newtag']

    def test_set_quote_sha256_mismatch(self, tmp_path):
        """set_quote raises ClickException when SHA256 does not match."""
        quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
        quotes = api.read_quotes(quote_file)
        line_num = quotes[0].get_line_number()

        new_quote = api.Quote('New text', 'New Author', None, [])
        with pytest.raises(click.ClickException, match='modified since it was last read'):
            api.set_quote(quote_file, line_num, new_quote, 'bogus_sha256')

    def test_set_quote_invalid_line_number(self, tmp_path):
        """set_quote raises ClickException for a nonexistent line number."""
        quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
        sha256 = api.get_sha256(quote_file)

        new_quote = api.Quote('New text', 'New Author', None, [])
        with pytest.raises(click.ClickException, match='No quote found at line number'):
            api.set_quote(quote_file, 999, new_quote, sha256)


# ---------------------------------------------------------------------------
# read_quotes_with_hash tests
# ---------------------------------------------------------------------------


def test_read_quotes_with_hash_returns_correct_quotes_and_hash(tmp_path):
    """read_quotes_with_hash() returns quotes and a matching SHA-256 hash."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes, sha256_hex = api.read_quotes_with_hash(quote_file)
    assert len(quotes) == 4
    with open(quote_file, 'rb') as f:
        expected_hash = hashlib.sha256(f.read()).hexdigest()
    assert sha256_hex == expected_hash


def test_read_quotes_with_hash_changes_on_file_change(tmp_path):
    """Hash changes when the file content changes."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    _, hash1 = api.read_quotes_with_hash(quote_file)
    with open(quote_file, 'a', encoding='utf-8') as f:
        f.write('Extra quote | Extra Author | | tag1\n')
    _, hash2 = api.read_quotes_with_hash(quote_file)
    assert hash1 != hash2


def test_read_quotes_with_hash_file_not_found(tmp_path):
    """read_quotes_with_hash() raises ClickException for nonexistent file."""
    path = os.path.join(str(tmp_path), 'nonexistent.txt')
    with pytest.raises(click.ClickException, match='was not found'):
        api.read_quotes_with_hash(path)


def test_read_quotes_with_hash_consistent_with_read_quotes(tmp_path):
    """read_quotes() returns the same quotes as read_quotes_with_hash()."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes_plain = api.read_quotes(quote_file)
    quotes_hash, _ = api.read_quotes_with_hash(quote_file)
    assert quotes_plain == quotes_hash


# ---------------------------------------------------------------------------
# write_quotes expected_sha256 tests
# ---------------------------------------------------------------------------


def test_write_quotes_succeeds_with_matching_hash(tmp_path):
    """write_quotes() succeeds when expected_sha256 matches the file."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes, sha256 = api.read_quotes_with_hash(quote_file)
    quotes[0].set_tags(['newtag'])
    api.write_quotes(quote_file, quotes, expected_sha256=sha256)
    updated = api.read_quotes(quote_file)
    assert updated[0].tags == ['newtag']


def test_write_quotes_fails_with_mismatched_hash(tmp_path):
    """write_quotes() raises ClickException when expected_sha256 does not match."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes, sha256 = api.read_quotes_with_hash(quote_file)
    # Modify file externally
    with open(quote_file, 'a', encoding='utf-8') as f:
        f.write('Injected quote | Injected Author | | tag1\n')
    with pytest.raises(click.ClickException, match='modified by another process'):
        api.write_quotes(quote_file, quotes, expected_sha256=sha256)


def test_write_quotes_succeeds_with_none_hash(tmp_path):
    """write_quotes() succeeds when expected_sha256 is None (backwards compatible)."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    quotes = api.read_quotes(quote_file)
    quotes[0].set_tags(['newtag'])
    api.write_quotes(quote_file, quotes)
    updated = api.read_quotes(quote_file)
    assert updated[0].tags == ['newtag']


# ---------------------------------------------------------------------------
# Concurrent modification detection in settags / add_quotes
# ---------------------------------------------------------------------------


def test_settags_fails_on_concurrent_modification(tmp_path, config):
    """settags() raises ClickException when quote file is modified externally."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.SECTION_GENERAL]['quote_file'] = str(quote_file)

    # Monkey-patch read_quotes_with_hash to modify the file after reading
    original_fn = store_mod.read_quotes_with_hash

    def _modified_read(filename):
        quotes, sha256 = original_fn(filename)
        with open(filename, 'a', encoding='utf-8') as f:
            f.write('Injected quote | Injected Author | | tag1\n')
        return quotes, sha256

    store_mod.read_quotes_with_hash = _modified_read
    try:
        with pytest.raises(click.ClickException, match='modified by another process'):
            api.settags(quote_file, 1, None, ['newtag'])
    finally:
        store_mod.read_quotes_with_hash = original_fn


def test_add_quotes_fails_on_concurrent_modification(tmp_path, config):
    """add_quotes() raises ClickException when quote file is modified externally."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.SECTION_GENERAL]['quote_file'] = str(quote_file)

    original_fn = store_mod.read_quotes_with_hash

    def _modified_read(filename):
        quotes, sha256 = original_fn(filename)
        with open(filename, 'a', encoding='utf-8') as f:
            f.write('Injected quote | Injected Author | | tag1\n')
        return quotes, sha256

    store_mod.read_quotes_with_hash = _modified_read
    try:
        new_quote = api.Quote('Brand new quote', 'Brand New Author', None, [])
        with pytest.raises(click.ClickException, match='modified by another process'):
            api.add_quotes(quote_file, [new_quote])
    finally:
        store_mod.read_quotes_with_hash = original_fn
