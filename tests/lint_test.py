# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from configparser import ConfigParser

import pytest

from jotquote import api
from jotquote.lint import (
    LintIssue,
    apply_fixes,
    lint_quotes,
    _check_ascii,
    _check_smart_quotes,
    _check_no_tags,
    _check_no_author,
    _check_author_antipatterns,
    _check_multiple_stars,
    _check_no_star,
    _check_no_visibility,
)


def _make_quote(quote='Test quote', author='Test Author', publication=None, tags=None, line_number=1):
    """Helper to create a Quote with a set line_number."""
    q = api.Quote(quote, author, publication, tags or [])
    q.line_number = line_number
    return q


def _make_config(visibility_tags='', spell_ignore='', author_antipattern_regex='', enabled_checks=''):
    """Helper to create a config with the jotquote.lint section populated."""
    cfg = ConfigParser()
    cfg.add_section(api.APP_NAME)
    cfg[api.APP_NAME]['quote_file'] = 'notset'
    cfg.add_section('jotquote.lint')
    cfg['jotquote.lint']['enabled_checks'] = enabled_checks
    cfg['jotquote.lint']['visibility_tags'] = visibility_tags
    cfg['jotquote.lint']['spell_ignore'] = spell_ignore
    cfg['jotquote.lint']['author_antipattern_regex'] = author_antipattern_regex
    return cfg


# ---------------------------------------------------------------------------
# _check_ascii
# ---------------------------------------------------------------------------

def test_check_ascii_clean():
    q = _make_quote(quote='Hello world', author='Jane Doe')
    assert _check_ascii(q) == []


def test_check_ascii_in_quote():
    q = _make_quote(quote='caf\u00e9')
    issues = _check_ascii(q)
    assert len(issues) == 1
    assert issues[0].check == 'ascii'
    assert issues[0].field == 'quote'
    assert not issues[0].fixable


def test_check_ascii_in_author():
    q = _make_quote(author='Fran\u00e7ois')
    issues = _check_ascii(q)
    assert len(issues) == 1
    assert issues[0].field == 'author'


def test_check_ascii_in_publication():
    q = _make_quote(publication='Le Monde \u00e9dition')
    issues = _check_ascii(q)
    assert len(issues) == 1
    assert issues[0].field == 'publication'


# ---------------------------------------------------------------------------
# _check_smart_quotes
# ---------------------------------------------------------------------------

def test_check_smart_quotes_clean():
    q = _make_quote(quote="It's a test")
    assert _check_smart_quotes(q) == []


def test_check_smart_quotes_in_quote():
    q = _make_quote(quote='\u201cHello\u201d')
    issues = _check_smart_quotes(q)
    assert len(issues) == 1
    assert issues[0].check == 'smart-quotes'
    assert issues[0].fixable
    assert issues[0].fix_value == '"Hello"'


def test_check_smart_quotes_in_author():
    q = _make_quote(author='\u2018Author\u2019')
    issues = _check_smart_quotes(q)
    assert len(issues) == 1
    assert issues[0].field == 'author'
    assert issues[0].fix_value == "'Author'"


def test_check_smart_quotes_multiple_fields():
    q = _make_quote(quote='\u201cQuote\u201d', author='\u2018Author\u2019', publication='\u00abPub\u00bb')
    issues = _check_smart_quotes(q)
    assert len(issues) == 3


# ---------------------------------------------------------------------------
# _check_no_tags
# ---------------------------------------------------------------------------

def test_check_no_tags_has_tags():
    q = _make_quote(tags=['funny'])
    assert _check_no_tags(q) == []


def test_check_no_tags_empty():
    q = _make_quote(tags=[])
    issues = _check_no_tags(q)
    assert len(issues) == 1
    assert issues[0].check == 'no-tags'
    assert not issues[0].fixable


# ---------------------------------------------------------------------------
# _check_no_author
# ---------------------------------------------------------------------------

def test_check_no_author_has_author():
    q = _make_quote(author='Jane Doe')
    assert _check_no_author(q) == []


def test_check_no_author_empty():
    # api.Quote requires author to be parseable, so we bypass validation
    q = api.Quote('Test', 'x', None, [])
    q.author = ''
    q.line_number = 1
    issues = _check_no_author(q)
    assert len(issues) == 1
    assert issues[0].check == 'no-author'


# ---------------------------------------------------------------------------
# _check_author_antipatterns
# ---------------------------------------------------------------------------

def test_author_antipatterns_clean():
    cfg = _make_config()['jotquote.lint']
    q = _make_quote(author='Jane Doe')
    assert _check_author_antipatterns(q, cfg) == []


def test_author_antipatterns_anonymous():
    cfg = _make_config()['jotquote.lint']
    for name in ['Unknown', 'anonymous', 'ANON', 'n/a', 'None', '?']:
        q = _make_quote(author=name)
        issues = _check_author_antipatterns(q, cfg)
        assert any(i.check == 'author-antipatterns' and 'unknown/anonymous' in i.message for i in issues), name


def test_author_antipatterns_trailing_punct():
    cfg = _make_config()['jotquote.lint']
    q = _make_quote(author='Jane Doe.')
    issues = _check_author_antipatterns(q, cfg)
    trailing = [i for i in issues if 'trailing punctuation' in i.message]
    assert len(trailing) == 1
    assert trailing[0].fixable
    assert trailing[0].fix_value == 'Jane Doe'


def test_author_antipatterns_allcaps():
    cfg = _make_config()['jotquote.lint']
    q = _make_quote(author='SMITH')
    issues = _check_author_antipatterns(q, cfg)
    assert any('all-caps' in i.message for i in issues)


def test_author_antipatterns_allcaps_short_allowed():
    """Two-letter uppercase words (initials/abbreviations) should not trigger."""
    cfg = _make_config()['jotquote.lint']
    q = _make_quote(author='J.K. Rowling')
    issues = _check_author_antipatterns(q, cfg)
    assert not any('all-caps' in i.message for i in issues)


def test_author_antipatterns_custom_regex():
    cfg = _make_config(author_antipattern_regex=r'^\d')['jotquote.lint']
    q = _make_quote(author='123Author')
    issues = _check_author_antipatterns(q, cfg)
    assert any('custom pattern' in i.message for i in issues)


def test_author_antipatterns_custom_regex_no_match():
    cfg = _make_config(author_antipattern_regex=r'^\d')['jotquote.lint']
    q = _make_quote(author='Jane Doe')
    issues = _check_author_antipatterns(q, cfg)
    assert not any('custom pattern' in i.message for i in issues)


# ---------------------------------------------------------------------------
# _check_multiple_stars
# ---------------------------------------------------------------------------

def test_multiple_stars_none():
    q = _make_quote(tags=['funny'])
    assert _check_multiple_stars(q) == []


def test_multiple_stars_one():
    q = _make_quote(tags=['3stars'])
    assert _check_multiple_stars(q) == []


def test_multiple_stars_two():
    q = _make_quote(tags=['1star', '3stars'])
    issues = _check_multiple_stars(q)
    assert len(issues) == 1
    assert issues[0].check == 'multiple-stars'


# ---------------------------------------------------------------------------
# _check_no_star
# ---------------------------------------------------------------------------

def test_no_star_has_star():
    q = _make_quote(tags=['3stars'])
    assert _check_no_star(q) == []


def test_no_star_missing():
    q = _make_quote(tags=['funny'])
    issues = _check_no_star(q)
    assert len(issues) == 1
    assert issues[0].check == 'no-star'


# ---------------------------------------------------------------------------
# _check_no_visibility
# ---------------------------------------------------------------------------

def test_no_visibility_not_configured():
    """When visibility_tags is empty, check is skipped."""
    cfg = _make_config(visibility_tags='')['jotquote.lint']
    q = _make_quote(tags=['funny'])
    assert _check_no_visibility(q, cfg) == []


def test_no_visibility_has_tag():
    cfg = _make_config(visibility_tags='public, private')['jotquote.lint']
    q = _make_quote(tags=['public', 'funny'])
    assert _check_no_visibility(q, cfg) == []


def test_no_visibility_missing_tag():
    cfg = _make_config(visibility_tags='public, private')['jotquote.lint']
    q = _make_quote(tags=['funny'])
    issues = _check_no_visibility(q, cfg)
    assert len(issues) == 1
    assert issues[0].check == 'no-visibility'


# ---------------------------------------------------------------------------
# apply_fixes
# ---------------------------------------------------------------------------

def test_apply_fixes_smart_quotes():
    q = _make_quote(quote='\u201cHello\u201d', author='Jane Doe', line_number=1)
    issues = [
        LintIssue(line_number=1, check='smart-quotes', field='quote',
                  message='', fixable=True, fix_value='"Hello"'),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    assert quotes[0].quote == '"Hello"'


def test_apply_fixes_trailing_punct():
    q = _make_quote(author='Jane Doe.', line_number=2)
    issues = [
        LintIssue(line_number=2, check='author-antipatterns', field='author',
                  message='', fixable=True, fix_value='Jane Doe'),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    assert quotes[0].author == 'Jane Doe'


def test_apply_fixes_smart_quotes_then_trailing_punct():
    """Smart-quote fix applied first; trailing-punct fix operates on the result."""
    q = _make_quote(author='\u2018Author\u2019.', line_number=1)
    issues = [
        LintIssue(line_number=1, check='smart-quotes', field='author',
                  message='', fixable=True, fix_value="'Author'."),
        LintIssue(line_number=1, check='author-antipatterns', field='author',
                  message='', fixable=True, fix_value='\u2018Author\u2019'),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 2
    assert quotes[0].author == "'Author'"


def test_apply_fixes_no_fixable_issues():
    q = _make_quote(line_number=1)
    issues = [
        LintIssue(line_number=1, check='no-tags', field='tags', message='', fixable=False),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 0


# ---------------------------------------------------------------------------
# lint_quotes integration
# ---------------------------------------------------------------------------

def test_lint_quotes_select_checks():
    """Only enabled checks should run."""
    cfg = _make_config()
    q = _make_quote(tags=[])  # would trigger no-tags but not ascii
    issues = lint_quotes([q], {'no-tags'}, cfg)
    assert all(i.check == 'no-tags' for i in issues)


def test_lint_quotes_empty_checks():
    cfg = _make_config()
    q = _make_quote(tags=[])
    issues = lint_quotes([q], set(), cfg)
    assert issues == []
