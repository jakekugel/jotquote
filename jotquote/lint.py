# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import re
from dataclasses import dataclass
from typing import Optional

ALL_CHECKS = frozenset({
    'ascii',
    'smart-quotes',
    'spelling',
    'no-tags',
    'no-author',
    'author-antipatterns',
    'multiple-stars',
    'no-star',
    'no-visibility',
})

# Smart/typographic quote characters and their ASCII replacements
_SMART_QUOTE_CHARS = '\u2018\u2019\u201c\u201d\u2039\u203a\u00ab\u00bb'
_SMART_QUOTE_MAP = str.maketrans(
    '\u2018\u2019\u201c\u201d\u2039\u203a\u00ab\u00bb',
    "''\"\"''\"\"",
)

_ANON_RE = re.compile(r'^\s*(unknown|anonymous|anon|n/a|none|\?)\s*$', re.IGNORECASE)
_TRAILING_PUNCT_RE = re.compile(r'[.,;:!?]+$')
_ALLCAPS_WORD_RE = re.compile(r'\b[A-Z]{3,}\b')

_STAR_TAGS = frozenset({'1star', '2stars', '3stars', '4stars', '5stars'})


@dataclass
class LintIssue:
    line_number: int
    check: str
    field: str
    message: str
    fixable: bool = False
    fix_value: Optional[str] = None


def lint_quotes(quotes, checks, config):
    """Run enabled checks against all quotes. Returns a list of LintIssue."""
    lint_cfg = config['jotquote.lint']
    issues = []
    for quote in quotes:
        if 'ascii' in checks:
            issues.extend(_check_ascii(quote))
        if 'smart-quotes' in checks:
            issues.extend(_check_smart_quotes(quote))
        if 'spelling' in checks:
            issues.extend(_check_spelling(quote, lint_cfg))
        if 'no-tags' in checks:
            issues.extend(_check_no_tags(quote))
        if 'no-author' in checks:
            issues.extend(_check_no_author(quote))
        if 'author-antipatterns' in checks:
            issues.extend(_check_author_antipatterns(quote, lint_cfg))
        if 'multiple-stars' in checks:
            issues.extend(_check_multiple_stars(quote))
        if 'no-star' in checks:
            issues.extend(_check_no_star(quote))
        if 'no-visibility' in checks:
            issues.extend(_check_no_visibility(quote, lint_cfg))
    return issues


def apply_fixes(quotes, issues):
    """Apply all fixable issues to the quote list.

    Returns (fixed_quotes, fix_count). Mutates quote objects in place.
    Smart-quote fixes are applied before trailing-punctuation fixes so that
    a quote with both issues on the same field is handled correctly.
    """
    fixes_by_line = {}
    for issue in issues:
        if issue.fixable:
            fixes_by_line.setdefault(issue.line_number, []).append(issue)

    fix_count = 0
    for quote in quotes:
        line_fixes = fixes_by_line.get(quote.line_number, [])
        if not line_fixes:
            continue

        # Smart-quotes: apply transformation to current field value
        for field_name in ('quote', 'author', 'publication'):
            sq = [i for i in line_fixes if i.check == 'smart-quotes' and i.field == field_name]
            if sq:
                current = getattr(quote, field_name) or ''
                setattr(quote, field_name, current.translate(_SMART_QUOTE_MAP))
                fix_count += 1

        # Author trailing punctuation: re-read field after smart-quote fix
        for issue in line_fixes:
            if issue.check == 'author-antipatterns' and issue.field == 'author':
                quote.author = _TRAILING_PUNCT_RE.sub('', quote.author).rstrip()
                fix_count += 1

    return quotes, fix_count


# ---------------------------------------------------------------------------
# Private check helpers
# ---------------------------------------------------------------------------

def _check_ascii(quote):
    issues = []
    for field_name, value in [('quote', quote.quote), ('author', quote.author), ('publication', quote.publication)]:
        if value is None:
            continue
        if any(ord(c) > 127 for c in value):
            issues.append(LintIssue(
                line_number=quote.line_number,
                check='ascii',
                field=field_name,
                message='Non-ASCII characters in {}: {!r}'.format(field_name, value),
            ))
    return issues


def _check_smart_quotes(quote):
    issues = []
    for field_name, value in [('quote', quote.quote), ('author', quote.author), ('publication', quote.publication)]:
        if value is None:
            continue
        if any(c in _SMART_QUOTE_CHARS for c in value):
            fixed = value.translate(_SMART_QUOTE_MAP)
            issues.append(LintIssue(
                line_number=quote.line_number,
                check='smart-quotes',
                field=field_name,
                message='Smart quotes in {}: {!r}'.format(field_name, value),
                fixable=True,
                fix_value=fixed,
            ))
    return issues


def _check_spelling(quote, lint_cfg):
    try:
        from spellchecker import SpellChecker
    except ImportError:
        return []

    ignore_raw = lint_cfg.get('spell_ignore', '')
    ignore_words = {w.strip().lower() for w in ignore_raw.split(',') if w.strip()}

    spell = SpellChecker()
    if ignore_words:
        spell.word_frequency.load_words(ignore_words)

    words = re.findall(r"[a-zA-Z']+", quote.quote)
    misspelled = spell.unknown(words) - ignore_words

    issues = []
    for word in sorted(misspelled):
        issues.append(LintIssue(
            line_number=quote.line_number,
            check='spelling',
            field='quote',
            message="Possible misspelling: '{}'".format(word),
        ))
    return issues


def _check_no_tags(quote):
    if not quote.tags:
        return [LintIssue(
            line_number=quote.line_number,
            check='no-tags',
            field='tags',
            message='Quote has no tags',
        )]
    return []


def _check_no_author(quote):
    if not quote.author or not quote.author.strip():
        return [LintIssue(
            line_number=quote.line_number,
            check='no-author',
            field='author',
            message='No author specified',
        )]
    return []


def _check_author_antipatterns(quote, lint_cfg):
    issues = []
    author = quote.author

    if _ANON_RE.match(author):
        issues.append(LintIssue(
            line_number=quote.line_number,
            check='author-antipatterns',
            field='author',
            message='Author matches unknown/anonymous pattern: {!r}'.format(author),
        ))

    if _TRAILING_PUNCT_RE.search(author):
        fixed = _TRAILING_PUNCT_RE.sub('', author).rstrip()
        issues.append(LintIssue(
            line_number=quote.line_number,
            check='author-antipatterns',
            field='author',
            message='Author has trailing punctuation: {!r}'.format(author),
            fixable=True,
            fix_value=fixed,
        ))

    allcaps = _ALLCAPS_WORD_RE.findall(author)
    if allcaps:
        issues.append(LintIssue(
            line_number=quote.line_number,
            check='author-antipatterns',
            field='author',
            message='Author contains all-caps word(s): {}'.format(', '.join(allcaps)),
        ))

    raw_patterns = lint_cfg.get('author_antipattern_regex', '')
    if raw_patterns.strip():
        for pattern in raw_patterns.split(','):
            pattern = pattern.strip()
            if pattern and re.search(pattern, author):
                issues.append(LintIssue(
                    line_number=quote.line_number,
                    check='author-antipatterns',
                    field='author',
                    message='Author matches custom pattern {!r}: {!r}'.format(pattern, author),
                ))

    return issues


def _check_multiple_stars(quote):
    star_count = sum(1 for tag in quote.tags if tag in _STAR_TAGS)
    if star_count > 1:
        return [LintIssue(
            line_number=quote.line_number,
            check='multiple-stars',
            field='tags',
            message='Quote has {} star tags (only one allowed)'.format(star_count),
        )]
    return []


def _check_no_star(quote):
    if not any(tag in _STAR_TAGS for tag in quote.tags):
        return [LintIssue(
            line_number=quote.line_number,
            check='no-star',
            field='tags',
            message='Quote has no star tag',
        )]
    return []


def _check_no_visibility(quote, lint_cfg):
    raw_tags = lint_cfg.get('visibility_tags', '')
    visibility_tags = {t.strip() for t in raw_tags.split(',') if t.strip()}
    if not visibility_tags:
        return []
    if not any(tag in visibility_tags for tag in quote.tags):
        return [LintIssue(
            line_number=quote.line_number,
            check='no-visibility',
            field='tags',
            message='Quote has no visibility tag (expected one of: {})'.format(
                ', '.join(sorted(visibility_tags))
            ),
        )]
    return []
