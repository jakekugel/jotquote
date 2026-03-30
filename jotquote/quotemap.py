# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import os
import random as randomlib
import re

import click

from jotquote.api import _get_newline, read_quotes


def read_quotemap(filename, include_future=True):
    """Given a path to a quotemap file, this function returns a dict mapping
    date strings (YYYYMMDD) to 16-character quote hashes.

    Each non-blank, non-comment line must have the format:
        YYYYMMDD: <16-char-hex-hash>  # optional comment

    If include_future is True (default), all entries are returned. If False,
    future entries that are not sticky are omitted.

    Returns a dict where each key is a date string (YYYYMMDD) and each value
    is a dict with keys:
        - 'hash': the 16-char hex hash (str)
        - 'sticky': whether the inline comment contains '# Sticky:' (bool)
        - 'raw_line': the original line from the file, stripped (str)

    Raises click.ClickException if the file does not exist or any line
    fails validation.
    """
    if not filename:
        raise click.ClickException('No quotemap file was specified.')

    if not os.path.exists(filename):
        raise click.ClickException("The quotemap file '{0}' was not found.".format(filename))

    quotemap = {}
    with open(filename, mode='r', encoding='utf-8') as infile:
        for lineno, raw_line in enumerate(infile, start=1):
            line = raw_line.strip()

            # Skip blank lines and full-line comments
            if not line or line.startswith('#'):
                continue

            # Strip inline comment at the first '#' and detect sticky marker
            data_line = line
            sticky = False
            if '#' in data_line:
                comment_pos = data_line.index('#')
                comment_text = data_line[comment_pos + 1 :]
                sticky = bool(re.match(r'\s*sticky\b', comment_text, re.IGNORECASE))
                data_line = data_line[:comment_pos].strip()

            # Must contain a colon separator
            if ':' not in data_line:
                raise click.ClickException(
                    "quotemap line {0}: missing ':' separator in '{1}'".format(lineno, data_line)
                )

            date_part, hash_part = data_line.split(':', 1)
            date_part = date_part.strip()
            hash_part = hash_part.strip()

            # Validate date: exactly 8 digits and a real calendar date
            if len(date_part) != 8 or not date_part.isdigit():
                raise click.ClickException("quotemap line {0}: invalid date '{1}'".format(lineno, date_part))
            try:
                parsed_date = datetime.datetime.strptime(date_part, '%Y%m%d')
                if parsed_date.year < 2000:
                    raise ValueError('year before 2000')
            except ValueError:
                raise click.ClickException("quotemap line {0}: invalid date '{1}'".format(lineno, date_part))

            # Validate hash: exactly 16 lowercase hex characters
            if len(hash_part) != 16 or not re.fullmatch(r'[0-9a-f]{16}', hash_part):
                raise click.ClickException("quotemap line {0}: invalid hash '{1}'".format(lineno, hash_part))

            # Check for duplicate date
            if date_part in quotemap:
                raise click.ClickException("quotemap line {0}: duplicate date '{1}'".format(lineno, date_part))

            quotemap[date_part] = {
                'hash': hash_part,
                'sticky': sticky,
                'raw_line': line,
            }

    # If include_future is False, drop future non-sticky entries
    if not include_future:
        today_str = datetime.datetime.now().strftime('%Y%m%d')
        quotemap = {d: e for d, e in quotemap.items() if d <= today_str or e['sticky']}

    return quotemap


def rebuild_quotemap(quotefile, quotemapfile, newquotemapfile, days=3652):
    """Rebuild a quotemap file, generating entries for the given number of future days.

    Args:
        quotefile (str): Path to the quote file.
        quotemapfile (str): Path to the existing quotemap file to read from, may be None.
        newquotemapfile (str): Path to write the rebuilt quotemap, filename must be provided but not file may exist with that name.
        days (int): Number of future days to generate entries for (default: 3652).
    """
    quotes = read_quotes(quotefile)
    if not quotes:
        raise click.ClickException('the quote file contains no quotes.')

    if quotemapfile:
        quotemap = read_quotemap(quotemapfile)
        isprior = True
    else:
        quotemap = {}
        isprior = False

    # Build hash_to_quote and hash_to_count lookups
    hash_to_quote = {q.get_hash(): q for q in quotes}
    hash_to_count = {q.get_hash(): 0 for q in quotes}
    for entry in quotemap.values():
        if entry['hash'] in hash_to_count:
            hash_to_count[entry['hash']] += 1
        else:
            raise click.ClickException(
                "the existing quotemap contains hash '{}' which does not match any quote in the quote file.".format(
                    entry['hash']
                )
            )

    # Fill in missing future dates
    randomlib.seed(0)
    today = datetime.date.today()
    for day_offset in range(days + 1):
        # Generate date string in format YYYYMMDD
        date_str = (today + datetime.timedelta(days=day_offset)).strftime('%Y%m%d')
        if date_str in quotemap:
            continue

        # Choose random quote hash using even distribution.
        selected_hash = _select_quote(hash_to_count)

        # If rebuilding an existing quotemap, make sticky if this is first use of the quote
        sticky = isprior and hash_to_count[selected_hash] == 0
        hash_to_count[selected_hash] += 1
        quote = hash_to_quote[selected_hash]

        # Insert the quote into the quotemap dictionary
        raw_line = _format_quotemap_line(date_str, selected_hash, quote, sticky)
        quotemap[date_str] = {'hash': selected_hash, 'sticky': sticky, 'raw_line': raw_line}

    write_quotemap(newquotemapfile, quotemap)


def write_quotemap(filename, quotemap):
    """Write quotemap dict to filename, sorted by date.

    Args:
        filename (str): Output file path. Must not already exist.
        quotemap (dict): Maps date string (YYYYMMDD) to entry dict with keys 'hash' and 'raw_line'.

    Raises click.ClickException if filename already exists.
    """
    if os.path.exists(filename):
        raise click.ClickException("the quotemap file '{}' already exists.".format(filename))
    newline = _get_newline()
    with open(filename, mode='wb') as f:
        for date_str in sorted(quotemap.keys()):
            f.write((quotemap[date_str]['raw_line'] + newline).encode('utf-8'))


def _select_quote(hash_to_count):
    """Select a quote hash using even distribution.

    Picks a random hash from those with the minimum usage count,
    ensuring no hash is used N+1 times before all hashes are used N times.

    Args:
        hash_to_count (dict): Maps quote hash (str) to usage count (int).

    Returns:
        str: Selected quote hash.
    """
    min_count = min(hash_to_count.values())
    candidates = [h for h, count in hash_to_count.items() if count == min_count]
    return randomlib.choice(candidates)


def _format_quotemap_line(date_str, hash_val, quote, sticky):
    """Format a single quotemap line for output.

    Args:
        date_str (str): Date in YYYYMMDD format.
        hash_val (str): 16-char quote hash.
        quote (Quote): The Quote object for the snippet.
        sticky (bool): Whether to mark this entry as Sticky.

    Returns:
        str: Formatted line, e.g. '20260321: abc123...  # Snippet - Author'
    """
    snippet = quote.quote[:60]
    if len(quote.quote) > 60:
        snippet += '...'
    snippet = '{} - {}'.format(snippet, quote.author)
    if sticky:
        return '{}: {}  # Sticky: {}'.format(date_str, hash_val, snippet)
    return '{}: {}  # {}'.format(date_str, hash_val, snippet)
