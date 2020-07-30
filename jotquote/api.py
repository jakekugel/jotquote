# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from __future__ import print_function
from __future__ import unicode_literals

# This import requires 'configparser' to be installed for Python 2.7
# noinspection PyCompatibility
from configparser import ConfigParser
import click
import datetime
import hashlib
import os
import random as randomlib
import re
from string import ascii_letters
from io import open
import shutil


APP_NAME = 'jotquote'
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.jotquote', 'settings.conf')
INVALID_CHARS_QUOTE = re.compile("[|\"\n\r]")
INVALID_CHARS = re.compile("[|\n\r]")


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

        _assert_no_invalid_chars_quote(self.quote, "quote")
        _assert_no_invalid_chars(self.author, "author")

        if self.publication is not None:
            _assert_no_invalid_chars(self.publication, "publication")

        self.tags = []
        self.set_tags(tags)

    def __eq__(self, other):
        if ((self.quote == other.quote)
                and (self.author == other.author)
                and (self.publication == other.publication)
                and (self.tags == other.tags)):
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
        if keyword in self.quote or \
                keyword in self.author or \
                keyword in self.publication or \
                self.has_tag(keyword):
            return True
        return False

    def set_tags(self, tags):
        if tags is None:
            self.tags = []
        else:
            if type(tags) is not list:
                raise click.ClickException("The quote object was not given a list for tags parameter.")
            self.tags = tags

    # Returns first 64 bits of MD5 hash for quote.  Since there is chance of hash collision,
    # should check if more than one quote matches hash.
    def get_hash(self):
        m = hashlib.md5()
        m.update(self.quote.encode('utf-8'))
        return m.hexdigest()[0:16]


def read_quotes(filename):
    """Given a path to quote file, this function returns a list of Quote objects containing
    the quotes.
    """

    if not os.path.exists(filename):
        raise click.ClickException("The quote file '{0}' was not found.".format(filename))

    with click.open_file(filename, mode='r', encoding='utf-8') as infile:
        quotes = parse_quotes(infile, filename, simple_format=False)

    _check_for_duplicates(quotes, filename)

    return quotes


def read_tags(quotefile):
    """Returns a list of all unique tags in use in the given quote file."""

    alltags = set()
    quotes = read_quotes(quotefile)
    for quote in quotes:
        for tag in quote.tags:
            alltags.add(tag)

    return sorted(list(alltags))


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
        if line == "":
            continue

        # Skip lines beginning with '#' (comments)
        if line.startswith("#"):
            continue

        try:
            quote = _parse_quote(line, simple_format=simple_format)
            quotes.append(quote)
        except Exception as exception:
            raise click.ClickException("syntax error on line {0} of {1}: {2}.  Line with error: "
                                       "\"{3}\"".format(str(linenum), filename, str(exception), line))

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
        raise click.ClickException("a quote was not found")

    if len(author) == 0:
        raise click.ClickException("an author was not included with the quote.  "
                                   + "Expecting quote in the format \"<quote> - <author>\".")

    quote = Quote(quotestring, author, publication, tags)
    return quote


def _parse_quote_simple(line):
    """Internal function to parse a single quote line in simple format."""
    if any(c == '|' for c in line):
        raise click.ClickException("the quote included an embedded pipe character (|)")

    # Get a list of matchers for hyphens next to and not next to a space char
    hyphen_w_period = list(re.finditer("(?<=\\.)\\s*[-]\\s*", line))
    hyphen_w_space = list(re.finditer("\\s+-\\s*|\\s*-\\s+", line))
    hyphen_wo_space = list(re.finditer("(?<=[^ ])-(?=[^ ])", line))

    # Based on hyphens found, infer which one separates quote from author.
    if len(hyphen_w_period) == 1:
        selected_matcher = hyphen_w_period[0]
    elif len(hyphen_w_space) == 1:
        selected_matcher = hyphen_w_space[0]
    elif len(hyphen_w_space) == 0 and len(hyphen_wo_space) == 1:
        selected_matcher = hyphen_wo_space[0]
    else:
        raise click.ClickException(
            "unable to determine which hyphen separates the quote from the author.")

    quote = line[:selected_matcher.start()]
    author = line[selected_matcher.end():]

    # Check if publication exists using parentheses
    regexes = [
        "^([^,]+)\\s*\\((.*)\\)$",  # Author name (publication)
        "^([^,]+),\\s*[(](.+)[)]$",  # Author name, (publication)
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
            "unable to parse the author and publication.  Try 'Quote - Author (Publication)', or 'Quote - Author, Publication'")

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
    """Public function that parses tags and returns list of tags.
    """

    return _parse_tags(tag_string)


def _parse_tags(tag_string):
    """An internal function to parse tags, its error messages are not complete sentence."""
    rawtags = tag_string.split(',')
    tagset = set()
    for rawtag in rawtags:
        tag = rawtag.strip()
        if not all(c in ascii_letters + '0123456789_' for c in tag):
            raise click.ClickException("invalid tag '{0}': only numbers, letters, and commas are "
                                       "allowed in tags".format(tag))
        if tag != "":
            tagset.add(tag)

    return sorted(list(tagset))


def get_config():
    """This function reads the file ~/.jotquote/settings.conf and returns a
    ConfigParser object containing the settings.  If settings.conf
    does not yet exist, a file containing default settings is created.
    """

    if not os.path.exists(CONFIG_FILE):
        # Create config directory ~/.jotquote if it does not exist
        config_dir = os.path.join(os.path.expanduser('~'), '.jotquote')
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)

        # Create settings.conf within ~/.jotquote
        quote_file = os.path.join(config_dir, 'quotes.txt')
        config = ConfigParser()
        config.add_section(APP_NAME)
        config[APP_NAME]['quote_file'] = quote_file
        config[APP_NAME]['line_separator'] = 'platform'
        config[APP_NAME]['web_port'] = '5544'
        config[APP_NAME]['web_ip'] = '127.0.0.1'
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

        # Create a default, empty quote file
        if not os.path.exists(quote_file):
            template_quote_file = os.path.normpath(os.path.join(__file__, '../templates/quotes.txt'))
            shutil.copyfile(template_quote_file, quote_file)

    config = ConfigParser()
    config.read(CONFIG_FILE)

    # If we made it here, the settings.conf file exists
    return config


def get_filename():
    """Convenience method to get the quote_file property from the
    settings.conf file and verify it exists."""
    config = get_config()
    filename = config.get(APP_NAME, 'quote_file')
    if not os.path.exists(filename):
        raise click.ClickException("The quote file specified in settings.conf, '{}', was not found.".format(filename))
    return filename


def add_quote(filename, quote):
    """Rewrites the quote file with given file name, adding the given new quote.
    Returns total number of quotes including new quote.
    """
    if not isinstance(quote, Quote):
        raise click.ClickException("The quote parameter must be type class Quote.")

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

    if not type(newquotes) is list:
        raise Exception("the add_quotes() function expected a list as second parameter.")

    # Check for duplicates within new quotes.  Exception raised if duplicate found within input lines.
    _check_for_duplicates(newquotes, "stdin")

    # Read in quotes from the quote file given.  Exception raised on I/O error
    quotes = read_quotes(filename)

    # Loop through existing quotes and check against new quotes for any duplicates
    for existing_quote in quotes:
        for new_quote in newquotes:
            if new_quote.quote == existing_quote.quote:
                raise click.ClickException(
                    "the quote \"{}\" is already in the quote file {}.".format(new_quote.quote, filename))

    # Rewrite quote file with any additional quotes
    quotes.extend(newquotes)
    write_quotes(filename, quotes)
    return len(quotes)


def write_quotes(quote_path, quotes):
    """Writes the given list of quotes to quote_path.

    Atomically overwrites quote_path with the quotes in the list.  If more than one
    process calls this function at the same time, the results are undefined.
    """
    if not os.path.exists(quote_path):
        raise click.ClickException("the quote file '{0}' was not found.".format(quote_path))

    config = get_config()
    linesep_property = config.get(APP_NAME, 'line_separator')
    if not linesep_property:
        newline = os.linesep
    elif linesep_property == 'unix':
        newline = '\n'
    elif linesep_property == 'windows':
        newline = '\r\n'
    elif linesep_property == 'platform':
        newline = os.linesep
    else:
        raise click.ClickException(
            "the value '{0}' is not valid value for the line_separator property."
            "  Valid values are 'platform', 'windows', or 'unix'.".format(linesep_property))

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

        # Sanity check backup size before overwriting backup
        if os.path.exists(backup_path):
            if os.path.getsize(backup_path) > os.path.getsize(temp_path):
                os.remove(temp_path)
                raise click.ClickException(
                    "the backup file '{0}' is larger than the quote file '{1}' would be after this operation.  "
                    "This is suspicious, the quote file was not modified.  If this was expected, "
                    "delete the backup file and try again.".format(backup_file, quote_file))

        # Create a backup (overwriting existing backup)
        shutil.copy(quote_path, backup_path)
    except click.ClickException:
        raise
    except:
        os.remove(temp_path)
        raise click.ClickException(
            "an error occurred writing the quotes.  The file '{0}' was not modified."
            .format(quote_path))

    # Replace original file with the new temp file.  The os.replace() function is
    # safest, but only available in Python 3.3 and later.
    try:
        if hasattr(os, 'replace'):
            os.replace(temp_path, quote_path)
        else:
            os.remove(quote_path)
            os.rename(temp_path, quote_path)
    except:
        raise click.ClickException("an error occurred writing the quotes.")


def format_quote(quote):
    """Given a Quote object, this function returns a single-line string containing the quote formatted as
    it will be written to the file: <quote> | <author> | [<publication>] | [<tag1>,<tag2>,...]
    """
    if not isinstance(quote, Quote):
        raise click.ClickException("The quote parameter must be type class Quote.")

    quotestr = quote.quote
    author = quote.author
    publication = quote.publication
    if publication is None:
        publication = ""
    tags = ", ".join(quote.tags)
    return "%s | %s | %s | %s" % (quotestr, author, publication, tags)


def get_random_choice(numquotes):
    """Return a random value between 0 and numquotes -1, inclusive."""

    # Get days since epoch
    endday = datetime.datetime.now().date()
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
            raise click.ClickException("a duplicate quote was found on line {} of '{}'.  "
                                       "Quote: \"{}\".".format(index + 1, source, quote.quote))


def _assert_does_not_contain(text, char, component_name):
    """Internal function to assert that text does not contain char.  If it does,
    an exception is raised from this function.
    """
    if any(c in char for c in text):
        _raise_invalid_char_exception(char, component_name)


def _assert_no_invalid_chars_quote(text, component_name):
    match = INVALID_CHARS_QUOTE.search(text)
    if match is not None:
        char = text[match.span()[0]:match.span()[1]]
        _raise_invalid_char_exception(char, component_name)


def _assert_no_invalid_chars(text, component_name):
    match = INVALID_CHARS.search(text)
    if match is not None:
        char = text[match.span()[0]:match.span()[1]]
        _raise_invalid_char_exception(char, component_name)


def _raise_invalid_char_exception(char, component_name):
    if char == '\n':
        charstring = "newline (0x0a)"
    elif char == '\r':
        charstring = "carriage return (0x0d)"
    else:
        charstring = "(" + char + ")"
    raise click.ClickException("the {} included a {} character".format(component_name, charstring))


if __name__ == '__main__':
    raise click.ClickException("This module is not executable.")
