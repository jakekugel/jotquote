# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import hashlib
import os
import random as randomlib
import re
import shutil
from configparser import ConfigParser
from string import ascii_letters

import click

APP_NAME = 'jotquote'
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.jotquote', 'settings.conf')
INVALID_CHARS_QUOTE = re.compile('[|"\n\r]')
INVALID_CHARS = re.compile('[|\n\r]')

ALL_CHECKS = frozenset(
    {
        'ascii',  # Flag non-ASCII characters in quote, author, or publication
        'smart-quotes',  # Flag (and fix) typographic/smart quote characters
        'smart-dashes',  # Flag (and fix) unicode dash/hyphen variants
        'double-spaces',  # Flag (and fix) runs of multiple spaces in any field
        'quote-too-long',  # Flag quotes exceeding a configurable max length (max_quote_length)
        'no-tags',  # Flag quotes with no tags
        'no-author',  # Flag quotes with no author
        'author-antipatterns',  # Flag author fields matching known bad patterns (anonymous, all-caps, source-type words)
        'required-tag-group',  # Flag quotes missing a tag from any user-defined required tag group
    }
)

SECTION_GENERAL = 'general'
SECTION_LINT = 'lint'
SECTION_WEB = 'web'
# Retained for backwards compatibility with the old single-section [jotquote] config format
_SECTION_LEGACY = 'jotquote'


class Quote:
    """A quote with these properties:
    quote: string with actual quote text.
    author: to whom quote is attributed
    publication: optional, the publication containing the quote
    tags: list of tags (strings)
    """

    def __init__(self, quote, author, publication, tags):
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
        return not (self == other)

    def has_tag(self, tag):
        if tag in self.tags:
            return True
        return False

    def has_tags(self, tags):
        for tag in tags:
            if tag not in self.tags:
                return False
        return True

    def has_keyword(self, keyword):
        if keyword in self.quote or keyword in self.author or keyword in self.publication or self.has_tag(keyword):
            return True
        return False

    def set_tags(self, tags):
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
        """Return the star rating (0-5) derived from star tags (1star, 2stars, etc.)."""
        for i, label in enumerate(['1star', '2stars', '3stars', '4stars', '5stars'], 1):
            if self.has_tag(label):
                return i
        return 0

    def get_line_number(self):
        """Return the line number of this quote in the quote file."""
        return self.line_number


def read_quotes(filename):
    """Given a path to quote file, this function returns a list of Quote objects containing
    the quotes.
    """
    quotes, _ = read_quotes_with_hash(filename)
    return quotes


def read_quotes_with_hash(filename):
    """Read quotes and compute SHA-256 hash of the file in a single read.

    Returns (quotes, sha256_hex) where quotes is a list of Quote objects
    and sha256_hex is the hex digest of the file contents.
    """
    if not os.path.exists(filename):
        raise click.ClickException("The quote file '{0}' was not found.".format(filename))

    with open(filename, 'rb') as f:
        raw = f.read()

    sha256_hex = hashlib.sha256(raw).hexdigest()
    lines = raw.decode('utf-8').splitlines()
    quotes = parse_quotes(lines, filename, simple_format=False)
    _check_for_duplicates(quotes, filename)

    return quotes, sha256_hex


def read_tags(quotefile):
    """Returns a list of all unique tags in use in the given quote file."""

    alltags = set()
    quotes = read_quotes(quotefile)
    for quote in quotes:
        for tag in quote.tags:
            alltags.add(tag)

    return sorted(list(alltags))


def get_first_match(quotes, tags=None, keyword=None, number=None, hash_arg=None, rand=False, excluded_tags=None):
    """Return the first Quote from quotes that matches all provided criteria, or None.

    tags          - comma-separated tag string; quote must have all listed tags
    keyword       - substring match against quote text, author, and publication
    number        - 1-based position in the list
    hash_arg      - MD5 hash prefix (first 16 chars) of the quote text
    rand          - if True, return a random match instead of the first one
    excluded_tags - comma-separated tag string; quote must not contain any of these tags
    """
    taglist = parse_tags(tags) if tags is not None else []
    excluded_taglist = parse_tags(excluded_tags) if excluded_tags is not None else []

    matched = [
        quote
        for index, quote in enumerate(quotes)
        if (keyword is None or quote.has_keyword(keyword))
        and (tags is None or quote.has_tags(taglist))
        and (number is None or number == index + 1)
        and (hash_arg is None or hash_arg == quote.get_hash())
        and not any(t in quote.tags for t in excluded_taglist)
    ]

    if not matched:
        return None
    if rand:
        return randomlib.choice(matched)
    return matched[0]


def settags(quotefile, n, hash, newtags):
    """Set tags on a quote identified by number (1-based) or hash.

    Exactly one of n or hash must be provided.  newtags is a list of tag strings
    (already parsed); pass [] to clear all tags.
    """
    if n is not None and hash is not None:
        raise click.ClickException('both the -s and -n option were included, but only one allowed.')
    if n is None and hash is None:
        raise click.ClickException('either the -n or the -s argument must be included.')

    quotes, sha256 = read_quotes_with_hash(quotefile)

    if n is not None:
        if n < 1 or n > len(quotes):
            raise click.ClickException('quote number {0} is out of range (1-{1}).'.format(n, len(quotes)))
        quote = quotes[n - 1]
    else:
        matched = [q for q in quotes if q.get_hash() == hash]
        if not matched:
            raise click.ClickException("no quote found with hash '{0}'.".format(hash))
        quote = matched[0]

    quote.set_tags(newtags)
    write_quotes(quotefile, quotes, expected_sha256=sha256)


def parse_quotes(rawlines, filename, encoding=None, simple_format=True):
    """Accepts an iterable String variable containing raw lines to be parsed
    and returns a list of Quote objects.  Blank lines, or lines beginning with
    '#' character are skipped.
    """
    quotes = []
    linenum = 0

    for rawline in rawlines:
        if encoding:
            line = rawline.decode(encoding).strip()
        else:
            line = rawline.strip()

        linenum += 1

        # Skip blank lines
        if line == '':
            continue

        # Skip lines beginning with '#' (comments)
        if line.startswith('#'):
            continue

        try:
            quote = _parse_quote(line, simple_format=simple_format)
            quote.line_number = linenum
            quotes.append(quote)
        except Exception as exception:
            raise click.ClickException(
                'syntax error on line {0} of {1}: {2}.  Line with error: "{3}"'.format(
                    str(linenum), filename, str(exception), line
                )
            )

    return quotes


def parse_quote(new_quote, simple_format=True):
    """This function accepts a string and parses to Quote object.  See the
    internal function definition for _parse_quote() for the syntax.
    """

    return _parse_quote(new_quote, simple_format=simple_format)


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


def parse_tags(tag_string):
    """Public function that parses tags and returns list of tags."""

    return _parse_tags(tag_string)


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


_GENERAL_KEYS = frozenset(
    {
        'quote_file',
        'line_separator',
        'show_author_count',
    }
)

_LINT_KEYS = frozenset(
    {
        'lint_on_add',
        'lint_author_antipattern_regex',
    }
)

_WEB_KEYS = frozenset(
    {
        'header_provider_extension',
        'quote_resolver_extension',
        'web_port',
        'web_ip',
        'web_expiration_seconds',
        'web_page_title',
        'web_show_stars',
        'web_light_foreground_color',
        'web_light_background_color',
        'web_dark_foreground_color',
        'web_dark_background_color',
    }
)


def _migrate_legacy_section(config):
    """Migrate in-memory config from old [jotquote] section to [general]/[lint]/[web].

    Detects the legacy format (has [jotquote] but no [general]), routes each key
    to the correct new section, strips lint_/web_ prefixes (except lint_on_add which
    retains its prefix), removes [jotquote], and returns True if migration occurred.
    """
    if not config.has_section(_SECTION_LEGACY) or config.has_section(SECTION_GENERAL):
        return False

    for section in (SECTION_GENERAL, SECTION_LINT, SECTION_WEB):
        if not config.has_section(section):
            config.add_section(section)

    for key, value in config.items(_SECTION_LEGACY):
        if key in _LINT_KEYS:
            new_key = key if key == 'lint_on_add' else key[len('lint_') :]
            config[SECTION_LINT][new_key] = value
        elif key.startswith('lint_'):
            config[SECTION_LINT][key[len('lint_') :]] = value
        elif key in _WEB_KEYS:
            new_key = key[len('web_') :] if key.startswith('web_') else key
            config[SECTION_WEB][new_key] = value
        else:
            config[SECTION_GENERAL][key] = value

    config.remove_section(_SECTION_LEGACY)
    return True


def _resolve_config_paths(config, config_dir):
    """Resolve relative path values in config in-place, relative to config_dir."""
    path_lookups = [
        (SECTION_GENERAL, 'quote_file'),
    ]
    for section, key in path_lookups:
        if config.has_option(section, key):
            value = config.get(section, key)
            if value and not os.path.isabs(value):
                config[section][key] = os.path.normpath(os.path.join(config_dir, value))


def get_config():
    """Read settings.conf and return (config, migrated).

    config is a ConfigParser with all settings.  migrated is True if the legacy
    [jotquote] section was detected and migrated in-memory to [general]/[lint]/[web];
    the caller should present a deprecation warning to the user in that case.

    The config file location is taken from the JOTQUOTE_CONFIG environment
    variable if set, otherwise defaults to ~/.jotquote/settings.conf.
    On first run the file is created from jotquote/templates/settings.conf
    and the default quote file is copied alongside it.
    Relative paths in the config (e.g. quote_file = ./quotes.txt) are resolved
    to absolute paths relative to the directory containing settings.conf.
    """
    config_file = os.environ.get('JOTQUOTE_CONFIG') or CONFIG_FILE
    config_dir = os.path.dirname(os.path.abspath(config_file))

    if not os.path.exists(config_file):
        os.makedirs(config_dir, exist_ok=True)

        # Read template and write to config_file with OS-default line endings
        template_conf = os.path.normpath(os.path.join(__file__, '../templates/settings.conf'))
        config = ConfigParser()
        config.read(template_conf)
        with open(config_file, 'w') as f:
            config.write(f)

        # If the quote file doesn't exist, copy the template quotes.txt to the configuration directory, usually ~/.jotquote/quotes.txt
        quote_file_raw = config.get(SECTION_GENERAL, 'quote_file')
        if not os.path.isabs(quote_file_raw):
            quote_file = os.path.normpath(os.path.join(config_dir, quote_file_raw))
        else:
            quote_file = quote_file_raw
        if not os.path.exists(quote_file):
            template_quotes = os.path.normpath(os.path.join(__file__, '../templates/quotes.txt'))
            shutil.copyfile(template_quotes, quote_file)

    config = ConfigParser()
    config.read(config_file)

    # Migrate legacy [jotquote] section to [general]/[lint]/[web]
    migrated = _migrate_legacy_section(config)

    # Ensure optional sections exist
    for section in (SECTION_LINT, SECTION_WEB):
        if not config.has_section(section):
            config.add_section(section)

    _resolve_config_paths(config, config_dir)

    # Validate required property
    if not config.has_option(SECTION_GENERAL, 'quote_file'):
        raise click.ClickException(
            "'quote_file' is not set in [general] section of {}. Please add it to your settings.conf file.".format(
                config_file
            )
        )

    # Add lint defaults in memory if not present
    if not config.has_option(SECTION_LINT, 'enabled_checks'):
        config[SECTION_LINT]['enabled_checks'] = ', '.join(sorted(ALL_CHECKS))

    return config, migrated


def get_filename():
    """Convenience method to get the quote_file property from the
    settings.conf file and verify it exists."""
    config, _ = get_config()
    filename = config.get(SECTION_GENERAL, 'quote_file')
    if not os.path.exists(filename):
        raise click.ClickException("The quote file specified in settings.conf, '{}', was not found.".format(filename))
    return filename


def get_sha256(filename):
    """Return the SHA256 hex digest of the given file."""
    h = hashlib.sha256()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def set_quote(quotefile, line_num, quote, sha256):
    """Replace the quote at line_num with the given Quote object.

    Reads the file, verifies the SHA256 checksum matches sha256 (to detect
    concurrent modifications), replaces the quote at the matching line_number,
    and writes the file atomically via write_quotes().

    Raises ClickException if the checksum does not match or line_num is invalid.
    """
    quotes, current_sha = read_quotes_with_hash(quotefile)
    if current_sha != sha256:
        raise click.ClickException(
            'The quote file has been modified since it was last read. Please reload the page and try again.'
        )
    target = None
    for q in quotes:
        if q.line_number == line_num:
            target = q
            break
    if target is None:
        raise click.ClickException('No quote found at line number {}.'.format(line_num))
    target.quote = quote.quote
    target.author = quote.author
    target.publication = quote.publication
    target.set_tags(quote.tags)
    write_quotes(quotefile, quotes, expected_sha256=current_sha)


def add_quote(filename, quote):
    """Rewrites the quote file with given file name, adding the given new quote.
    Returns total number of quotes including new quote.
    """
    if not isinstance(quote, Quote):
        raise click.ClickException('The quote parameter must be type class Quote.')

    quotes = [quote]
    return add_quotes(filename, quotes)


def add_quotes(filename, newquotes):
    """Adds the list of quotes to end of filename.

    If more than one process calls this function at the same time, the results
    are undefined.

    Returns total number of quotes including new quote.
    """
    if not os.path.exists(filename):
        raise click.ClickException("The quote file '%s' does not exist." % filename)

    if type(newquotes) is not list:
        raise Exception('the add_quotes() function expected a list as second parameter.')

    # Check for duplicates within new quotes.  Exception raised if duplicate found within input lines.
    _check_for_duplicates(newquotes, 'stdin')

    # Read in quotes from the quote file given.  Exception raised on I/O error
    quotes, sha256 = read_quotes_with_hash(filename)

    # Loop through existing quotes and check against new quotes for any duplicates
    for existing_quote in quotes:
        for new_quote in newquotes:
            if new_quote.quote == existing_quote.quote:
                raise click.ClickException(
                    'the quote "{}" is already in the quote file {}.'.format(new_quote.quote, filename)
                )

    # Rewrite quote file with any additional quotes
    quotes.extend(newquotes)
    write_quotes(filename, quotes, expected_sha256=sha256)
    return len(quotes)


def write_quotes(quote_path, quotes, expected_sha256=None):
    """Writes the given list of quotes to quote_path.

    Atomically overwrites quote_path with the quotes in the list.  If more than one
    process calls this function at the same time, the results are undefined.

    If expected_sha256 is provided, verifies the current file's SHA-256 matches
    before writing. Raises ClickException if the file has been modified.
    """
    if not os.path.exists(quote_path):
        raise click.ClickException("the quote file '{0}' was not found.".format(quote_path))

    if expected_sha256 is not None:
        current_sha = get_sha256(quote_path)
        if current_sha != expected_sha256:
            raise click.ClickException(
                'the quote file was modified by another process during this operation. No changes were saved.'
            )

    newline = _get_newline()

    parent_path = os.path.abspath(os.path.join(quote_path, os.pardir))
    quote_file = os.path.basename(quote_path)
    backup_file = '.' + quote_file + '.jotquote.bak'
    backup_path = os.path.join(parent_path, backup_file)

    while True:
        temp_file = '.' + quote_file + str(randomlib.randint(0, 99999999)) + '.jotquote.tmp'
        temp_path = os.path.join(parent_path, temp_file)
        if not os.path.exists(temp_path):
            break

    try:
        # I had previously called open_file with atomic=True and passed the quote
        # file directly, but hit a bug in Cryptomator filesystem where write() failed
        # but the close() succeeded, so Click replaced quote file with a partially
        # written temp file.  Cryptomator fixed the bug, but I am creating the temp
        # file myself now to avoid this class of error, and use atomic=False instead
        # of atomic=True.
        with click.open_file(temp_path, mode='wb', errors='strict', atomic=False) as outfile:
            for quote in quotes:
                output_bytes = format_quote(quote).encode('utf-8') + newline.encode('utf-8')
                outfile.write(output_bytes)

        # Sanity check backup size and line count before overwriting backup
        if os.path.exists(backup_path):
            backup_size = os.path.getsize(backup_path)
            temp_size = os.path.getsize(temp_path)
            if backup_size > temp_size + 1000:
                os.remove(temp_path)
                raise click.ClickException(
                    "the backup file '{0}' is more than 1,000 bytes larger than the quote file '{1}' would be "
                    'after this operation.  This is suspicious, the quote file was not modified.  '
                    'If this was expected, delete the backup file and try again.'.format(backup_file, quote_file)
                )
            with open(backup_path, 'rb') as f:
                backup_lines = f.read().count(b'\n')
            with open(temp_path, 'rb') as f:
                temp_lines = f.read().count(b'\n')
            if backup_lines > temp_lines:
                os.remove(temp_path)
                raise click.ClickException(
                    "the backup file '{0}' has {1} lines but the quote file '{2}' would have {3} lines after "
                    'this operation.  This is suspicious, the quote file was not modified.  '
                    'If this was expected, delete the backup file and try again.'.format(
                        backup_file, backup_lines, quote_file, temp_lines
                    )
                )

        # Create a backup (overwriting existing backup)
        shutil.copy(quote_path, backup_path)
    except click.ClickException:
        raise
    except:
        os.remove(temp_path)
        raise click.ClickException(
            "an error occurred writing the quotes.  The file '{0}' was not modified.".format(quote_path)
        )

    try:
        os.replace(temp_path, quote_path)
    except:
        raise click.ClickException('an error occurred writing the quotes.')


def format_quote(quote):
    """Given a Quote object, this function returns a single-line string containing the quote formatted as
    it will be written to the file: <quote> | <author> | [<publication>] | [<tag1>,<tag2>,...]
    """
    if not isinstance(quote, Quote):
        raise click.ClickException('The quote parameter must be type class Quote.')

    quotestr = quote.quote
    author = quote.author
    publication = quote.publication
    if publication is None:
        publication = ''
    tags = ', '.join(quote.tags)
    return '%s | %s | %s | %s' % (quotestr, author, publication, tags)


def get_random_choice(numquotes):
    """Return a random value between 0 and numquotes -1, inclusive."""

    # Get days since epoch, advancing to next day after 11:45 PM so caches
    # expiring at midnight will already contain the next day's quote
    now = datetime.datetime.now()
    if now.hour == 23 and now.minute >= 45:
        endday = (now + datetime.timedelta(days=1)).date()
    else:
        endday = now.date()
    beginday = datetime.date(2016, 1, 1)
    days_since_epoch = (endday - beginday).days

    # Get quote index
    index = _get_random_value(days_since_epoch, numquotes)
    return index


def _get_random_value(days_since_epoch, numquotes):
    """This function returns a random value between 0 and numquotes - 1.  For a given
    days_since_epoch and numquotes, it will always return the same value.
    """
    numlist = list(range(0, numquotes))
    randomlib.seed(0)
    randomlib.shuffle(numlist)
    index = days_since_epoch % numquotes
    return numlist[index]


def _check_for_duplicates(quotes, source):
    """Throws an exception if the given list of quotes contains duplicates."""

    quoteset = set()
    for index, quote in enumerate(quotes):
        if quote.quote not in quoteset:
            quoteset.add(quote.quote)
        else:
            raise click.ClickException(
                'a duplicate quote was found on line {} of \'{}\'.  Quote: "{}".'.format(index + 1, source, quote.quote)
            )


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


def _get_newline():
    """Return the newline string based on the line_separator config property."""
    config, _ = get_config()
    linesep_property = config.get(SECTION_GENERAL, 'line_separator', fallback='platform')
    if not linesep_property or linesep_property == 'platform':
        return os.linesep
    elif linesep_property == 'unix':
        return '\n'
    elif linesep_property == 'windows':
        return '\r\n'
    else:
        raise click.ClickException(
            "the value '{0}' is not valid value for the line_separator property."
            "  Valid values are 'platform', 'windows', or 'unix'.".format(linesep_property)
        )


def _raise_invalid_char_exception(char, component_name):
    if char == '\n':
        charstring = 'newline (0x0a)'
    elif char == '\r':
        charstring = 'carriage return (0x0d)'
    else:
        charstring = '(' + char + ')'
    raise click.ClickException('the {} included a {} character'.format(component_name, charstring))


if __name__ == '__main__':
    raise click.ClickException('This module is not executable.')
