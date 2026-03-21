# -*- coding: utf-8 -*-
# This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os

import click
import pytest

from jotquote import api


def test_read_quotemap_valid(tmp_path):
    """Valid file with multiple entries returns correct dict."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('20260319: a1b2c3d4e5f67890\n20260320: 25382c2519fb23bd\n', encoding='utf-8')
    result = api.read_quotemap(str(f))
    assert result['20260319']['hash'] == 'a1b2c3d4e5f67890'
    assert result['20260320']['hash'] == '25382c2519fb23bd'
    assert result['20260319']['sticky'] is False
    assert result['20260320']['sticky'] is False


def test_read_quotemap_empty_file(tmp_path):
    """Empty file returns empty dict."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('', encoding='utf-8')
    result = api.read_quotemap(str(f))
    assert result == {}


def test_read_quotemap_comments_and_blanks(tmp_path):
    """Comments and blank lines are skipped."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('# A comment\n\n# Another comment\n20260319: a1b2c3d4e5f67890\n\n', encoding='utf-8')
    result = api.read_quotemap(str(f))
    assert result['20260319']['hash'] == 'a1b2c3d4e5f67890'
    assert len(result) == 1


def test_read_quotemap_missing_file(tmp_path):
    """Nonexistent path raises ClickException."""
    with pytest.raises(click.ClickException, match='not found'):
        api.read_quotemap(str(tmp_path / 'nonexistent.txt'))


def test_read_quotemap_empty_path():
    """Empty string path raises ClickException."""
    with pytest.raises(click.ClickException, match='No quotemap file was specified'):
        api.read_quotemap('')


def test_read_quotemap_invalid_date(tmp_path):
    """Line with non-digit date chars raises ClickException."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('2026031X: a1b2c3d4e5f67890\n', encoding='utf-8')
    with pytest.raises(click.ClickException, match='invalid date'):
        api.read_quotemap(str(f))


def test_read_quotemap_invalid_date_short(tmp_path):
    """Date with fewer than 8 digits raises ClickException."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('2026031: a1b2c3d4e5f67890\n', encoding='utf-8')
    with pytest.raises(click.ClickException, match='invalid date'):
        api.read_quotemap(str(f))


def test_read_quotemap_invalid_hash_length(tmp_path):
    """Hash not 16 chars raises ClickException."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('20260319: a1b2c3d4e5f6789\n', encoding='utf-8')
    with pytest.raises(click.ClickException, match='invalid hash'):
        api.read_quotemap(str(f))


def test_read_quotemap_invalid_hash_chars(tmp_path):
    """Hash with non-hex chars raises ClickException."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('20260319: a1b2c3d4e5f6789z\n', encoding='utf-8')
    with pytest.raises(click.ClickException, match='invalid hash'):
        api.read_quotemap(str(f))


def test_read_quotemap_no_colon(tmp_path):
    """Line without colon separator raises ClickException."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('20260319 a1b2c3d4e5f67890\n', encoding='utf-8')
    with pytest.raises(click.ClickException, match="missing ':'"):
        api.read_quotemap(str(f))


def test_read_quotemap_inline_comments(tmp_path):
    """Lines with inline comments after the hash are parsed correctly."""
    f = tmp_path / 'quotemap.txt'
    f.write_text(
        '20260319: a1b2c3d4e5f67890  # "The only way..." - Steve Jobs\n'
        '20260320: 25382c2519fb23bd  # Be yourself\n',
        encoding='utf-8',
    )
    result = api.read_quotemap(str(f))
    assert result['20260319']['hash'] == 'a1b2c3d4e5f67890'
    assert result['20260320']['hash'] == '25382c2519fb23bd'


def test_read_quotemap_sticky(tmp_path):
    """Lines with '# Sticky:' inline comment are flagged as sticky."""
    f = tmp_path / 'quotemap.txt'
    f.write_text(
        '20260319: a1b2c3d4e5f67890  # Sticky: some quote\n'
        '20260320: 25382c2519fb23bd  # regular comment\n',
        encoding='utf-8',
    )
    result = api.read_quotemap(str(f))
    assert result['20260319']['sticky'] is True
    assert result['20260320']['sticky'] is False


def test_read_quotemap_sticky_case_insensitive(tmp_path):
    """Sticky detection is case-insensitive and allows extra whitespace."""
    f = tmp_path / 'quotemap.txt'
    f.write_text(
        '20260319: a1b2c3d4e5f67890  #   STICKY: some quote\n'
        '20260320: 25382c2519fb23bd  #sticky: another\n',
        encoding='utf-8',
    )
    result = api.read_quotemap(str(f))
    assert result['20260319']['sticky'] is True
    assert result['20260320']['sticky'] is True


def test_read_quotemap_raw_line(tmp_path):
    """Each entry includes the raw_line from the file."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('20260319: a1b2c3d4e5f67890  # a comment\n', encoding='utf-8')
    result = api.read_quotemap(str(f))
    assert result['20260319']['raw_line'] == '20260319: a1b2c3d4e5f67890  # a comment'


def test_read_quotemap_mixed_valid_invalid(tmp_path):
    """Any invalid line causes ClickException (entire file rejected)."""
    f = tmp_path / 'quotemap.txt'
    f.write_text(
        '20260319: a1b2c3d4e5f67890\n'
        'BADDATE!: 25382c2519fb23bd\n',
        encoding='utf-8',
    )
    with pytest.raises(click.ClickException):
        api.read_quotemap(str(f))


def test_read_quotemap_invalid_calendar_date(tmp_path):
    """February 32nd is not a real date and raises ClickException."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('20260232: a1b2c3d4e5f67890\n', encoding='utf-8')
    with pytest.raises(click.ClickException, match='invalid date'):
        api.read_quotemap(str(f))


def test_read_quotemap_year_before_2000(tmp_path):
    """Dates with year before 2000 raise ClickException."""
    f = tmp_path / 'quotemap.txt'
    f.write_text('19990101: a1b2c3d4e5f67890\n', encoding='utf-8')
    with pytest.raises(click.ClickException, match='invalid date'):
        api.read_quotemap(str(f))


def test_read_quotemap_include_future_false(tmp_path, monkeypatch):
    """include_future=False omits future non-sticky entries."""
    import datetime as dt
    monkeypatch.setattr(dt, 'datetime', type('MockDT', (dt.datetime,), {
        'now': staticmethod(lambda: dt.datetime(2026, 3, 20)),
    }))
    f = tmp_path / 'quotemap.txt'
    f.write_text(
        '20260319: a1b2c3d4e5f67890\n'                     # past
        '20260320: 25382c2519fb23bd\n'                      # today
        '20260321: a1b2c3d4e5f67890  # sticky: keep\n'     # future sticky
        '20260322: 25382c2519fb23bd  # drop this\n',        # future non-sticky
        encoding='utf-8',
    )
    result = api.read_quotemap(str(f), include_future=False)
    assert '20260319' in result
    assert '20260320' in result
    assert '20260321' in result
    assert '20260322' not in result
