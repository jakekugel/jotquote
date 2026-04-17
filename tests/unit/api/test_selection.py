# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime as real_datetime

import pytest

from jotquote import api
from jotquote.api import selection as selection_mod


@pytest.mark.parametrize(
    'days, numvalues, expected',
    [
        (5, 10, 4),
        (3, 15, 5),
        (199, 100, 49),
    ],
)
def test_get_random_value(days, numvalues, expected):
    assert selection_mod._get_random_value(days, numvalues) == expected


def test_get_random_value_sequence():
    items = [selection_mod._get_random_value(i, 8) for i in range(12)]
    assert items == [4, 1, 5, 2, 0, 3, 7, 6, 4, 1, 5, 2]


def test_get_random_choice_uses_today_before_cutoff(monkeypatch):
    """Before 11:45 PM, today's date drives quote selection."""

    class FakeDatetime(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 3, 14, 23, 44, 0)

    monkeypatch.setattr('jotquote.api.selection.datetime.datetime', FakeDatetime)
    result = api.get_random_choice(100)
    beginday = real_datetime.date(2016, 1, 1)
    days = (real_datetime.date(2026, 3, 14) - beginday).days
    assert result == selection_mod._get_random_value(days, 100)


def test_get_random_choice_uses_tomorrow_at_cutoff(monkeypatch):
    """At 11:45 PM exactly, tomorrow's date drives quote selection."""

    class FakeDatetime(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.datetime(2026, 3, 14, 23, 45, 0)

    monkeypatch.setattr('jotquote.api.selection.datetime.datetime', FakeDatetime)
    result = api.get_random_choice(100)
    beginday = real_datetime.date(2016, 1, 1)
    days = (real_datetime.date(2026, 3, 15) - beginday).days
    assert result == selection_mod._get_random_value(days, 100)


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
