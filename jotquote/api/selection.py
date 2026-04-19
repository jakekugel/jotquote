# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import random as randomlib

from jotquote.api.quote import parse_tags


def get_first_match(quotes, tags=None, keyword=None, number=None, hash_arg=None, rand=False, excluded_tags=None):
    """Return the first :class:`Quote` from ``quotes`` matching all criteria.

    Args:
        quotes (list[Quote]): Quotes to filter.
        tags (str | None): Comma-separated tag string; the quote must have
            every listed tag.  ``None`` disables the tag filter.
        keyword (str | None): Substring match against quote text, author, and
            publication.  ``None`` disables the keyword filter.
        number (int | None): 1-based position in ``quotes``.  ``None`` disables
            positional filtering.
        hash_arg (str | None): 16-character MD5 hash prefix of the quote text.
            ``None`` disables hash filtering.
        rand (bool): If ``True``, return a random match rather than the first.
        excluded_tags (str | None): Comma-separated tag string; the quote must
            not contain any of these tags.  ``None`` disables the exclusion
            filter.

    Returns:
        Quote | None: The selected quote, or ``None`` if no quote matches.
    """
    taglist = parse_tags(tags) if tags is not None else []
    excluded_taglist = parse_tags(excluded_tags) if excluded_tags is not None else []

    matched = [
        quote
        for index, quote in enumerate(quotes)
        if (keyword is None or quote.has_keyword(keyword))
        and (tags is None or quote.has_tags(taglist))
        and (number is None or number == index + 1)
        and (hash_arg is None or hash_arg == quote.get_hash())
        and not any(t in quote.tags for t in excluded_taglist)
    ]

    if not matched:
        return None
    if rand:
        return randomlib.choice(matched)
    return matched[0]


def get_random_choice(numquotes):
    """Return a deterministic quote index for today's date.

    The same value is returned for any call on the same day; after 11:45 PM
    local time, the value advances to the next day so caches expiring at
    midnight already contain the next day's quote.

    Args:
        numquotes (int): Total number of quotes.

    Returns:
        int: A value in ``[0, numquotes - 1]``.
    """

    # Get days since epoch, advancing to next day after 11:45 PM so caches
    # expiring at midnight will already contain the next day's quote
    now = datetime.datetime.now()
    if now.hour == 23 and now.minute >= 45:
        endday = (now + datetime.timedelta(days=1)).date()
    else:
        endday = now.date()
    beginday = datetime.date(2016, 1, 1)
    days_since_epoch = (endday - beginday).days

    # Get quote index
    index = _get_random_value(days_since_epoch, numquotes)
    return index


def _get_random_value(days_since_epoch, numquotes):
    """This function returns a random value between 0 and numquotes - 1.  For a given
    days_since_epoch and numquotes, it will always return the same value.
    """
    numlist = list(range(0, numquotes))
    randomlib.seed(0)
    randomlib.shuffle(numlist)
    index = days_since_epoch % numquotes
    return numlist[index]
