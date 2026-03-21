# -*- coding: utf-8 -*-
# This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import os
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


def _empty_quotemap(tmp_path):
    """Create an empty quotemap file and return its path."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('', encoding='utf-8')
    return str(f)


def _new_quotemap_path(tmp_path):
    """Return a path for a new (non-existent) quotemap output file."""
    return str(tmp_path / 'new_quotemap.txt')


def _read_data_lines(path):
    """Read output quotemap file and return non-blank, non-comment lines."""
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
    return [line for line in lines if line and not line.startswith('#')]


def _tomorrow():
    return (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y%m%d')


def test_rebuild_generates_entries(tmp_path):
    """Rebuild generates entries for the given number of days."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = _empty_quotemap(tmp_path)
    new_file = _new_quotemap_path(tmp_path)
    api.rebuild_quotemap(quote_file, quotemap_file, new_file, days=10)
    data_lines = _read_data_lines(new_file)
    assert len(data_lines) == 11  # days=10 generates today + 10 future days


def test_rebuild_skips_existing_dates(tmp_path):
    """Rebuild skips dates that already exist in the quotemap."""
    quote_file = _copy_quotes(tmp_path)
    quotes = api.read_quotes(quote_file)
    existing_hash = quotes[0].get_hash()
    tomorrow = _tomorrow()
    qm_file = tmp_path / 'quotemap.txt'
    qm_file.write_text('{}: {}  # existing\n'.format(tomorrow, existing_hash), encoding='utf-8')
    new_file = _new_quotemap_path(tmp_path)
    api.rebuild_quotemap(quote_file, str(qm_file), new_file, days=5)
    data_lines = _read_data_lines(new_file)
    # The existing entry is preserved, plus 4 new ones (days=5, one already exists)
    tomorrow_lines = [line for line in data_lines if line.startswith(tomorrow)]
    assert len(tomorrow_lines) == 1
    assert existing_hash in tomorrow_lines[0]


def test_rebuild_sticky_on_first_use(tmp_path):
    """A hash used for the first time gets a Sticky marker."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = _empty_quotemap(tmp_path)
    new_file = _new_quotemap_path(tmp_path)
    api.rebuild_quotemap(quote_file, quotemap_file, new_file, days=100)
    data_lines = _read_data_lines(new_file)
    quotes = api.read_quotes(quote_file)
    # Every hash should appear exactly once with Sticky
    for q in quotes:
        h = q.get_hash()
        sticky_lines = [line for line in data_lines if h in line and '# Sticky:' in line]
        assert len(sticky_lines) == 1, 'Expected exactly 1 Sticky line for hash {}'.format(h)


def test_rebuild_even_distribution(tmp_path):
    """No hash is used N+1 times until all are used N times."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = _empty_quotemap(tmp_path)
    new_file = _new_quotemap_path(tmp_path)
    api.rebuild_quotemap(quote_file, quotemap_file, new_file, days=3652)
    data_lines = _read_data_lines(new_file)
    counts = {}
    for line in data_lines:
        hash_val = line.split(':')[1].strip().split()[0]
        counts[hash_val] = counts.get(hash_val, 0) + 1
    values = list(counts.values())
    assert max(values) - min(values) <= 1


def test_rebuild_deterministic(tmp_path):
    """Same input produces same output."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = _empty_quotemap(tmp_path)
    new_file1 = str(tmp_path / 'out1.txt')
    new_file2 = str(tmp_path / 'out2.txt')
    api.rebuild_quotemap(quote_file, quotemap_file, new_file1, days=50)
    api.rebuild_quotemap(quote_file, quotemap_file, new_file2, days=50)
    with open(new_file1, encoding='utf-8') as f:
        content1 = f.read()
    with open(new_file2, encoding='utf-8') as f:
        content2 = f.read()
    assert content1 == content2


def test_rebuild_output_format(tmp_path):
    """Data lines match expected format: YYYYMMDD: <hash>  # <snippet>."""
    import re
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = _empty_quotemap(tmp_path)
    new_file = _new_quotemap_path(tmp_path)
    api.rebuild_quotemap(quote_file, quotemap_file, new_file, days=10)
    data_lines = _read_data_lines(new_file)
    for line in data_lines:
        assert re.match(r'^\d{8}: [0-9a-f]{16}  # .+', line), 'Bad format: {}'.format(line)


def test_rebuild_quotemapfile_none(tmp_path):
    """quotemapfile=None is treated as no prior quotemap and generates entries."""
    quote_file = _copy_quotes(tmp_path)
    new_file = _new_quotemap_path(tmp_path)
    api.rebuild_quotemap(quote_file, None, new_file, days=5)
    data_lines = _read_data_lines(new_file)
    assert len(data_lines) == 6  # today + 5 future days


def test_rebuild_nonexistent_quotemapfile_raises(tmp_path):
    """A non-existent quotemapfile path raises ClickException."""
    quote_file = _copy_quotes(tmp_path)
    quotemap_file = str(tmp_path / 'does_not_exist.txt')
    new_file = _new_quotemap_path(tmp_path)
    with pytest.raises(click.ClickException, match='was not found'):
        api.rebuild_quotemap(quote_file, quotemap_file, new_file, days=5)


def test_rebuild_no_sticky_when_no_prior(tmp_path):
    """No Sticky markers are added when quotemapfile is None (isprior=False)."""
    quote_file = _copy_quotes(tmp_path)
    new_file = _new_quotemap_path(tmp_path)
    api.rebuild_quotemap(quote_file, None, new_file, days=20)
    data_lines = _read_data_lines(new_file)
    assert not any('# Sticky:' in line for line in data_lines)


def test_rebuild_unresolvable_hash(tmp_path):
    """Quotemap entry with a hash not in the quote file raises ClickException."""
    quote_file = _copy_quotes(tmp_path)
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d')
    qm_file = tmp_path / 'quotemap.txt'
    qm_file.write_text('{}: aaaaaaaaaaaaaaaa\n'.format(yesterday), encoding='utf-8')
    new_file = _new_quotemap_path(tmp_path)
    with pytest.raises(click.ClickException, match='does not match any quote'):
        api.rebuild_quotemap(quote_file, str(qm_file), new_file)


def test_rebuild_empty_quotefile(tmp_path):
    """Empty quote file raises ClickException."""
    quote_file = tmp_path / 'empty.txt'
    quote_file.write_text('', encoding='utf-8')
    quotemap_file = _empty_quotemap(tmp_path)
    new_file = _new_quotemap_path(tmp_path)
    with pytest.raises(click.ClickException, match='no quotes'):
        api.rebuild_quotemap(str(quote_file), quotemap_file, new_file)


def test_write_quotemap_raises_if_exists(tmp_path):
    """write_quotemap raises ClickException if the output file already exists."""
    existing = tmp_path / 'existing.txt'
    existing.write_text('', encoding='utf-8')
    with pytest.raises(click.ClickException, match='already exists'):
        api.write_quotemap(str(existing), {})


def test_write_quotemap_empty(config, tmp_path):
    """write_quotemap with an empty quotemap writes an empty file."""
    out = tmp_path / 'out.txt'
    api.write_quotemap(str(out), {})
    assert out.read_bytes() == b''


def test_write_quotemap_writes_raw_lines(config, tmp_path):
    """write_quotemap writes each entry's raw_line verbatim."""
    quotemap = {
        '20260321': {'hash': 'aaaaaaaaaaaaaaaa', 'raw_line': '20260321: aaaaaaaaaaaaaaaa  # First'},
        '20260322': {'hash': 'bbbbbbbbbbbbbbbb', 'raw_line': '20260322: bbbbbbbbbbbbbbbb  # Second'},
    }
    out = tmp_path / 'out.txt'
    api.write_quotemap(str(out), quotemap)
    content = out.read_text(encoding='utf-8')
    assert '20260321: aaaaaaaaaaaaaaaa  # First' in content
    assert '20260322: bbbbbbbbbbbbbbbb  # Second' in content


def test_write_quotemap_sorted_by_date(config, tmp_path):
    """write_quotemap outputs entries sorted by date regardless of insertion order."""
    quotemap = {
        '20260325': {'hash': 'cccccccccccccccc', 'raw_line': '20260325: cccccccccccccccc'},
        '20260321': {'hash': 'aaaaaaaaaaaaaaaa', 'raw_line': '20260321: aaaaaaaaaaaaaaaa'},
        '20260323': {'hash': 'bbbbbbbbbbbbbbbb', 'raw_line': '20260323: bbbbbbbbbbbbbbbb'},
    }
    out = tmp_path / 'out.txt'
    api.write_quotemap(str(out), quotemap)
    lines = [l for l in out.read_text(encoding='utf-8').splitlines() if l]
    assert lines[0].startswith('20260321')
    assert lines[1].startswith('20260323')
    assert lines[2].startswith('20260325')


def test_write_quotemap_unix_line_separator(config, tmp_path):
    """write_quotemap uses \\n when line_separator = unix."""
    config[api.APP_NAME]['line_separator'] = 'unix'
    quotemap = {
        '20260321': {'hash': 'aaaaaaaaaaaaaaaa', 'raw_line': '20260321: aaaaaaaaaaaaaaaa'},
        '20260322': {'hash': 'bbbbbbbbbbbbbbbb', 'raw_line': '20260322: bbbbbbbbbbbbbbbb'},
    }
    out = tmp_path / 'out.txt'
    api.write_quotemap(str(out), quotemap)
    assert b'\r\n' not in out.read_bytes()
    assert out.read_bytes().count(b'\n') == 2


def test_write_quotemap_windows_line_separator(config, tmp_path):
    """write_quotemap uses \\r\\n when line_separator = windows."""
    config[api.APP_NAME]['line_separator'] = 'windows'
    quotemap = {
        '20260321': {'hash': 'aaaaaaaaaaaaaaaa', 'raw_line': '20260321: aaaaaaaaaaaaaaaa'},
        '20260322': {'hash': 'bbbbbbbbbbbbbbbb', 'raw_line': '20260322: bbbbbbbbbbbbbbbb'},
    }
    out = tmp_path / 'out.txt'
    api.write_quotemap(str(out), quotemap)
    assert out.read_bytes().count(b'\r\n') == 2


def test_write_quotemap_invalid_line_separator(config, tmp_path):
    """write_quotemap raises ClickException for an invalid line_separator value."""
    config[api.APP_NAME]['line_separator'] = 'VAX-VMS'
    quotemap = {'20260321': {'hash': 'aaaaaaaaaaaaaaaa', 'raw_line': '20260321: aaaaaaaaaaaaaaaa'}}
    out = tmp_path / 'out.txt'
    with pytest.raises(click.ClickException, match='not valid value for the line_separator property'):
        api.write_quotemap(str(out), quotemap)
