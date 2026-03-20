# -*- coding: utf-8 -*-
# This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import os
import re
import shutil

import click
import pytest

from jotquote import api


def _copy_quotes(tmp_path, fixture='quotes1.txt'):
    """Copy a test quote fixture into tmp_path and return the path."""
    src = os.path.join(os.path.dirname(__file__), 'testdata', fixture)
    dst = tmp_path / fixture
    shutil.copy(src, dst)
    return str(dst)


def _today():
    return datetime.datetime.now().strftime('%Y%m%d')


def _tomorrow():
    return (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y%m%d')


def test_rebuild_generates_entries(tmp_path):
    """Rebuild generates entries for ~10 years (~3652 days)."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = str(tmp_path / 'quotemap.txt')
    lines = api.rebuild_quotemap(quote_file, quotemap_file)
    # Count data lines (non-blank, non-comment)
    data_lines = [l for l in lines if l and not l.startswith('#')]
    assert len(data_lines) == 3652


def test_rebuild_preserves_past_entries(tmp_path):
    """Past entries are preserved verbatim in the output."""
    quote_file = _copy_quotes(tmp_path)
    quotes = api.read_quotes(quote_file)
    past_hash = quotes[0].get_hash()
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')
    raw_line = '{}: {}  # My special comment'.format(yesterday, past_hash)

    qm_file = tmp_path / 'quotemap.txt'
    qm_file.write_text(raw_line + '\n', encoding='utf-8')

    lines = api.rebuild_quotemap(quote_file, str(qm_file))
    assert raw_line in lines


def test_rebuild_preserves_sticky_entries(tmp_path):
    """Future sticky entries are preserved."""
    quote_file = _copy_quotes(tmp_path)
    quotes = api.read_quotes(quote_file)
    sticky_hash = quotes[0].get_hash()
    future_date = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y%m%d')

    qm_file = tmp_path / 'quotemap.txt'
    qm_file.write_text(
        '{}: {}  # Sticky: important quote\n'.format(future_date, sticky_hash),
        encoding='utf-8',
    )

    lines = api.rebuild_quotemap(quote_file, str(qm_file))
    sticky_lines = [l for l in lines if future_date in l]
    assert len(sticky_lines) == 1
    assert '# Sticky:' in sticky_lines[0]
    assert sticky_hash in sticky_lines[0]


def test_rebuild_regenerates_non_sticky_future(tmp_path):
    """Non-sticky future entries are regenerated (not preserved verbatim)."""
    quote_file = _copy_quotes(tmp_path)
    quotes = api.read_quotes(quote_file)
    future_date = _tomorrow()
    old_comment = '# old non-sticky comment'

    qm_file = tmp_path / 'quotemap.txt'
    qm_file.write_text(
        '{}: {}  {}\n'.format(future_date, quotes[0].get_hash(), old_comment),
        encoding='utf-8',
    )

    lines = api.rebuild_quotemap(quote_file, str(qm_file))
    future_lines = [l for l in lines if future_date in l]
    assert len(future_lines) == 1
    assert old_comment not in future_lines[0]


def test_rebuild_even_distribution(tmp_path):
    """No hash is used N+1 times until all are used N times."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = str(tmp_path / 'quotemap.txt')
    lines = api.rebuild_quotemap(quote_file, quotemap_file)

    # Count hash usage
    counts = {}
    for line in lines:
        if line and not line.startswith('#'):
            hash_val = line.split(':')[1].strip().split()[0]
            counts[hash_val] = counts.get(hash_val, 0) + 1

    values = list(counts.values())
    assert max(values) - min(values) <= 1


def test_rebuild_monthly_headers(tmp_path):
    """Output includes monthly comment headers."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = str(tmp_path / 'quotemap.txt')
    lines = api.rebuild_quotemap(quote_file, quotemap_file)
    headers = [l for l in lines if l.startswith('# Quotes for ')]
    # At least 12 months of headers (10 years = ~120 months)
    assert len(headers) >= 12


def test_rebuild_deterministic(tmp_path):
    """Same input produces same output."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = str(tmp_path / 'quotemap.txt')
    lines1 = api.rebuild_quotemap(quote_file, quotemap_file)
    lines2 = api.rebuild_quotemap(quote_file, quotemap_file)
    assert lines1 == lines2


def test_rebuild_nonexistent_quotemap(tmp_path):
    """Works with a nonexistent quotemap file (fresh generation)."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = str(tmp_path / 'does_not_exist.txt')
    lines = api.rebuild_quotemap(quote_file, quotemap_file)
    data_lines = [l for l in lines if l and not l.startswith('#')]
    assert len(data_lines) == 3652


def test_rebuild_unresolvable_hash(tmp_path):
    """Preserved entry with unresolvable hash raises ClickException."""
    quote_file = _copy_quotes(tmp_path)
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')

    qm_file = tmp_path / 'quotemap.txt'
    qm_file.write_text('{}: aaaaaaaaaaaaaaaa\n'.format(yesterday), encoding='utf-8')

    with pytest.raises(click.ClickException, match='does not match any quote'):
        api.rebuild_quotemap(quote_file, str(qm_file))


def test_rebuild_empty_quotefile(tmp_path):
    """Empty quote file raises ClickException."""
    quote_file = tmp_path / 'empty.txt'
    quote_file.write_text('', encoding='utf-8')
    quotemap_file = str(tmp_path / 'quotemap.txt')

    with pytest.raises(click.ClickException, match='no quotes'):
        api.rebuild_quotemap(str(quote_file), quotemap_file)


def test_rebuild_output_format(tmp_path):
    """Data lines match expected format: YYYYMMDD: <hash>  # <snippet>."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = str(tmp_path / 'quotemap.txt')
    lines = api.rebuild_quotemap(quote_file, quotemap_file)
    data_lines = [l for l in lines if l and not l.startswith('#')]
    for line in data_lines[:10]:
        assert re.match(r'^\d{8}: [0-9a-f]{16}  # .+', line), f'Bad format: {line}'
