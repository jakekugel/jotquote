# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import re
from dataclasses import dataclass
from typing import ClassVar, Optional

from jotquote.api import config as _config

# Smart/typographic quote characters and their ASCII replacements
_SMART_QUOTE_CHARS = '‘’“”‹›«»'
_SMART_QUOTE_MAP = str.maketrans(
    '‘’“”‹›«»',
    "''''''''",
)

# Unicode dash/hyphen characters and their ASCII hyphen replacement
_SMART_DASH_NAMES = {
    '‐': 'hyphen',
    '‑': 'non-breaking hyphen',
    '‒': 'figure dash',
    '–': 'en dash',
    '—': 'em dash',
    '―': 'horizontal bar',
    '−': 'minus sign',
    '﹘': 'small em dash',
    '﹣': 'small hyphen-minus',
    '－': 'fullwidth hyphen-minus',
}
_SMART_DASH_CHARS = ''.join(_SMART_DASH_NAMES)
_SMART_DASH_MAP = str.maketrans(_SMART_DASH_CHARS, '-' * len(_SMART_DASH_CHARS))

# Unicode horizontal ellipsis (U+2026); auto-fixed to three ASCII periods.
_UNICODE_ELLIPSIS = '…'

# Trailing closing-punctuation characters that are stripped before checking for
# terminal punctuation (e.g. a quote ending in `."` is considered terminated).
_TRAILING_CLOSE_CHARS = '"\'”’)]'
_END_PUNCTUATION = '.!?'

# Fields a per-quote check may attach issues to.
_TEXT_FIELDS = ('quote', 'author', 'publication')


@dataclass
class LintIssue:
    """A single lint finding attached to a specific quote.

    Attributes:
        line_number (int): 1-based line number of the quote in the source file.
        check (str): Name of the check that produced the issue (e.g.
            ``'smart-quotes'``).
        field (str): The field the issue applies to — one of ``'quote'``,
            ``'author'``, ``'publication'``, or ``'tags'``.
        message (str): Human-readable description of the issue.
        fixable (bool): ``True`` if :func:`apply_fixes` can auto-correct this
            issue.
        fix_value (str | None): Single-issue preview of the corrected field
            value (what the field would become if this issue alone were
            applied to the original text). Useful to external callers such as
            CLI dry-run output; :func:`apply_fixes` does not consume it,
            because applying multiple issues to the same field requires
            recomputing against the live attribute value rather than stacking
            stored previews.
    """

    line_number: int
    check: str
    field: str  # One of: 'quote', 'author', 'publication', 'tags'
    message: str
    fixable: bool = False
    fix_value: Optional[str] = None


def lint_quotes(quotes, checks, config):
    """Run the enabled lint checks against a list of quotes.

    Args:
        quotes (list[Quote]): The quotes to check.
        checks (Iterable[str]): Names of the checks to run.  Unknown names
            are silently ignored.
        config (configparser.ConfigParser): Application config.  Used to
            look up per-check configuration in the ``[lint]`` section.

    Returns:
        list[LintIssue]: All issues found, in the order produced by the
            checks.
    """
    lint_cfg = config[_config.SECTION_LINT]
    issues = []

    # Dispatch each enabled check against the appropriate target (per-quote
    # or whole-file). The check registry knows its own scope and config
    # requirements, so this loop is shape-agnostic.
    for name in checks:
        check_obj = CHECKS.get(name)
        if check_obj is None:
            continue
        cfg = lint_cfg if check_obj.needs_config else None
        if check_obj.scope == 'file':
            issues.extend(check_obj.check(quotes, config=cfg))
        else:
            for quote in quotes:
                issues.extend(check_obj.check(quote, config=cfg))
    return issues


def apply_fixes(quotes, issues):
    """Apply every auto-fixable issue to the matching quote, in place.

    Args:
        quotes (list[Quote]): The quotes to update.  Modified in place.
        issues (list[LintIssue]): Issues produced by :func:`lint_quotes`.
            Non-fixable issues, and issues whose check is not registered,
            are ignored.

    Returns:
        tuple[list[Quote], int]: The (mutated) ``quotes`` list and the count
            of fixes that were applied.
    """
    by_line = {q.line_number: q for q in quotes}

    fix_count = 0
    for issue in issues:
        if not issue.fixable:
            continue
        quote = by_line.get(issue.line_number)
        if quote is None:
            continue
        check_obj = CHECKS.get(issue.check)
        if check_obj is None:
            continue
        check_obj.fix(quote, issue)
        fix_count += 1
    return quotes, fix_count


# ---------------------------------------------------------------------------
# Check infrastructure
# ---------------------------------------------------------------------------


CHECKS: 'dict[str, Check]' = {}


class Check:
    """Base class for lint checks.

    Subclassing this class registers the check in :data:`CHECKS` automatically
    via ``__init_subclass__`` at the moment the subclass body executes — no
    explicit registration list is needed.

    Class attributes:
        name (str): Canonical identifier (e.g. ``'smart-quotes'``). Concrete
            subclasses must declare this.
        scope (str): ``'quote'`` for per-quote checks (the default) or
            ``'file'`` for whole-file checks.
        needs_config (bool): If ``True``, :meth:`check` is called with the
            ``[lint]`` config section. Default ``False``.
        fixable (bool): If ``True``, instances of this check produce
            :class:`LintIssue` records with ``fixable=True`` and
            :func:`apply_fixes` will invoke :meth:`fix` on them.
    """

    name: ClassVar[str]
    scope: ClassVar[str] = 'quote'
    needs_config: ClassVar[bool] = False
    fixable: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Register only concrete subclasses that declared their own `name`.
        # Intermediate abstract bases can omit `name` and will not register.
        if 'name' in cls.__dict__:
            CHECKS[cls.name] = cls()

    def check(self, target, *, config=None):
        """Return zero or more LintIssues for ``target``.

        When ``scope == 'quote'``, ``target`` is a single ``Quote``.  When
        ``scope == 'file'``, ``target`` is the full ``list[Quote]``.
        """
        raise NotImplementedError

    def fix(self, quote, issue):
        """Mutate ``quote`` in place to resolve ``issue``.

        :func:`apply_fixes` only calls this method when ``issue.fixable`` is
        ``True``, so non-fixable checks may leave the default implementation
        in place.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Concrete checks — each registers itself in CHECKS at class-body execution.
# ---------------------------------------------------------------------------


class SmartQuotesCheck(Check):
    """Flag and fix typographic/smart quote characters in any text field."""

    name = 'smart-quotes'
    fixable = True

    def check(self, quote, *, config=None):
        issues = []
        for field_name in _TEXT_FIELDS:
            value = getattr(quote, field_name)
            if value is None:
                continue
            if any(c in _SMART_QUOTE_CHARS for c in value):
                issues.append(
                    LintIssue(
                        line_number=quote.line_number,
                        check=self.name,
                        field=field_name,
                        message='Smart quotes in {}'.format(field_name),
                        fixable=True,
                        fix_value=value.translate(_SMART_QUOTE_MAP),
                    )
                )
        return issues

    def fix(self, quote, issue):
        current = getattr(quote, issue.field) or ''
        setattr(quote, issue.field, current.translate(_SMART_QUOTE_MAP))


class SmartDashesCheck(Check):
    """Flag and fix unicode dash/hyphen variants in any text field."""

    name = 'smart-dashes'
    fixable = True

    def check(self, quote, *, config=None):
        issues = []
        for field_name in _TEXT_FIELDS:
            value = getattr(quote, field_name)
            if value is None:
                continue
            found = [c for c in value if c in _SMART_DASH_CHARS]
            if found:
                names = sorted({_SMART_DASH_NAMES[c] for c in found})
                issues.append(
                    LintIssue(
                        line_number=quote.line_number,
                        check=self.name,
                        field=field_name,
                        message='Non-standard {} in {} (use ASCII hyphen)'.format(
                            ', '.join(names), field_name
                        ),
                        fixable=True,
                        fix_value=value.translate(_SMART_DASH_MAP),
                    )
                )
        return issues

    def fix(self, quote, issue):
        current = getattr(quote, issue.field) or ''
        setattr(quote, issue.field, current.translate(_SMART_DASH_MAP))


class UnicodeEllipsisCheck(Check):
    """Flag and fix the Unicode horizontal ellipsis (U+2026) in any text field."""

    name = 'unicode-ellipsis'
    fixable = True

    def check(self, quote, *, config=None):
        issues = []
        for field_name in _TEXT_FIELDS:
            value = getattr(quote, field_name)
            if value is None:
                continue
            if _UNICODE_ELLIPSIS in value:
                issues.append(
                    LintIssue(
                        line_number=quote.line_number,
                        check=self.name,
                        field=field_name,
                        message='Unicode ellipsis in {}'.format(field_name),
                        fixable=True,
                        fix_value=value.replace(_UNICODE_ELLIPSIS, '...'),
                    )
                )
        return issues

    def fix(self, quote, issue):
        current = getattr(quote, issue.field) or ''
        setattr(quote, issue.field, current.replace(_UNICODE_ELLIPSIS, '...'))


class DoubleSpacesCheck(Check):
    """Flag and fix runs of multiple consecutive spaces in any text field."""

    name = 'double-spaces'
    fixable = True

    def check(self, quote, *, config=None):
        issues = []
        for field_name in _TEXT_FIELDS:
            value = getattr(quote, field_name)
            if value is None:
                continue
            if '  ' in value:
                issues.append(
                    LintIssue(
                        line_number=quote.line_number,
                        check=self.name,
                        field=field_name,
                        message='Multiple consecutive spaces in {}'.format(field_name),
                        fixable=True,
                        fix_value=re.sub(r'  +', ' ', value),
                    )
                )
        return issues

    def fix(self, quote, issue):
        current = getattr(quote, issue.field) or ''
        setattr(quote, issue.field, re.sub(r'  +', ' ', current))


class QuoteLengthCheck(Check):
    """Flag quotes exceeding the configured maximum length (max_quote_length)."""

    name = 'quote-too-long'
    needs_config = True

    def check(self, quote, *, config=None):
        max_len = int(config.get('max_quote_length', '0'))
        if max_len <= 0:
            return []
        length = len(quote.quote)
        if length > max_len:
            return [
                LintIssue(
                    line_number=quote.line_number,
                    check=self.name,
                    field='quote',
                    message='Quote is {} characters, exceeds maximum of {}'.format(
                        length, max_len
                    ),
                )
            ]
        return []


class NoTagsCheck(Check):
    """Flag quotes with no tags."""

    name = 'no-tags'

    def check(self, quote, *, config=None):
        if not quote.tags:
            return [
                LintIssue(
                    line_number=quote.line_number,
                    check=self.name,
                    field='tags',
                    message='Quote has no tags',
                )
            ]
        return []


class NoAuthorCheck(Check):
    """Flag and fix quotes with no author (auto-fix sets the author to 'Unknown')."""

    name = 'no-author'
    fixable = True

    def check(self, quote, *, config=None):
        if not quote.author or not quote.author.strip():
            return [
                LintIssue(
                    line_number=quote.line_number,
                    check=self.name,
                    field='author',
                    message='No author specified',
                    fixable=True,
                    fix_value='Unknown',
                )
            ]
        return []

    def fix(self, quote, issue):
        quote.author = 'Unknown'


class RequiredTagGroupCheck(Check):
    """Flag quotes missing a tag from any user-defined required tag group."""

    name = 'required-tag-group'
    needs_config = True

    def check(self, quote, *, config=None):
        issues = []
        for key, value in config.items():
            if not key.startswith('required_group_'):
                continue
            required_tags = {t.strip() for t in value.split(',') if t.strip()}
            if not required_tags:
                continue
            if not any(tag in required_tags for tag in quote.tags):
                issues.append(
                    LintIssue(
                        line_number=quote.line_number,
                        check=self.name,
                        field='tags',
                        message='Quote must have one of the following tags: {}'.format(
                            ', '.join(sorted(required_tags))
                        ),
                    )
                )
        return issues


class DuplicateHashCheck(Check):
    """Flag quotes whose fuzzy hash collides with an earlier quote in the file."""

    name = 'duplicate-hash'
    scope = 'file'

    def check(self, quotes, *, config=None):
        issues = []
        seen = {}
        for quote in quotes:
            h = quote.get_hash()
            if h in seen:
                issues.append(
                    LintIssue(
                        line_number=quote.line_number,
                        check=self.name,
                        field='quote',
                        message='Quote hash matches the quote on line {}'.format(seen[h]),
                    )
                )
            else:
                seen[h] = quote.line_number
        return issues


class MissingEndPunctuationCheck(Check):
    """Flag and fix quotes whose text does not end with terminal punctuation."""

    name = 'missing-end-punctuation'
    fixable = True

    def check(self, quote, *, config=None):
        text = quote.quote
        stripped = text.rstrip().rstrip(_TRAILING_CLOSE_CHARS)
        if not stripped:
            return []
        if stripped[-1] in _END_PUNCTUATION:
            return []
        return [
            LintIssue(
                line_number=quote.line_number,
                check=self.name,
                field='quote',
                message='Quote does not end with terminal punctuation',
                fixable=True,
                fix_value=text.rstrip() + '.',
            )
        ]

    def fix(self, quote, issue):
        quote.quote = quote.quote.rstrip() + '.'


class LowercaseStartCheck(Check):
    """Flag and fix quotes whose first alphabetic character is lowercase."""

    name = 'lowercase-start'
    fixable = True

    def check(self, quote, *, config=None):
        text = quote.quote
        for idx, ch in enumerate(text):
            if ch.isalpha():
                if ch.islower():
                    return [
                        LintIssue(
                            line_number=quote.line_number,
                            check=self.name,
                            field='quote',
                            message='Quote should start with a capital letter',
                            fixable=True,
                            fix_value=text[:idx] + ch.upper() + text[idx + 1 :],
                        )
                    ]
                return []
        return []

    def fix(self, quote, issue):
        text = quote.quote
        for idx, ch in enumerate(text):
            if ch.isalpha():
                quote.quote = text[:idx] + ch.upper() + text[idx + 1 :]
                return


# Canonical, frozen view of the registered check names. Derived from CHECKS
# after every concrete subclass above has self-registered, so adding a new
# check (or removing one) requires no edits here.
ALL_CHECKS = frozenset(CHECKS)
