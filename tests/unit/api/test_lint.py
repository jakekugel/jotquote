# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from configparser import ConfigParser

from jotquote import api
from jotquote.api.lint import (
    CHECKS,
    LintIssue,
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
    assert CHECKS['smart-quotes'].check(q) == []


def test_check_smart_quotes_in_quote():
    q = _make_quote(quote='\u201cHello\u201d')
    issues = CHECKS['smart-quotes'].check(q)
    assert len(issues) == 1
    assert issues[0].check == 'smart-quotes'
    assert issues[0].fixable
    assert issues[0].fix_value == "'Hello'"


def test_check_smart_quotes_in_author():
    q = _make_quote(author='\u2018Author\u2019')
    issues = CHECKS['smart-quotes'].check(q)
    assert len(issues) == 1
    assert issues[0].field == 'author'
    assert issues[0].fix_value == "'Author'"


def test_check_smart_quotes_multiple_fields():
    q = _make_quote(quote='\u201cQuote\u201d', author='\u2018Author\u2019', publication='\u00abPub\u00bb')
    issues = CHECKS['smart-quotes'].check(q)
    assert len(issues) == 3


# ---------------------------------------------------------------------------
# _check_smart_dashes
# ---------------------------------------------------------------------------


def test_check_smart_dashes_clean():
    q = _make_quote(quote='A regular - hyphen')
    assert CHECKS['smart-dashes'].check(q) == []


def test_check_smart_dashes_en_dash():
    q = _make_quote(quote='pages 10\u201320')
    issues = CHECKS['smart-dashes'].check(q)
    assert len(issues) == 1
    assert issues[0].fixable
    assert issues[0].fix_value == 'pages 10-20'


def test_check_smart_dashes_em_dash():
    q = _make_quote(quote='word\u2014word')
    issues = CHECKS['smart-dashes'].check(q)
    assert len(issues) == 1
    assert issues[0].fix_value == 'word-word'


def test_check_smart_dashes_in_author():
    q = _make_quote(author='Mary\u2010Jane')
    issues = CHECKS['smart-dashes'].check(q)
    assert len(issues) == 1
    assert issues[0].field == 'author'
    assert issues[0].fix_value == 'Mary-Jane'


def test_check_smart_dashes_multiple_fields():
    q = _make_quote(quote='a\u2013b', author='c\u2014d', publication='e\u2015f')
    issues = CHECKS['smart-dashes'].check(q)
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
    assert CHECKS['double-spaces'].check(q) == []


def test_check_double_spaces_in_quote():
    q = _make_quote(quote='One thing I know.  This is wisdom.')
    issues = CHECKS['double-spaces'].check(q)
    assert len(issues) == 1
    assert issues[0].field == 'quote'
    assert issues[0].fixable
    assert issues[0].fix_value == 'One thing I know. This is wisdom.'


def test_check_double_spaces_in_author():
    q = _make_quote(author='Jane  Doe')
    issues = CHECKS['double-spaces'].check(q)
    assert len(issues) == 1
    assert issues[0].field == 'author'
    assert issues[0].fix_value == 'Jane Doe'


def test_check_double_spaces_in_publication():
    q = _make_quote(publication='Some  Book')
    issues = CHECKS['double-spaces'].check(q)
    assert len(issues) == 1
    assert issues[0].field == 'publication'
    assert issues[0].fix_value == 'Some Book'


def test_check_double_spaces_three_spaces():
    q = _make_quote(quote='Too   many spaces')
    issues = CHECKS['double-spaces'].check(q)
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
    assert CHECKS['quote-too-long'].check(q, config=cfg) == []


def test_check_quote_length_within_limit():
    cfg = _make_config(max_quote_length='100')[api.SECTION_LINT]
    q = _make_quote(quote='x' * 100)
    assert CHECKS['quote-too-long'].check(q, config=cfg) == []


def test_check_quote_length_exceeds_limit():
    cfg = _make_config(max_quote_length='100')[api.SECTION_LINT]
    q = _make_quote(quote='x' * 101)
    issues = CHECKS['quote-too-long'].check(q, config=cfg)
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
    assert CHECKS['no-tags'].check(q) == []


def test_check_no_tags_empty():
    q = _make_quote(tags=[])
    issues = CHECKS['no-tags'].check(q)
    assert len(issues) == 1
    assert issues[0].check == 'no-tags'
    assert not issues[0].fixable


# ---------------------------------------------------------------------------
# _check_no_author
# ---------------------------------------------------------------------------


def test_check_no_author_has_author():
    q = _make_quote(author='Jane Doe')
    assert CHECKS['no-author'].check(q) == []


def test_check_no_author_empty():
    # api.Quote requires author to be parseable, so we bypass validation
    q = api.Quote('Test', 'x', None, [])
    q.author = ''
    q.line_number = 1
    issues = CHECKS['no-author'].check(q)
    assert len(issues) == 1
    assert issues[0].check == 'no-author'
    assert issues[0].field == 'author'
    assert issues[0].fixable
    assert issues[0].fix_value == 'Unknown'


def test_check_no_author_whitespace_only():
    q = api.Quote('Test', 'x', None, [])
    q.author = '   '
    q.line_number = 1
    issues = CHECKS['no-author'].check(q)
    assert len(issues) == 1
    assert issues[0].fixable
    assert issues[0].fix_value == 'Unknown'


# ---------------------------------------------------------------------------
# _check_missing_end_punctuation
# ---------------------------------------------------------------------------


def test_check_missing_end_punctuation_clean_period():
    q = _make_quote(quote='Hello world.')
    assert CHECKS['missing-end-punctuation'].check(q) == []


def test_check_missing_end_punctuation_clean_question():
    q = _make_quote(quote='What is this?')
    assert CHECKS['missing-end-punctuation'].check(q) == []


def test_check_missing_end_punctuation_clean_exclamation():
    q = _make_quote(quote='Look out!')
    assert CHECKS['missing-end-punctuation'].check(q) == []


def test_check_missing_end_punctuation_clean_trailing_close_quote():
    # Period before a closing quote character is still terminal punctuation.
    q = _make_quote(quote="He said, 'hello.'")
    assert CHECKS['missing-end-punctuation'].check(q) == []


def test_check_missing_end_punctuation_clean_trailing_paren():
    q = _make_quote(quote='Some statement (and an aside.)')
    assert CHECKS['missing-end-punctuation'].check(q) == []


def test_check_missing_end_punctuation_detected():
    q = _make_quote(quote='Hello world')
    issues = CHECKS['missing-end-punctuation'].check(q)
    assert len(issues) == 1
    assert issues[0].check == 'missing-end-punctuation'
    assert issues[0].field == 'quote'
    assert issues[0].fixable
    assert issues[0].fix_value == 'Hello world.'


def test_check_missing_end_punctuation_only_quote_field():
    # Missing punctuation in author/publication is NOT flagged - only quote text.
    q = _make_quote(quote='Hello world.', author='Jane Doe', publication='The Times')
    assert CHECKS['missing-end-punctuation'].check(q) == []


# ---------------------------------------------------------------------------
# _check_lowercase_start
# ---------------------------------------------------------------------------


def test_check_lowercase_start_clean_uppercase():
    q = _make_quote(quote='Hello world.')
    assert CHECKS['lowercase-start'].check(q) == []


def test_check_lowercase_start_clean_leading_quote():
    q = _make_quote(quote="'Hello,' she said.")
    assert CHECKS['lowercase-start'].check(q) == []


def test_check_lowercase_start_clean_leading_paren():
    q = _make_quote(quote='(Hello world.)')
    assert CHECKS['lowercase-start'].check(q) == []


def test_check_lowercase_start_clean_no_alpha():
    # No alphabetic characters at all - silently pass.
    q = _make_quote(quote='123 456.')
    assert CHECKS['lowercase-start'].check(q) == []


def test_check_lowercase_start_detected():
    q = _make_quote(quote='hello world.')
    issues = CHECKS['lowercase-start'].check(q)
    assert len(issues) == 1
    assert issues[0].check == 'lowercase-start'
    assert issues[0].field == 'quote'
    assert issues[0].fixable
    assert issues[0].fix_value == 'Hello world.'


def test_check_lowercase_start_ignored_with_leading_quote():
    # First character is non-alphabetic, so the check does not apply.
    q = _make_quote(quote="'hello world.'")
    assert CHECKS['lowercase-start'].check(q) == []


def test_check_lowercase_start_ignored_with_leading_paren():
    # First character is non-alphabetic, so the check does not apply.
    q = _make_quote(quote='(hello world.)')
    assert CHECKS['lowercase-start'].check(q) == []


def test_check_lowercase_start_ignored_with_leading_digit():
    # First character is non-alphabetic, so the check does not apply.
    q = _make_quote(quote='3 hello world.')
    assert CHECKS['lowercase-start'].check(q) == []


# ---------------------------------------------------------------------------
# _check_required_tag_groups
# ---------------------------------------------------------------------------


def test_required_tag_groups_not_configured():
    """When no lint_required_group_* keys exist, no issues are raised."""
    cfg = _make_config()[api.SECTION_LINT]
    q = _make_quote(tags=['funny'])
    assert CHECKS['required-tag-group'].check(q, config=cfg) == []


def test_required_tag_groups_quote_has_required_tag():
    cfg = _make_config(required_tag_groups={'stars': '1star, 2stars, 3stars, 4stars, 5stars'})[api.SECTION_LINT]
    q = _make_quote(tags=['3stars', 'funny'])
    assert CHECKS['required-tag-group'].check(q, config=cfg) == []


def test_required_tag_groups_missing_tag():
    cfg = _make_config(required_tag_groups={'stars': '1star, 2stars, 3stars, 4stars, 5stars'})[api.SECTION_LINT]
    q = _make_quote(tags=['funny'])
    issues = CHECKS['required-tag-group'].check(q, config=cfg)
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
    assert CHECKS['required-tag-group'].check(q, config=cfg) == []


def test_required_tag_groups_multiple_groups_one_missing():
    cfg = _make_config(
        required_tag_groups={
            'stars': '1star, 2stars, 3stars, 4stars, 5stars',
            'visibility': 'public, private',
        }
    )[api.SECTION_LINT]
    q = _make_quote(tags=['3stars', 'funny'])
    issues = CHECKS['required-tag-group'].check(q, config=cfg)
    assert len(issues) == 1
    assert issues[0].check == 'required-tag-group'
    assert 'public' in issues[0].message
    assert 'private' in issues[0].message


# ---------------------------------------------------------------------------
# _check_duplicate_hash
# ---------------------------------------------------------------------------


def test_check_duplicate_hash_clean():
    """No issues when every quote has a unique hash."""
    quotes = [
        _make_quote(quote='Alpha bravo charlie delta.', line_number=1),
        _make_quote(quote='Echo foxtrot golf hotel.', line_number=2),
    ]
    assert CHECKS['duplicate-hash'].check(quotes) == []


def test_check_duplicate_hash_detects_pair():
    """Two quotes with the same hash are flagged on the second occurrence."""
    quotes = [
        _make_quote(quote='Apples bake cherries deliciously.', line_number=3),
        _make_quote(quote='Ants bother cats daily.', line_number=7),
    ]
    issues = CHECKS['duplicate-hash'].check(quotes)
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
    issues = CHECKS['duplicate-hash'].check(quotes)
    assert len(issues) == 2
    assert {i.line_number for i in issues} == {5, 9}


# ---------------------------------------------------------------------------
# _check_unicode_ellipsis
# ---------------------------------------------------------------------------


def test_check_unicode_ellipsis_clean():
    q = _make_quote(quote='Three dots... not a single codepoint')
    assert CHECKS['unicode-ellipsis'].check(q) == []


def test_check_unicode_ellipsis_in_quote():
    q = _make_quote(quote='Wait… really?')
    issues = CHECKS['unicode-ellipsis'].check(q)
    assert len(issues) == 1
    assert issues[0].check == 'unicode-ellipsis'
    assert issues[0].field == 'quote'
    assert issues[0].fixable
    assert issues[0].fix_value == 'Wait... really?'


def test_check_unicode_ellipsis_in_author():
    q = _make_quote(author='Jane Doe…')
    issues = CHECKS['unicode-ellipsis'].check(q)
    assert len(issues) == 1
    assert issues[0].field == 'author'
    assert issues[0].fix_value == 'Jane Doe...'


def test_check_unicode_ellipsis_in_publication():
    q = _make_quote(publication='The Times…')
    issues = CHECKS['unicode-ellipsis'].check(q)
    assert len(issues) == 1
    assert issues[0].field == 'publication'
    assert issues[0].fix_value == 'The Times...'


def test_check_unicode_ellipsis_multiple_occurrences():
    q = _make_quote(quote='Wait… really…')
    issues = CHECKS['unicode-ellipsis'].check(q)
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


def test_apply_fixes_missing_end_punctuation():
    q = _make_quote(quote='Hello world', line_number=1)
    issues = [
        LintIssue(
            line_number=1,
            check='missing-end-punctuation',
            field='quote',
            message='',
            fixable=True,
            fix_value='Hello world.',
        ),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    assert quotes[0].quote == 'Hello world.'


def test_apply_fixes_lowercase_start():
    q = _make_quote(quote='hello world.', line_number=1)
    issues = [
        LintIssue(
            line_number=1,
            check='lowercase-start',
            field='quote',
            message='',
            fixable=True,
            fix_value='Hello world.',
        ),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    assert quotes[0].quote == 'Hello world.'


def test_apply_fixes_lowercase_and_end_punct_together():
    # A single quote with both issues should get both fixes in one pass.
    q = _make_quote(quote='hello world', line_number=1)
    issues = [
        LintIssue(
            line_number=1,
            check='lowercase-start',
            field='quote',
            message='',
            fixable=True,
            fix_value='Hello world',
        ),
        LintIssue(
            line_number=1,
            check='missing-end-punctuation',
            field='quote',
            message='',
            fixable=True,
            fix_value='hello world.',
        ),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 2
    assert quotes[0].quote == 'Hello world.'


def test_apply_fixes_no_author():
    q = api.Quote('Test quote.', 'x', None, [])
    q.author = ''
    q.line_number = 1
    issues = [
        LintIssue(
            line_number=1,
            check='no-author',
            field='author',
            message='',
            fixable=True,
            fix_value='Unknown',
        ),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    assert quotes[0].author == 'Unknown'


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


# ---------------------------------------------------------------------------
# Dispatcher behaviour (Check registry)
# ---------------------------------------------------------------------------


def test_lint_quotes_unknown_check_name_silently_ignored():
    """An unrecognized check name does not raise — it just produces no issues."""
    cfg = _make_config()
    q = _make_quote(tags=[])
    issues = lint_quotes([q], {'no-tags', 'no-such-check-exists'}, cfg)
    # Only the known check ran; the unknown one contributed nothing.
    assert all(i.check == 'no-tags' for i in issues)
    assert len(issues) == 1


def test_lint_quotes_file_scope_check_runs_once_across_all_quotes():
    """File-scope checks (duplicate-hash) see the full quote list, not one quote at a time."""
    cfg = _make_config()
    quotes = [
        _make_quote(quote='Apples bake cherries deliciously.', line_number=1),
        _make_quote(quote='Ants bother cats daily.', line_number=5),
    ]
    issues = lint_quotes(quotes, {'duplicate-hash'}, cfg)
    # Both quotes share the same fuzzy hash, so the file-scope check finds 1.
    assert len(issues) == 1
    assert issues[0].check == 'duplicate-hash'
    assert issues[0].line_number == 5


def test_apply_fixes_dispatches_to_check_fix_method():
    """A fixable issue triggers the corresponding Check.fix on the matching quote."""
    q = _make_quote(quote='“hello”', line_number=1)
    issues = lint_quotes([q], {'smart-quotes'}, _make_config())
    assert len(issues) == 1
    quotes, count = apply_fixes([q], issues)
    assert count == 1
    # The smart-quote characters in the quote field have been translated to ASCII.
    assert '“' not in quotes[0].quote
    assert '”' not in quotes[0].quote
    assert quotes[0].quote == "'hello'"


def test_apply_fixes_ignores_unknown_check_name():
    """An issue whose check is not in the registry is skipped without crashing."""
    q = _make_quote(quote='Hello.', line_number=1)
    issues = [
        LintIssue(
            line_number=1,
            check='no-such-check',
            field='quote',
            message='',
            fixable=True,
            fix_value='whatever',
        ),
    ]
    quotes, count = apply_fixes([q], issues)
    assert count == 0
    assert quotes[0].quote == 'Hello.'


def test_check_subclass_self_registers():
    """Defining a new Check subclass adds it to CHECKS automatically."""
    from jotquote.api.lint import CHECKS, Check

    class _TempProbeCheck(Check):
        name = 'temp-probe-test-only'

        def check(self, quote, *, config=None):
            return []

    try:
        assert 'temp-probe-test-only' in CHECKS
        assert isinstance(CHECKS['temp-probe-test-only'], _TempProbeCheck)
    finally:
        # Don't leak the probe into other tests via the module-global registry.
        CHECKS.pop('temp-probe-test-only', None)
