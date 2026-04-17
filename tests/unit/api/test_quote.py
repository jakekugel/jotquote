# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import hashlib
import re

import click
import pytest

from jotquote import api
from jotquote.api import quote as quote_mod


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


def test_assert_does_not_contain_period():
    """The internal _assert_does_not_contain function should raise exception if char in text."""
    with pytest.raises(Exception, match=re.escape('the quote included a (.) character')):
        quote_mod._assert_does_not_contain('There is a period in this string.', '.', 'quote')


def test_assert_does_not_contain_newline():
    """The internal _assert_does_not_contain function should raise exception if char missing from text."""
    with pytest.raises(Exception, match=re.escape('the quote included a newline (0x0a) character')):
        quote_mod._assert_does_not_contain('There is a newline (\n) in this string.', '\n', 'quote')


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
    quote, author, publication, tags = quote_mod._parse_quote_simple(raw_quote)
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
        quote_mod._parse_quote_simple(raw_quote)


def test_get_hash_acronym_algorithm():
    """get_hash() uses the first letter of each word (lowercased) as the hash input."""
    q = api.Quote('Hello World foo', 'Author', None, [])
    # words: 'Hello' -> 'h', 'World' -> 'w', 'foo' -> 'f'  =>  acronym = 'hwf'
    expected = hashlib.md5('hwf'.encode()).hexdigest()[:16]
    assert q.get_hash() == expected


def test_get_hash_ignores_non_alpha():
    """get_hash() treats non-alphabetic characters as word separators and ignores them."""
    # Digits and punctuation between words are separators; leading/trailing punctuation stripped
    q = api.Quote('Hello, World! 123 foo', 'Author', None, [])
    # words: 'Hello' -> 'h', 'World' -> 'w', 'foo' -> 'f'  =>  acronym = 'hwf'
    expected = hashlib.md5('hwf'.encode()).hexdigest()[:16]
    assert q.get_hash() == expected


def test_get_hash_empty_quote():
    """get_hash() returns consistent result for a quote with no alphabetic characters."""
    q = api.Quote('123', 'Author', None, [])
    # No alphabetic chars -> acronym = ''
    expected = hashlib.md5(b'').hexdigest()[:16]
    assert q.get_hash() == expected


def test_get_hash_single_pass():
    """get_hash() takes only the FIRST letter of each word, not all letters."""
    q = api.Quote('The quick brown fox', 'Author', None, [])
    # Each word contributes only its first letter: 't', 'q', 'b', 'f'
    expected = hashlib.md5('tqbf'.encode()).hexdigest()[:16]
    assert q.get_hash() == expected
