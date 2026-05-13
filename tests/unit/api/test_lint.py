# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from configparser import ConfigParser

from jotquote import api
from jotquote.api.lint import (
    LintIssue,
    _check_double_spaces,
    _check_duplicate_hash,
    _check_no_author,
    _check_no_tags,
    _check_quote_length,
    _check_required_tag_groups,
    _check_smart_dashes,
    _check_smart_quotes,
    _check_unicode_ellipsis,
    apply_fixes,
    lint_quotes,
)


def _make_quote(quote='Test quote', author='Test Author', publication=None, tags=None, line_number=1):
    """Helper to create a Quote with a set line_number."""
    q = api.Quote(quote, author, publication, tags or [])
    q.line_number = line_number
    return q


def _make_config(enabled_checks='', max_quote_length='0', required_tag_groups=None):
    """Helper to create a config with the lint section populated."""
    cfg = ConfigParser()
    cfg.add_section(api.SECTION_GENERAL)
    cfg[api.SECTION_GENERAL]['quote_file'] = 'notset'
    cfg.add_section(api.SECTION_LINT)
    cfg[api.SECTION_LINT]['enabled_checks'] = enabled_checks
    cfg[api.SECTION_LINT]['max_quote_length'] = max_quote_length
    if required_tag_groups:
        for name, tags in required_tag_groups.items():
            cfg[api.SECTION_LINT]['required_group_{}'.format(name)] = tags
    return cfg


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
    assert issues[0].fix_value == "'Hello'"


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
# _check_smart_dashes
# ---------------------------------------------------------------------------


def test_check_smart_dashes_clean():
    q = _make_quote(quote='A regular - hyphen')
    assert _check_smart_dashes(q) == []


def test_check_smart_dashes_en_dash():
    q = _make_quote(quote='pages 10\u201320')
    issues = _check_smart_dashes(q)
    assert len(issues) == 1
    assert issues[0].fixable
    assert issues[0].fix_value == 'pages 10-20'


def test_check_smart_dashes_em_dash():
    q = _make_quote(quote='word\u2014word')
    issues = _check_smart_dashes(q)
    assert len(issues) == 1
    assert issues[0].fix_value == 'word-word'


def test_check_smart_dashes_in_author():
    q = _make_quote(author='Mary\u2010Jane')
    issues = _check_smart_dashes(q)
    assert len(issues) == 1
    assert issues[0].field == 'author'
    assert issues[0].fix_value == 'Mary-Jane'


def test_check_smart_dashes_multiple_fields():
    q = _make_quote(quote='a\u2013b', author='c\u2014d', publication='e\u2015f')
    issues = _check_smart_dashes(q)
    assert len(issues) == 3


def test_apply_fixes_smart_dashes():
    q = _make_quote(quote='10\u201320', line_number=1)
    issues = [
        LintIssue(line_number=1, check='smart-dashes', field='quote', message='', fixable=True, fix_value='10-20'),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    assert quotes[0].quote == '10-20'


# ---------------------------------------------------------------------------
# _check_double_spaces
# ---------------------------------------------------------------------------


def test_check_double_spaces_clean():
    q = _make_quote(quote='No double spaces here.')
    assert _check_double_spaces(q) == []


def test_check_double_spaces_in_quote():
    q = _make_quote(quote='One thing I know.  This is wisdom.')
    issues = _check_double_spaces(q)
    assert len(issues) == 1
    assert issues[0].field == 'quote'
    assert issues[0].fixable
    assert issues[0].fix_value == 'One thing I know. This is wisdom.'


def test_check_double_spaces_in_author():
    q = _make_quote(author='Jane  Doe')
    issues = _check_double_spaces(q)
    assert len(issues) == 1
    assert issues[0].field == 'author'
    assert issues[0].fix_value == 'Jane Doe'


def test_check_double_spaces_in_publication():
    q = _make_quote(publication='Some  Book')
    issues = _check_double_spaces(q)
    assert len(issues) == 1
    assert issues[0].field == 'publication'
    assert issues[0].fix_value == 'Some Book'


def test_check_double_spaces_three_spaces():
    q = _make_quote(quote='Too   many spaces')
    issues = _check_double_spaces(q)
    assert len(issues) == 1
    assert issues[0].fix_value == 'Too many spaces'


def test_apply_fixes_double_spaces():
    q = _make_quote(quote='Hello.  World.', line_number=1)
    issues = [
        LintIssue(
            line_number=1, check='double-spaces', field='quote', message='', fixable=True, fix_value='Hello. World.'
        ),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    assert quotes[0].quote == 'Hello. World.'


# ---------------------------------------------------------------------------
# _check_quote_length
# ---------------------------------------------------------------------------


def test_check_quote_length_no_limit():
    """When lint_max_quote_length is 0 (default), no issues are raised."""
    cfg = _make_config()[api.SECTION_LINT]
    q = _make_quote(quote='x' * 500)
    assert _check_quote_length(q, cfg) == []


def test_check_quote_length_within_limit():
    cfg = _make_config(max_quote_length='100')[api.SECTION_LINT]
    q = _make_quote(quote='x' * 100)
    assert _check_quote_length(q, cfg) == []


def test_check_quote_length_exceeds_limit():
    cfg = _make_config(max_quote_length='100')[api.SECTION_LINT]
    q = _make_quote(quote='x' * 101)
    issues = _check_quote_length(q, cfg)
    assert len(issues) == 1
    assert issues[0].check == 'quote-too-long'
    assert issues[0].field == 'quote'
    assert '101' in issues[0].message
    assert '100' in issues[0].message
    assert not issues[0].fixable


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
# _check_required_tag_groups
# ---------------------------------------------------------------------------


def test_required_tag_groups_not_configured():
    """When no lint_required_group_* keys exist, no issues are raised."""
    cfg = _make_config()[api.SECTION_LINT]
    q = _make_quote(tags=['funny'])
    assert _check_required_tag_groups(q, cfg) == []


def test_required_tag_groups_quote_has_required_tag():
    cfg = _make_config(required_tag_groups={'stars': '1star, 2stars, 3stars, 4stars, 5stars'})[api.SECTION_LINT]
    q = _make_quote(tags=['3stars', 'funny'])
    assert _check_required_tag_groups(q, cfg) == []


def test_required_tag_groups_missing_tag():
    cfg = _make_config(required_tag_groups={'stars': '1star, 2stars, 3stars, 4stars, 5stars'})[api.SECTION_LINT]
    q = _make_quote(tags=['funny'])
    issues = _check_required_tag_groups(q, cfg)
    assert len(issues) == 1
    assert issues[0].check == 'required-tag-group'
    assert issues[0].field == 'tags'
    assert 'stars' in issues[0].message
    assert not issues[0].fixable


def test_required_tag_groups_multiple_groups_all_satisfied():
    cfg = _make_config(
        required_tag_groups={
            'stars': '1star, 2stars, 3stars, 4stars, 5stars',
            'visibility': 'public, private',
        }
    )[api.SECTION_LINT]
    q = _make_quote(tags=['3stars', 'public', 'funny'])
    assert _check_required_tag_groups(q, cfg) == []


def test_required_tag_groups_multiple_groups_one_missing():
    cfg = _make_config(
        required_tag_groups={
            'stars': '1star, 2stars, 3stars, 4stars, 5stars',
            'visibility': 'public, private',
        }
    )[api.SECTION_LINT]
    q = _make_quote(tags=['3stars', 'funny'])
    issues = _check_required_tag_groups(q, cfg)
    assert len(issues) == 1
    assert issues[0].check == 'required-tag-group'
    assert 'visibility' in issues[0].message


# ---------------------------------------------------------------------------
# _check_duplicate_hash
# ---------------------------------------------------------------------------


def test_check_duplicate_hash_clean():
    """No issues when every quote has a unique hash."""
    quotes = [
        _make_quote(quote='Alpha bravo charlie delta.', line_number=1),
        _make_quote(quote='Echo foxtrot golf hotel.', line_number=2),
    ]
    assert _check_duplicate_hash(quotes) == []


def test_check_duplicate_hash_detects_pair():
    """Two quotes with the same hash are flagged on the second occurrence."""
    quotes = [
        _make_quote(quote='Apples bake cherries deliciously.', line_number=3),
        _make_quote(quote='Ants bother cats daily.', line_number=7),
    ]
    issues = _check_duplicate_hash(quotes)
    assert len(issues) == 1
    assert issues[0].check == 'duplicate-hash'
    assert issues[0].field == 'quote'
    assert issues[0].line_number == 7
    assert '3' in issues[0].message
    assert not issues[0].fixable


def test_check_duplicate_hash_detects_group_of_three():
    """Three quotes with the same hash produce two issues (second and third)."""
    quotes = [
        _make_quote(quote='Apples bake cherries deliciously.', line_number=1),
        _make_quote(quote='Ants bother cats daily.', line_number=5),
        _make_quote(quote='Alligators build canals daily.', line_number=9),
    ]
    issues = _check_duplicate_hash(quotes)
    assert len(issues) == 2
    assert {i.line_number for i in issues} == {5, 9}


# ---------------------------------------------------------------------------
# _check_unicode_ellipsis
# ---------------------------------------------------------------------------


def test_check_unicode_ellipsis_clean():
    q = _make_quote(quote='Three dots... not a single codepoint')
    assert _check_unicode_ellipsis(q) == []


def test_check_unicode_ellipsis_in_quote():
    q = _make_quote(quote='Wait… really?')
    issues = _check_unicode_ellipsis(q)
    assert len(issues) == 1
    assert issues[0].check == 'unicode-ellipsis'
    assert issues[0].field == 'quote'
    assert issues[0].fixable
    assert issues[0].fix_value == 'Wait... really?'


def test_check_unicode_ellipsis_in_author():
    q = _make_quote(author='Jane Doe…')
    issues = _check_unicode_ellipsis(q)
    assert len(issues) == 1
    assert issues[0].field == 'author'
    assert issues[0].fix_value == 'Jane Doe...'


def test_check_unicode_ellipsis_in_publication():
    q = _make_quote(publication='The Times…')
    issues = _check_unicode_ellipsis(q)
    assert len(issues) == 1
    assert issues[0].field == 'publication'
    assert issues[0].fix_value == 'The Times...'


def test_check_unicode_ellipsis_multiple_occurrences():
    q = _make_quote(quote='Wait… really…')
    issues = _check_unicode_ellipsis(q)
    assert len(issues) == 1
    assert issues[0].fix_value == 'Wait... really...'


# ---------------------------------------------------------------------------
# apply_fixes
# ---------------------------------------------------------------------------


def test_apply_fixes_smart_quotes():
    q = _make_quote(quote='\u201cHello\u201d', author='Jane Doe', line_number=1)
    issues = [
        LintIssue(line_number=1, check='smart-quotes', field='quote', message='', fixable=True, fix_value="'Hello'"),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    assert quotes[0].quote == "'Hello'"


def test_apply_fixes_unicode_ellipsis():
    q = _make_quote(quote='Wait… really?', author='Jane Doe', line_number=1)
    issues = [
        LintIssue(
            line_number=1,
            check='unicode-ellipsis',
            field='quote',
            message='',
            fixable=True,
            fix_value='Wait... really?',
        ),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    assert quotes[0].quote == 'Wait... really?'


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
