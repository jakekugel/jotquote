# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import hashlib
import os
import random as randomlib
import shutil

import click

from jotquote.api import config as _config
from jotquote.api.quote import Quote, _parse_quote


def read_quotes(filename):
    """Read all quotes from the given quote file.

    Args:
        filename (str): Path to the quote file to read.

    Returns:
        list[Quote]: The parsed quotes, in file order.

    Raises:
        click.ClickException: If the file does not exist, contains a duplicate
            quote, or has a malformed line.
    """
    quotes, _ = read_quotes_with_hash(filename)
    return quotes


def read_quotes_with_hash(filename):
    """Read quotes and compute the SHA-256 hash of the file in a single pass.

    Args:
        filename (str): Path to the quote file to read.

    Returns:
        tuple[list[Quote], str]: The parsed quotes and the hex SHA-256 digest
            of the file contents.

    Raises:
        click.ClickException: If the file does not exist, contains a duplicate
            quote, or has a malformed line.
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
    """Return a sorted list of every unique tag used in the given quote file.

    Args:
        quotefile (str): Path to the quote file to read.

    Returns:
        list[str]: Sorted list of unique tag strings.
    """

    alltags = set()
    quotes = read_quotes(quotefile)
    for quote in quotes:
        for tag in quote.tags:
            alltags.add(tag)

    return sorted(list(alltags))


def parse_quotes(rawlines, filename, encoding=None, simple_format=True):
    """Parse an iterable of raw lines into a list of :class:`Quote` objects.

    Blank lines and lines beginning with ``#`` are skipped.

    Args:
        rawlines (Iterable[str] | Iterable[bytes]): Iterable yielding quote
            lines.  If ``encoding`` is given, each line is decoded first.
        filename (str): File name used in error messages (does not need to be
            a real file path).
        encoding (str | None): If provided, decode each line with this
            encoding; otherwise the input is already ``str``.
        simple_format (bool): If ``True`` parse lines in the human-friendly
            hyphen format; if ``False`` parse the pipe-delimited quote-file
            format.

    Returns:
        list[Quote]: Parsed quotes with ``line_number`` set to the 1-based
            line number in ``rawlines``.

    Raises:
        click.ClickException: If a non-comment line cannot be parsed.
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


def settags(quotefile, n, hash, newtags):
    """Set tags on the quote identified by number (1-based) or hash.

    Exactly one of ``n`` or ``hash`` must be provided.

    Args:
        quotefile (str): Path to the quote file to edit.
        n (int | None): 1-based quote number, or ``None`` to select by hash.
        hash (str | None): 16-character MD5 hash prefix, or ``None`` to select
            by number.
        newtags (list[str]): New tags to assign to the quote.  Pass ``[]`` to
            clear all tags.

    Raises:
        click.ClickException: If neither or both of ``n`` / ``hash`` are
            provided, if ``n`` is out of range, if ``hash`` matches no quote,
            or if the file was modified concurrently.
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


def get_sha256(filename):
    """Return the SHA-256 hex digest of the given file.

    Args:
        filename (str): Path to the file to hash.

    Returns:
        str: The hex SHA-256 digest of the file contents.
    """
    h = hashlib.sha256()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def set_quote(quotefile, line_num, quote, sha256):
    """Replace the quote at ``line_num`` with the given :class:`Quote`.

    Reads the file, verifies the SHA-256 matches ``sha256`` (to detect
    concurrent modifications), replaces the quote at the matching line
    number, and writes the file atomically via :func:`write_quotes`.

    Args:
        quotefile (str): Path to the quote file to edit.
        line_num (int): 1-based line number of the quote to replace.
        quote (Quote): The new quote content.  Its line number is ignored.
        sha256 (str): Expected SHA-256 hex digest of the quote file.

    Raises:
        click.ClickException: If the checksum does not match or ``line_num``
            does not identify an existing quote.
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
    """Append a single quote to the given quote file.

    Args:
        filename (str): Path to the quote file to edit.
        quote (Quote): The quote to add.

    Returns:
        int: Total number of quotes in the file after the add.

    Raises:
        click.ClickException: If ``quote`` is not a :class:`Quote`, if the
            file does not exist, or if the quote is already present.
    """
    if not isinstance(quote, Quote):
        raise click.ClickException('The quote parameter must be type class Quote.')

    quotes = [quote]
    return add_quotes(filename, quotes)


def add_quotes(filename, newquotes):
    """Append a list of quotes to the given quote file.

    If more than one process calls this function on the same file at the
    same time, the results are undefined.

    Args:
        filename (str): Path to the quote file to edit.
        newquotes (list[Quote]): Quotes to append.

    Returns:
        int: Total number of quotes in the file after the append.

    Raises:
        click.ClickException: If the file does not exist, if any of the new
            quotes duplicates an existing quote, or if the file was modified
            by another process during the operation.
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
    """Atomically overwrite ``quote_path`` with the given quotes.

    If ``expected_sha256`` is provided, the current file's SHA-256 is
    verified to match it before writing.  If the file was modified by
    another process, the write is aborted.

    If more than one process calls this function on the same file at the
    same time, the results are undefined.

    Args:
        quote_path (str): Path to the quote file to overwrite.
        quotes (list[Quote]): The quotes to write.
        expected_sha256 (str | None): Expected SHA-256 hex digest of the
            quote file as it exists on disk.  When ``None`` (default), no
            concurrency check is performed.

    Raises:
        click.ClickException: If the file does not exist, the SHA-256 does
            not match, the backup sanity check fails, or an I/O error
            occurs during the write.
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
    """Format a :class:`Quote` as a single pipe-delimited line.

    The returned string is the exact representation written to the quote
    file: ``<quote> | <author> | [<publication>] | [<tag1>,<tag2>,...]``.

    Args:
        quote (Quote): The quote to format.

    Returns:
        str: A single line without a trailing newline.

    Raises:
        click.ClickException: If ``quote`` is not a :class:`Quote`.
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


def _get_newline():
    """Return the newline string based on the line_separator config property."""
    config, _ = _config.get_config()
    linesep_property = config.get(_config.SECTION_GENERAL, 'line_separator', fallback='platform')
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
