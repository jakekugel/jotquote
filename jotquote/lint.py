# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import re
from dataclasses import dataclass
from typing import Optional

ALL_CHECKS = frozenset({
    'ascii',             # Flag non-ASCII characters in quote, author, or publication
    'smart-quotes',      # Flag (and fix) typographic/smart quote characters
    'smart-dashes',      # Flag (and fix) unicode dash/hyphen variants
    'spelling',          # Flag possible misspellings in the quote text (requires pyspellchecker)
    'double-spaces',     # Flag (and fix) runs of multiple spaces in any field
    'quote-too-long',    # Flag quotes exceeding a configurable max length (lint_max_quote_length)
    'no-tags',           # Flag quotes with no tags
    'no-author',         # Flag quotes with no author
    'author-antipatterns',  # Flag author fields matching known bad patterns (anonymous, all-caps, source-type words)
    'multiple-stars',    # Flag quotes with more than one star-rating tag
    'required-tag-group',  # Flag quotes missing a tag from any user-defined required tag group
})

# Smart/typographic quote characters and their ASCII replacements
_SMART_QUOTE_CHARS = '\u2018\u2019\u201c\u201d\u2039\u203a\u00ab\u00bb'
_SMART_QUOTE_MAP = str.maketrans(
    '\u2018\u2019\u201c\u201d\u2039\u203a\u00ab\u00bb',
    "''\"\"''\"\"",
)

# Unicode dash/hyphen characters and their ASCII hyphen replacement
_SMART_DASH_NAMES = {
    '\u2010': 'hyphen',
    '\u2011': 'non-breaking hyphen',
    '\u2012': 'figure dash',
    '\u2013': 'en dash',
    '\u2014': 'em dash',
    '\u2015': 'horizontal bar',
    '\u2212': 'minus sign',
    '\ufe58': 'small em dash',
    '\ufe63': 'small hyphen-minus',
    '\uff0d': 'fullwidth hyphen-minus',
}
_SMART_DASH_CHARS = ''.join(_SMART_DASH_NAMES)
_SMART_DASH_MAP = str.maketrans(_SMART_DASH_CHARS, '-' * len(_SMART_DASH_CHARS))

_STAR_TAGS = frozenset({'1star', '2stars', '3stars', '4stars', '5stars'})

_ANON_RE = re.compile(r'^\s*(unknown|anonymous|anon|n/a|none|\?)\s*$', re.IGNORECASE)
_ALLCAPS_WORD_RE = re.compile(r'\b[A-Z]{3,}\b')

# Words always ignored by the spell checker regardless of user configuration.
_SPELL_IGNORE_BUILTIN = frozenset({"uncared", "might've"})


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
    lint_cfg = config['jotquote']
    spell, ignore_words = _make_spellchecker(lint_cfg) if 'spelling' in checks else (None, None)
    issues = []
    for quote in quotes:
        if 'ascii' in checks:
            issues.extend(_check_ascii(quote))
        if 'smart-quotes' in checks:
            issues.extend(_check_smart_quotes(quote))
        if 'smart-dashes' in checks:
            issues.extend(_check_smart_dashes(quote))
        if 'double-spaces' in checks:
            issues.extend(_check_double_spaces(quote))
        if 'quote-too-long' in checks:
            issues.extend(_check_quote_length(quote, lint_cfg))
        if spell is not None:
            issues.extend(_check_spelling(quote, spell, ignore_words))
        if 'no-tags' in checks:
            issues.extend(_check_no_tags(quote))
        if 'no-author' in checks:
            issues.extend(_check_no_author(quote))
        if 'author-antipatterns' in checks:
            issues.extend(_check_author_antipatterns(quote, lint_cfg))
        if 'multiple-stars' in checks:
            issues.extend(_check_multiple_stars(quote))
        if 'required-tag-group' in checks:
            issues.extend(_check_required_tag_groups(quote, lint_cfg))
    return issues


def apply_fixes(quotes, issues):
    """Apply all fixable issues to the quote list.

    Returns (fixed_quotes, fix_count). Mutates quote objects in place.
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

        # Smart-quotes and smart-dashes: apply transformations to current field values
        for field_name in ('quote', 'author', 'publication'):
            sq = [i for i in line_fixes if i.check == 'smart-quotes' and i.field == field_name]
            if sq:
                current = getattr(quote, field_name) or ''
                setattr(quote, field_name, current.translate(_SMART_QUOTE_MAP))
                fix_count += 1
            sd = [i for i in line_fixes if i.check == 'smart-dashes' and i.field == field_name]
            if sd:
                current = getattr(quote, field_name) or ''
                setattr(quote, field_name, current.translate(_SMART_DASH_MAP))
                fix_count += 1
            ds = [i for i in line_fixes if i.check == 'double-spaces' and i.field == field_name]
            if ds:
                current = getattr(quote, field_name) or ''
                setattr(quote, field_name, re.sub(r'  +', ' ', current))
                fix_count += 1


    return quotes, fix_count


# ---------------------------------------------------------------------------
# Private check helpers
# ---------------------------------------------------------------------------

_ASCII_SKIP = frozenset(_SMART_QUOTE_CHARS) | frozenset(_SMART_DASH_CHARS)


def _check_ascii(quote):
    issues = []
    for field_name, value in [('quote', quote.quote), ('author', quote.author), ('publication', quote.publication)]:
        if value is None:
            continue
        non_ascii = [(i, c) for i, c in enumerate(value) if ord(c) > 127 and c not in _ASCII_SKIP]
        if non_ascii:
            pos, char = non_ascii[0]
            issues.append(LintIssue(
                line_number=quote.line_number,
                check='ascii',
                field=field_name,
                message='Non-ASCII character {!r} at position {} in {}'.format(char, pos, field_name),
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
                message='Smart quotes in {}'.format(field_name),
                fixable=True,
                fix_value=fixed,
            ))
    return issues


def _check_smart_dashes(quote):
    issues = []
    for field_name, value in [('quote', quote.quote), ('author', quote.author), ('publication', quote.publication)]:
        if value is None:
            continue
        found = [c for c in value if c in _SMART_DASH_CHARS]
        if found:
            names = sorted({_SMART_DASH_NAMES[c] for c in found})
            fixed = value.translate(_SMART_DASH_MAP)
            issues.append(LintIssue(
                line_number=quote.line_number,
                check='smart-dashes',
                field=field_name,
                message='Non-standard {} in {} (use ASCII hyphen)'.format(
                    ', '.join(names), field_name),
                fixable=True,
                fix_value=fixed,
            ))
    return issues


def _check_double_spaces(quote):
    issues = []
    for field_name, value in [('quote', quote.quote), ('author', quote.author), ('publication', quote.publication)]:
        if value is None:
            continue
        if '  ' in value:
            fixed = re.sub(r'  +', ' ', value)
            issues.append(LintIssue(
                line_number=quote.line_number,
                check='double-spaces',
                field=field_name,
                message='Multiple consecutive spaces in {}'.format(field_name),
                fixable=True,
                fix_value=fixed,
            ))
    return issues


def _check_quote_length(quote, lint_cfg):
    max_len = int(lint_cfg.get('lint_max_quote_length', '0'))
    if max_len <= 0:
        return []
    length = len(quote.quote)
    if length > max_len:
        return [LintIssue(
            line_number=quote.line_number,
            check='quote-too-long',
            field='quote',
            message='Quote is {} characters, exceeds maximum of {}'.format(length, max_len),
        )]
    return []


def _make_spellchecker(lint_cfg):
    """Create a SpellChecker instance once, or return (None, None) if unavailable."""
    try:
        from spellchecker import SpellChecker
    except ImportError:
        return None, None

    ignore_raw = lint_cfg.get('lint_spell_ignore', '')
    ignore_words = {w.strip().lower() for w in ignore_raw.split(',') if w.strip()} | _SPELL_IGNORE_BUILTIN

    spell = SpellChecker()
    if ignore_words:
        spell.word_frequency.load_words(ignore_words)
    return spell, ignore_words


def _check_spelling(quote, spell, ignore_words):
    issues = []
    for field_name, value in [('quote', quote.quote)]:
        if not value:
            continue
        raw_words = re.findall(r"[a-zA-Z']+", value)
        words = [w.strip("'") for w in raw_words if w.strip("'")]
        misspelled = spell.unknown(words) - ignore_words
        for word in sorted(misspelled):
            issues.append(LintIssue(
                line_number=quote.line_number,
                check='spelling',
                field=field_name,
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

    if _ANON_RE.match(author) and author.strip() != 'Unknown':
        issues.append(LintIssue(
            line_number=quote.line_number,
            check='author-antipatterns',
            field='author',
            message='Author matches unknown/anonymous pattern: {!r} (use "Unknown" instead)'.format(author),
        ))

    allcaps = _ALLCAPS_WORD_RE.findall(author)
    if allcaps:
        issues.append(LintIssue(
            line_number=quote.line_number,
            check='author-antipatterns',
            field='author',
            message='Author contains all-caps word(s): {}'.format(', '.join(allcaps)),
        ))

    raw_patterns = lint_cfg.get('lint_author_antipattern_regex', '')
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


def _check_required_tag_groups(quote, lint_cfg):
    issues = []
    for key, value in lint_cfg.items():
        if not key.startswith('lint_required_group_'):
            continue
        group_name = key[len('lint_required_group_'):]
        required_tags = {t.strip() for t in value.split(',') if t.strip()}
        if not required_tags:
            continue
        if not any(tag in required_tags for tag in quote.tags):
            issues.append(LintIssue(
                line_number=quote.line_number,
                check='required-tag-group',
                field='tags',
                message='Quote missing required tag from group {!r} (expected one of: {})'.format(
                    group_name, ', '.join(sorted(required_tags))
                ),
            ))
    return issues
