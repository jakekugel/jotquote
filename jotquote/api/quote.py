# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import hashlib
import re
from string import ascii_letters

import click

INVALID_CHARS_QUOTE = re.compile('[|"\n\r]')
INVALID_CHARS = re.compile('[|\n\r]')


class Quote:
    """A quote with author, optional publication, and tags.

    Attributes:
        quote (str): The quote text.
        author (str): Name of the person to whom the quote is attributed.
        publication (str | None): Publication containing the quote, or ``None``
            if not recorded.
        tags (list[str]): Zero or more tags associated with the quote.
        line_number (int): 1-based line number of the quote in the quote file
            it was read from; 0 for quotes that were not read from a file.
    """

    def __init__(self, quote, author, publication, tags):
        """Construct a Quote after validating the input fields.

        Args:
            quote (str): The quote text.  Leading/trailing whitespace is stripped.
            author (str): The author of the quote.  Leading/trailing whitespace
                is stripped.
            publication (str | None): The publication containing the quote, or
                ``None``.  Leading/trailing whitespace is stripped when
                provided.
            tags (list[str] | None): List of tag strings, or ``None`` for no
                tags.

        Raises:
            click.ClickException: If any of ``quote``, ``author``, or
                ``publication`` contains a forbidden character (pipe, double
                quote, newline, carriage return), or if ``tags`` is not a list.
        """
        self.quote = quote.strip()
        self.author = author.strip()
        if publication is None:
            self.publication = None
        else:
            self.publication = publication.strip()

        _assert_no_invalid_chars_quote(self.quote, 'quote')
        _assert_no_invalid_chars(self.author, 'author')

        if self.publication is not None:
            _assert_no_invalid_chars(self.publication, 'publication')

        self.tags = []
        self.set_tags(tags)
        self.line_number = 0

    def __eq__(self, other):
        """Return True if two quotes have the same quote, author, publication, and tags."""
        if (
            (self.quote == other.quote)
            and (self.author == other.author)
            and (self.publication == other.publication)
            and (self.tags == other.tags)
        ):
            return True
        else:
            return False

    def __ne__(self, other):
        """Return True if the two quotes are not equal (see :meth:`__eq__`)."""
        return not (self == other)

    def has_tag(self, tag):
        """Return True if this quote has the given tag.

        Args:
            tag (str): The tag to look for.

        Returns:
            bool: ``True`` if ``tag`` is in this quote's tags.
        """
        if tag in self.tags:
            return True
        return False

    def has_tags(self, tags):
        """Return True if this quote has every tag in the given iterable.

        Args:
            tags (Iterable[str]): Tags to look for.

        Returns:
            bool: ``True`` if every tag in ``tags`` is present on this quote.
        """
        for tag in tags:
            if tag not in self.tags:
                return False
        return True

    def has_keyword(self, keyword):
        """Return True if the keyword appears in the quote, author, publication, or tags.

        Args:
            keyword (str): Substring to search for.

        Returns:
            bool: ``True`` if ``keyword`` appears in any searchable field.
        """
        if keyword in self.quote or keyword in self.author or keyword in self.publication or self.has_tag(keyword):
            return True
        return False

    def set_tags(self, tags):
        """Replace this quote's tags with the given list.

        Args:
            tags (list[str] | None): New list of tags.  ``None`` clears tags.

        Raises:
            click.ClickException: If ``tags`` is not ``None`` and not a list.
        """
        if tags is None:
            self.tags = []
        else:
            if type(tags) is not list:
                raise click.ClickException('The quote object was not given a list for tags parameter.')
            self.tags = tags

    def get_hash(self):
        """Return a 16-character hex hash for this quote.

        The hash is computed in a single pass over the quote text: the first
        (lowercased) letter of each alphabetic word is collected, and the
        resulting string is hashed with MD5.  Non-alphabetic characters act as
        word separators and are otherwise ignored.  Since there is a chance of
        hash collision, callers should verify that only one quote matches.

        The intent of this hash is to tolerate minor edits to the quote text
        while still matching the same quote.  The first letter of a word is
        usually less prone to a typo than other characters, and ignoring
        non-alphabetic characters also makes the hash more robust to formatting
        changes.

        Returns:
            str: The first 16 hex characters of the MD5 digest.
        """
        # Single pass: record the first lowercase letter of every alphabetic word.
        first_letters = []
        in_word = False
        for ch in self.quote:
            if ch.isalpha():
                if not in_word:
                    first_letters.append(ch.lower())
                    in_word = True
            else:
                in_word = False
        acronym = ''.join(first_letters)
        m = hashlib.md5()
        m.update(acronym.encode('utf-8'))
        return m.hexdigest()[0:16]

    def get_num_stars(self):
        """Return the star rating (0-5) derived from star tags.

        The star tags are ``1star``, ``2stars``, ``3stars``, ``4stars``, and
        ``5stars``.  If more than one star tag is present, the lowest one
        wins.

        Returns:
            int: A rating between 0 and 5, inclusive.
        """
        for i, label in enumerate(['1star', '2stars', '3stars', '4stars', '5stars'], 1):
            if self.has_tag(label):
                return i
        return 0

    def get_line_number(self):
        """Return the line number of this quote in the quote file.

        Returns:
            int: The 1-based line number, or 0 for quotes that were not read
                from a file.
        """
        return self.line_number


def parse_quote(new_quote, simple_format=True):
    """Parse a single quote string into a :class:`Quote`.

    If ``simple_format`` is True, the line is expected in
    ``<quote> - <author> [(publication)]`` form.  If False, the pipe-delimited
    quote-file format is used:
    ``<quote>|<author>|[<publication>]|[<tag1>,<tag2>,...]``.

    The following characters are not allowed in the quote, author, and
    publication fields: pipe (``|``), double quote (``"``), newline, and
    carriage return.  Tags are restricted to letters, digits, and underscores.

    Args:
        new_quote (str): The raw quote line to parse.
        simple_format (bool): If ``True`` (default) use the human-friendly
            hyphen-separated format; if ``False`` use the pipe-delimited format.

    Returns:
        Quote: The parsed quote object.

    Raises:
        click.ClickException: If the line cannot be parsed.
    """
    return _parse_quote(new_quote, simple_format=simple_format)


def parse_tags(tag_string):
    """Parse a comma-separated tag string into a sorted list of unique tags.

    Args:
        tag_string (str): Comma-separated tag string (e.g. ``'a, b, c'``).

    Returns:
        list[str]: Sorted list of unique non-empty tags.

    Raises:
        click.ClickException: If any tag contains characters other than
            ASCII letters, digits, or underscores.
    """
    return _parse_tags(tag_string)


def _parse_quote(raw_line, simple_format=True):
    """This internal function takes a single line string containing quote in
    one of two formats.  If simple_format=True, the quote is expected in the
    format:

        <quote> - <author> [(publication)]

    If simple_quote=False, the quote is expected in same format as quote file:

        <quote>|<author>|[<publication>]|[<tag1>,<tag2>,...]

    The function parses the quote in the given format and returns a Quote object.
    An exception is raised if there is a syntax error.

    The following characters are not allowed in the quote, author, and
    publication:

        pipe character (|)
        double quote (")
        newline (0x0a)
        carriage return (0x0d)

    The tags are restricted to letters, digits, and underscore characters.
    """
    line = raw_line.strip()

    if simple_format:
        quotestring, author, publication, tags = _parse_quote_simple(line)
    else:
        quotestring, author, publication, tags = _parse_quote_extended(line)

    if len(quotestring) == 0:
        raise click.ClickException('a quote was not found')

    if len(author) == 0:
        raise click.ClickException(
            'an author was not included with the quote.  ' + 'Expecting quote in the format "<quote> - <author>".'
        )

    quote = Quote(quotestring, author, publication, tags)
    return quote


def _parse_quote_simple(line):
    """Internal function to parse a single quote line in simple format."""
    if any(c == '|' for c in line):
        raise click.ClickException('the quote included an embedded pipe character (|)')

    # Get a list of matchers for hyphens next to and not next to a space char
    hyphen_w_period = list(re.finditer('(?<=\\.)\\s*[-]\\s*', line))
    hyphen_w_space = list(re.finditer('\\s+-\\s*|\\s*-\\s+', line))
    hyphen_wo_space = list(re.finditer('(?<=[^ ])-(?=[^ ])', line))

    # Based on hyphens found, infer which one separates quote from author.
    if len(hyphen_w_period) == 1:
        selected_matcher = hyphen_w_period[0]
    elif len(hyphen_w_space) == 1:
        selected_matcher = hyphen_w_space[0]
    elif len(hyphen_w_space) == 0 and len(hyphen_wo_space) == 1:
        selected_matcher = hyphen_wo_space[0]
    else:
        raise click.ClickException('unable to determine which hyphen separates the quote from the author.')

    quote = line[: selected_matcher.start()]
    author = line[selected_matcher.end() :]

    # Check if publication exists using parentheses
    regexes = [
        '^([^,]+)\\s*\\((.*)\\)$',  # Author name (publication)
        '^([^,]+),\\s*[(](.+)[)]$',  # Author name, (publication)
        "^([^,]+),\\s*([^,']+)$",  # Author name, publication
        "^([^,]+),\\s*'(.+)'$",  # Author name, 'publication'
        "^([^,\\(\\)']+)\\s*()$",  # Author name
    ]
    for regex in regexes:
        match = re.search(regex, author)

        if match is not None:
            break

    if match is not None:
        author = match.group(1).strip()
        publication = match.group(2).strip()
    else:
        raise click.ClickException(
            "unable to parse the author and publication.  Try 'Quote - Author (Publication)', or 'Quote - Author, Publication'"
        )

    if publication == '':
        publication = None

    return quote, author, publication, []


def _parse_quote_extended(quote_line):
    """An internal function to parse single quote line in the pipe-delimited
    (extended) format.
    """
    fields = quote_line.split('|')

    if len(fields) != 4:
        raise click.ClickException("did not find 3 '|' characters")

    quote = fields[0].strip()
    author = fields[1].strip()
    publication = fields[2].strip()
    tags_string = fields[3].strip()
    tags = _parse_tags(tags_string)
    return quote, author, publication, tags


def _parse_tags(tag_string):
    """An internal function to parse tags, its error messages are not complete sentence."""
    rawtags = tag_string.split(',')
    tagset = set()
    for rawtag in rawtags:
        tag = rawtag.strip()
        if not all(c in ascii_letters + '0123456789_' for c in tag):
            raise click.ClickException(
                "invalid tag '{0}': only numbers, letters, and commas are allowed in tags".format(tag)
            )
        if tag != '':
            tagset.add(tag)

    return sorted(list(tagset))


def _assert_does_not_contain(text, char, component_name):
    """Internal function to assert that text does not contain char.  If it does,
    an exception is raised from this function.
    """
    if any(c in char for c in text):
        _raise_invalid_char_exception(char, component_name)


def _assert_no_invalid_chars_quote(text, component_name):
    match = INVALID_CHARS_QUOTE.search(text)
    if match is not None:
        char = text[match.span()[0] : match.span()[1]]
        _raise_invalid_char_exception(char, component_name)


def _assert_no_invalid_chars(text, component_name):
    match = INVALID_CHARS.search(text)
    if match is not None:
        char = text[match.span()[0] : match.span()[1]]
        _raise_invalid_char_exception(char, component_name)


def _raise_invalid_char_exception(char, component_name):
    if char == '\n':
        charstring = 'newline (0x0a)'
    elif char == '\r':
        charstring = 'carriage return (0x0d)'
    else:
        charstring = '(' + char + ')'
    raise click.ClickException('the {} included a {} character'.format(component_name, charstring))
