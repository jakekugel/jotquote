# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime as real_datetime
import hashlib
import os
import re
from configparser import ConfigParser

import click
import pytest

import tests.test_util
from jotquote import api


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


def test_parse_quotes():
    """parse_quotes() should parse a pipe-delimited quote string."""
    quote = api.parse_quote('  This is a quote. |  Author  | Publication   | tag1, tag2 , tag3  ', simple_format=False)
    assert quote.quote == 'This is a quote.'
    assert quote.author == 'Author'
    assert quote.publication == 'Publication'
    assert len(quote.tags) == 3


def test_parse_quotes_doublequote():
    """parse_quote() should raise exception if there is double quote in quote being parsed."""
    with pytest.raises(Exception, match=re.escape('the quote included a (") character')):
        api.parse_quote('  This is a quote". |  Author  | Publication   | tag1, tag2 , tag3  ', simple_format=False)


def test_parse_quotes_not_three_vertical_bars():
    """parse_quote() should raise exception if there are not three pipe characters"""
    with pytest.raises(Exception, match=re.escape("did not find 3 '|' characters")):
        api.parse_quote('  This is a quote||', simple_format=False)


def test_parse_quotes_no_quote():
    """parse_quote() should raise exception if the quote field is empty."""
    with pytest.raises(Exception, match='a quote was not found'):
        api.parse_quote('|  Author  | Publication   | tag1, tag2 , tag3  ', simple_format=False)


def test_parse_quotes_no_author():
    """parse_quote() should raise exception if there is no author."""
    with pytest.raises(
        Exception,
        match=re.escape(
            'an author was not included with the quote.  Expecting quote in the format "<quote> - <author>".'
        ),
    ):
        api.parse_quote('This is a quote. | | Publication   | tag1, tag2 , tag3  ', simple_format=False)


def test_parse_quotes_alphanumerics_only_in_tags():
    """parse_quote() should raise exception if there are invalid characters in tags."""
    with pytest.raises(
        click.ClickException, match="invalid tag 'tag3!': only numbers, letters, and commas are allowed in tags"
    ):
        api.parse_quote('This is a quote. | Author | Publication   | tag1, tag2 , tag3!  ', simple_format=False)


def test_parse_simple_quote():
    """parse_quote() should work when parsing a quote in simple format."""
    quote = api.parse_quote('  We accept the love we think we deserve.  - Stephen Chbosky', simple_format=True)
    assert quote.quote == 'We accept the love we think we deserve.'
    assert quote.author == 'Stephen Chbosky'
    assert quote.publication is None
    assert len(quote.tags) == 0


def test_parse_simple_quote_with_double_quote():
    """Not allowed to have double quote character in quote itself"""
    with pytest.raises(Exception, match=re.escape('the quote included a (") character')):
        api.parse_quote('  We accept the love we think we " deserve.  - Stephen Chbosky', simple_format=True)


def test_parse_simple_quote_with_double_quote_in_author():
    """It is supported to have a double quote character in the author."""
    quote = api.parse_quote(
        '  Hey, grades are not cool, learning is cool. - Arthur "Fonzie" Fonzarelli', simple_format=True
    )
    assert quote.author == 'Arthur "Fonzie" Fonzarelli'


def test_parse_simple_quote_with_no_hyphen():
    """Test that parse_quote() raises exception if there is not a hyphen."""
    with pytest.raises(
        Exception, match=re.escape('unable to determine which hyphen separates the quote from the author.')
    ):
        api.parse_quote('  We accept the love we think we deserve. Stephen Chbosky', simple_format=True)


def test_parse_simple_quote_with_no_quote():
    """parse_quote() should raise exception if parsing simple format and there is no quote before hyphen."""
    with pytest.raises(Exception, match=re.escape('a quote was not found')):
        api.parse_quote(' - Hamlet  ', simple_format=True)


def test_parse_simple_quote_with_no_author():
    """parse_quote() should raise exception if parsing simple format and no author after hyphen."""
    with pytest.raises(
        Exception,
        match=re.escape(
            "unable to parse the author and publication.  Try 'Quote - Author (Publication)', or 'Quote - Author, Publication'"
        ),
    ):
        api.parse_quote(' Quote -   ', simple_format=True)


def test_parse_simple_quote_with_pipe_character():
    """parse_quote() should raise exception if parsing simple format and there is a pipe character."""
    with pytest.raises(Exception, match=re.escape('the quote included an embedded pipe character (|)')):
        api.parse_quote(' Quote with | character - Author', simple_format=True)


def test_parse_simple_quote_with_newline():
    """parse_quote() should raise exception if parsing simple format and there is a newline char."""
    with pytest.raises(Exception, match=re.escape('the quote included a newline (0x0a) character')):
        api.parse_quote(' Quote with \n character - Author', simple_format=True)


def test_parse_simple_quote_with_carriage_return():
    """parse_quote() should raise exception if parsing simple format and there is a carriage return char."""
    with pytest.raises(Exception, match=re.escape('the quote included a carriage return (0x0d) character')):
        api.parse_quote(' Quote with \r character - Author', simple_format=True)


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
        api._check_for_duplicates(quotes, 'stdin')


def test_check_for_duplicates():
    quotes = [
        api.Quote('  This is an added quote.', 'Another author', 'Publication', ['tag1, tag2']),
        api.Quote('  This is a different added quote.', 'Another author2', 'Publication', ['tag1, tag2']),
        api.Quote('  This is yet another added quote.', 'Another author3', 'Publication', ['tag1, tag2']),
    ]

    api._check_for_duplicates(quotes, 'testcase')


def test_parse_tags():
    tagstring = '  tag1  , tag2 , tag3  , '
    tags = api.parse_tags(tagstring)
    assert tags[0] == 'tag1'
    assert tags[1] == 'tag2'
    assert tags[2] == 'tag3'


def test_parse_tags_complex():
    tagstring = '    , tag2 , tag3  ,,  , , tag2 , tag1 '
    tags = api.parse_tags(tagstring)
    assert tags[0] == 'tag1'
    assert tags[1] == 'tag2'
    assert tags[2] == 'tag3'


def test_parse_tags_with_underscores():
    tagstring = '    , tag_2 , tag3_  ,,  , , tag2 , tag1 '
    tags = api.parse_tags(tagstring)
    assert tags[0] == 'tag1'
    assert tags[1] == 'tag2'
    assert tags[2] == 'tag3_'
    assert tags[3] == 'tag_2'


def test_parse_tags_invalid():
    """The parse_tags() method should raise exception if invalid character in tag"""
    tagstring = 'tag1, tag2, tag3!'
    with pytest.raises(
        Exception, match=re.escape("invalid tag 'tag3!': only numbers, letters, and commas are allowed in tags")
    ):
        api.parse_tags(tagstring)


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


def test_has_tag():
    quote = api.Quote('New quote', 'New author', 'New publication', ['tag1', 'tag3', 'tag5'])
    assert quote.has_tag('tag1')
    assert not quote.has_tag('tagA')


def test_has_tags():
    quote = api.Quote('New quote', 'New author', 'New publication', ['tag1', 'tag3', 'tag5'])
    assert quote.has_tags(['tag1', 'tag3'])
    assert not quote.has_tags(['tag1', 'tagA'])
    assert quote.has_tags([])


def test_has_keyword():
    quote = api.Quote('New quote', 'New author', 'New publication', ['tag1', 'tag3', 'tag5'])
    assert quote.has_keyword('quote')
    assert quote.has_keyword('author')
    assert quote.has_keyword('publication')
    assert quote.has_keyword('tag3')
    assert not quote.has_keyword('tagA')


@pytest.mark.parametrize(
    'days, numvalues, expected',
    [
        (5, 10, 4),
        (3, 15, 5),
        (199, 100, 49),
    ],
)
def test_get_random_value(days, numvalues, expected):
    assert api._get_random_value(days, numvalues) == expected


def test_get_random_value_sequence():
    items = [api._get_random_value(i, 8) for i in range(12)]
    assert items == [4, 1, 5, 2, 0, 3, 7, 6, 4, 1, 5, 2]


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


def test_assert_does_not_contain_period():
    """The internal _assert_does_not_contain function should raise exception if char in text."""
    with pytest.raises(Exception, match=re.escape('the quote included a (.) character')):
        api._assert_does_not_contain('There is a period in this string.', '.', 'quote')


def test_assert_does_not_contain_newline():
    """The internal _assert_does_not_contain function should raise exception if char missing from text."""
    with pytest.raises(Exception, match=re.escape('the quote included a newline (0x0a) character')):
        api._assert_does_not_contain('There is a newline (\n) in this string.', '\n', 'quote')


@pytest.mark.parametrize(
    'raw_quote, expected_quote, expected_author, expected_publication',
    [
        ('This is a quote. - Author', 'This is a quote.', 'Author', None),
        ('This is-a quote. - Author', 'This is-a quote.', 'Author', None),
        ('This is a quote. - Author-name', 'This is a quote.', 'Author-name', None),
        ('This is a quote.-Author', 'This is a quote.', 'Author', None),
        (
            'This is a quote with alternative-punctuation! - Author',
            'This is a quote with alternative-punctuation!',
            'Author',
            None,
        ),
        ('This is a quote. - Author(My Publication)', 'This is a quote.', 'Author', 'My Publication'),
        ('This is a quote. - Author (My Publication)', 'This is a quote.', 'Author', 'My Publication'),
        ('This is a quote. - Author,(My Publication)', 'This is a quote.', 'Author', 'My Publication'),
        ('This is a quote. - Author, (My Publication)', 'This is a quote.', 'Author', 'My Publication'),
        ("This is a quote. - Author,'My Publication-name'", 'This is a quote.', 'Author', 'My Publication-name'),
        ("This is a quote. - Author, 'My Publication-name'", 'This is a quote.', 'Author', 'My Publication-name'),
        ('This is a quote. - Author, Publication', 'This is a quote.', 'Author', 'Publication'),
    ],
)
def test__parse_quote_simple__should_parse_out_author_and_publication(
    raw_quote, expected_quote, expected_author, expected_publication
):
    quote, author, publication, tags = api._parse_quote_simple(raw_quote)
    assert quote == expected_quote
    assert author == expected_author
    assert publication == expected_publication
    assert tags == []


@pytest.mark.parametrize(
    'raw_quote, error_message',
    [
        (
            'This is a quote. - Author name (publication name) more stuff',
            "unable to parse the author and publication.  Try 'Quote - Author (Publication)', or 'Quote - Author, Publication'",
        ),
        (
            'This is-a quote. - Author name, publication name, more stuff',
            "unable to parse the author and publication.  Try 'Quote - Author (Publication)', or 'Quote - Author, Publication'",
        ),
        ('This-is-a quote-Author-name', 'unable to determine which hyphen separates the quote from the author.'),
        ('This - is a quote - Author', 'unable to determine which hyphen separates the quote from the author.'),
        (
            "This is a quote. - Author 'The-Rock' Last Name",
            "unable to parse the author and publication.  Try 'Quote - Author (Publication)', or 'Quote - Author, Publication'",
        ),
    ],
)
def test__parse_quote_simple__should_raise_exception_if_not_parseable(raw_quote, error_message):
    with pytest.raises(click.ClickException, match=re.escape(error_message)):
        api._parse_quote_simple(raw_quote)


def test_get_random_choice_uses_today_before_cutoff(monkeypatch):
    """Before 11:45 PM, today's date drives quote selection."""

    class FakeDatetime(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 3, 14, 23, 44, 0)

    monkeypatch.setattr(api.datetime, 'datetime', FakeDatetime)
    result = api.get_random_choice(100)
    beginday = real_datetime.date(2016, 1, 1)
    days = (real_datetime.date(2026, 3, 14) - beginday).days
    assert result == api._get_random_value(days, 100)


def test_get_random_choice_uses_tomorrow_at_cutoff(monkeypatch):
    """At 11:45 PM exactly, tomorrow's date drives quote selection."""

    class FakeDatetime(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 3, 14, 23, 45, 0)

    monkeypatch.setattr(api.datetime, 'datetime', FakeDatetime)
    result = api.get_random_choice(100)
    beginday = real_datetime.date(2016, 1, 1)
    days = (real_datetime.date(2026, 3, 15) - beginday).days
    assert result == api._get_random_value(days, 100)


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


# --- get_first_match() tests ---


@pytest.fixture
def sample_quotes():
    return [
        api.Quote('Python is great', 'Guido', '', ['programming', 'fun']),
        api.Quote('Python is elegant', 'Alice', '', ['programming', 'serious']),
        api.Quote('Nature is beautiful', 'Bob', '', ['nature']),
        api.Quote('Life is short', 'Guido', '', ['life', 'fun']),
    ]


def test_get_first_match_no_criteria(sample_quotes):
    """No criteria returns the first quote."""
    result = api.get_first_match(sample_quotes)
    assert result == sample_quotes[0]


def test_get_first_match_keyword_in_quote_text(sample_quotes):
    """keyword matches against quote text."""
    result = api.get_first_match(sample_quotes, keyword='elegant')
    assert result == sample_quotes[1]


def test_get_first_match_keyword_in_author(sample_quotes):
    """keyword matches against the author field, returning the first match."""
    result = api.get_first_match(sample_quotes, keyword='Guido')
    assert result == sample_quotes[0]


def test_get_first_match_keyword_no_match(sample_quotes):
    """keyword with no match returns None."""
    result = api.get_first_match(sample_quotes, keyword='xyz')
    assert result is None


def test_get_first_match_tags(sample_quotes):
    """tags returns the first quote that has the tag."""
    result = api.get_first_match(sample_quotes, tags='nature')
    assert result == sample_quotes[2]


def test_get_first_match_tags_returns_first_of_multiple(sample_quotes):
    """When multiple quotes match a tag, the first one is returned."""
    result = api.get_first_match(sample_quotes, tags='fun')
    assert result == sample_quotes[0]


def test_get_first_match_tags_no_match(sample_quotes):
    """tags with no match returns None."""
    result = api.get_first_match(sample_quotes, tags='missing')
    assert result is None


def test_get_first_match_multiple_tags_all_present(sample_quotes):
    """Multiple tags: quote must have all of them."""
    result = api.get_first_match(sample_quotes, tags='programming, fun')
    assert result == sample_quotes[0]


def test_get_first_match_multiple_tags_partial_match(sample_quotes):
    """No quote has all three tags, so returns None."""
    result = api.get_first_match(sample_quotes, tags='programming, fun, nature')
    assert result is None


def test_get_first_match_number(sample_quotes):
    """number returns the quote at that 1-based position."""
    result = api.get_first_match(sample_quotes, number=3)
    assert result == sample_quotes[2]


def test_get_first_match_number_out_of_range(sample_quotes):
    """number larger than the list returns None rather than raising."""
    result = api.get_first_match(sample_quotes, number=99)
    assert result is None


def test_get_first_match_hash_arg(sample_quotes):
    """hash_arg returns the quote whose hash matches."""
    target = sample_quotes[1]
    result = api.get_first_match(sample_quotes, hash_arg=target.get_hash())
    assert result == target


def test_get_first_match_hash_arg_no_match(sample_quotes):
    """hash_arg with no match returns None."""
    result = api.get_first_match(sample_quotes, hash_arg='0000000000000000')
    assert result is None


def test_get_hash_acronym_algorithm():
    """get_hash() uses the first letter of each word (lowercased) as the hash input."""
    import hashlib

    q = api.Quote('Hello World foo', 'Author', None, [])
    # words: 'Hello' -> 'h', 'World' -> 'w', 'foo' -> 'f'  =>  acronym = 'hwf'
    expected = hashlib.md5('hwf'.encode()).hexdigest()[:16]
    assert q.get_hash() == expected


def test_get_hash_ignores_non_alpha():
    """get_hash() treats non-alphabetic characters as word separators and ignores them."""
    import hashlib

    # Digits and punctuation between words are separators; leading/trailing punctuation stripped
    q = api.Quote('Hello, World! 123 foo', 'Author', None, [])
    # words: 'Hello' -> 'h', 'World' -> 'w', 'foo' -> 'f'  =>  acronym = 'hwf'
    expected = hashlib.md5('hwf'.encode()).hexdigest()[:16]
    assert q.get_hash() == expected


def test_get_hash_empty_quote():
    """get_hash() returns consistent result for a quote with no alphabetic characters."""
    import hashlib

    q = api.Quote('123', 'Author', None, [])
    # No alphabetic chars -> acronym = ''
    expected = hashlib.md5(b'').hexdigest()[:16]
    assert q.get_hash() == expected


def test_get_hash_single_pass():
    """get_hash() takes only the FIRST letter of each word, not all letters."""
    import hashlib

    q = api.Quote('The quick brown fox', 'Author', None, [])
    # Each word contributes only its first letter: 't', 'q', 'b', 'f'
    expected = hashlib.md5('tqbf'.encode()).hexdigest()[:16]
    assert q.get_hash() == expected


def test_get_first_match_excluded_tags_skips_first(sample_quotes):
    """excluded_tags skips quotes that carry the excluded tag."""
    result = api.get_first_match(sample_quotes, excluded_tags='programming')
    assert result == sample_quotes[2]


def test_get_first_match_excluded_tags_eliminates_all(sample_quotes):
    """excluded_tags that matches every quote returns None."""
    result = api.get_first_match(sample_quotes, excluded_tags='fun, serious, nature, life')
    assert result is None


def test_get_first_match_tags_and_excluded_tags(sample_quotes):
    """tags + excluded_tags: must have required tag but not excluded tag."""
    result = api.get_first_match(sample_quotes, tags='programming', excluded_tags='fun')
    assert result == sample_quotes[1]


def test_get_first_match_rand_returns_a_valid_match(sample_quotes):
    """rand=True returns one of the matching quotes, not necessarily the first."""
    result = api.get_first_match(sample_quotes, tags='fun', rand=True)
    assert result in (sample_quotes[0], sample_quotes[3])


def test_get_first_match_rand_single_match(sample_quotes):
    """rand=True with only one matching quote still returns that quote."""
    result = api.get_first_match(sample_quotes, tags='nature', rand=True)
    assert result == sample_quotes[2]


def test_get_first_match_empty_list():
    """Empty quote list returns None for any criteria."""
    assert api.get_first_match([]) is None
    assert api.get_first_match([], keyword='anything') is None


# ---------------------------------------------------------------------------
# get_config()
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# get_config() with new three-section format
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Legacy [jotquote] migration
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Missing required property
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# _migrate_legacy_section() prefix stripping
# ---------------------------------------------------------------------------


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

    api._migrate_legacy_section(config)

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
    original_fn = api.read_quotes_with_hash

    def _modified_read(filename):
        quotes, sha256 = original_fn(filename)
        with open(filename, 'a', encoding='utf-8') as f:
            f.write('Injected quote | Injected Author | | tag1\n')
        return quotes, sha256

    api.read_quotes_with_hash = _modified_read
    try:
        with pytest.raises(click.ClickException, match='modified by another process'):
            api.settags(quote_file, 1, None, ['newtag'])
    finally:
        api.read_quotes_with_hash = original_fn


def test_add_quotes_fails_on_concurrent_modification(tmp_path, config):
    """add_quotes() raises ClickException when quote file is modified externally."""
    quote_file = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.SECTION_GENERAL]['quote_file'] = str(quote_file)

    original_fn = api.read_quotes_with_hash

    def _modified_read(filename):
        quotes, sha256 = original_fn(filename)
        with open(filename, 'a', encoding='utf-8') as f:
            f.write('Injected quote | Injected Author | | tag1\n')
        return quotes, sha256

    api.read_quotes_with_hash = _modified_read
    try:
        new_quote = api.Quote('Brand new quote', 'Brand New Author', None, [])
        with pytest.raises(click.ClickException, match='modified by another process'):
            api.add_quotes(quote_file, [new_quote])
    finally:
        api.read_quotes_with_hash = original_fn
