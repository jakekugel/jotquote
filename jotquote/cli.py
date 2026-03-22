# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
import random as randomlib
import sys
import time

import click

from jotquote import api

HELP_MAIN_F_ARG = 'optional path to quote file (if not provided, the command ' \
                  'will check ~/.jotquote/settings.conf for path)'

HELP_LIST_E_ARG = 'list the quotes using the same pipe-delimited format used in the quote file.'
HELP_LIST_S_ARG = 'list the quote with the matching hash value'
HELP_LIST_N_ARG = 'list the quote on the given line number'
HELP_LIST_L_ARG = 'list the quotes using long-form output which includes publication, tags, and hash in addition ' \
                  'to quote, author, and publication'
HELP_LIST_K_ARG = 'list the quotes the given keyword in quote, author, or publication'
HELP_LIST_T_ARG = 'list the quotes with the given tag will be displayed'

HELP_ADD_USAGE = 'jotquote add [-e] [ - | <quote> ]'
HELP_ADD_POS_ARG = 'this positional argument can either be a single dash indicating multiple ' \
                   'quotes should be read from stdin, or a quote in following ' \
                   'format: "<quote> - <author> [(publication)]", or "<quote> - <author> [\'publication\']"'
HELP_ADD_E_ARG = 'use the same pipe-delimited quote format that is used in the quote file: ' \
                 '"<quote>|<author>|[<publication>]|[<tag1>,<tag2>,...]"'

HELP_SHOWALLTAGS_USAGE = 'quote showalltags [-h]'

HELP_SETTAGS_USAGE = 'jotquote settags [-n <number> | -s <hash>] <new tags>'

HELP_SETTAGS_N_ARG = 'the quote with the given position in the text file should have its tags set'
HELP_SETTAGS_S_ARG = 'the quote with the given hash value in the text file should have its tags set'

HELP_RANDOM = 'display a single random quote, optionally selected from quotes matching criteria'
HELP_RANDOM_K_ARG = 'display a random quote with the given keyword in the quote, author, or publication'
HELP_RANDOM_T_ARG = 'display a random quote with the given tag'

HELP_TODAY_T_ARG = 'the quote must have the given tag'


@click.group(invoke_without_command=True)
@click.option('--quotefile', type=click.Path(exists=False), help=HELP_MAIN_F_ARG)
@click.version_option()
@click.pass_context
def jotquote(ctx, quotefile):
    """This command allows you to manage a collection of quotes contained in a text
    file; you can add, view, and tag quotes.  The command can also be used to start
    a simple web server to display a quote of the day.
    """
    config = api.get_config()

    # Get path to quote file
    if quotefile is None:
        quotefile = config.get(api.APP_NAME, 'quote_file')

        # All subcommands except webserver require quotefile to exist.  The
        # webserver subcommand lazy-loads when user views page.
        if ctx.invoked_subcommand not in ('webserver', 'quotemap') and not os.path.exists(quotefile):
            config_dir = click.get_app_dir(api.APP_NAME, roaming=True, force_posix=False)
            config_path = os.path.join(config_dir, 'settings.conf')
            print("The quote file '{0}' does not exist.  Either create an empty file with this name, or edit "
                  "the configuration file {1} and change the default_quote_file property to refer to a quote "
                  "file that exists.".format(quotefile, config_path))
            exit(1)

    # Save quotefile path into context so subcommands can use it
    ctx.obj['QUOTEFILE'] = quotefile

    if ctx.invoked_subcommand is None:
        _print_random(quotefile, None, None)


@jotquote.command()
@click.option('--extended', '-e', help=HELP_ADD_E_ARG, is_flag=True)
@click.argument('quote')  # , help=HELP_ADD_POS_ARG
@click.pass_context
def add(ctx, extended, quote):
    """add a new quote to the quote file.
    """
    quotefile = ctx.obj['QUOTEFILE']

    _add_quotes(quotefile, quote, extended)


@jotquote.command()
@click.option('--tags', '-t', help=HELP_LIST_T_ARG, multiple=False)
@click.option('--keyword', '-k', help=HELP_LIST_K_ARG, multiple=False)
@click.option('--long', '-l', help=HELP_LIST_L_ARG, is_flag=True)
@click.option('--number', '-n', help=HELP_LIST_N_ARG, multiple=True)
@click.option('--hash', '-s', help=HELP_LIST_S_ARG)
@click.option('--extended', '-e', help=HELP_LIST_E_ARG, is_flag=True)
@click.pass_context
def list(ctx, tags, keyword, long, number, hash, extended):
    """List all quotes in the text file meeting some criteria.
    """
    quotefile = ctx.obj['QUOTEFILE']

    # Some input validation
    if extended and long:
        raise click.ClickException("the 'extended' option and the 'long' option are mutually exclusive.")

    quotenum = _parse_number_arg(number)
    quotes = api.read_quotes(quotefile)
    selected_quotes = _select_quotes(quotes, tags=tags, keyword=keyword, number=quotenum, hash_arg=hash,
                                     rand=False)

    # Print each selected quote
    for index in selected_quotes:
        quote = quotes[index]
        if long:
            print_quote_long(quote, index + 1)
        elif extended:
            print_quote_extended(quote)
        else:
            print_quote_short(quote)


@jotquote.command()
@click.pass_context
def showalltags(ctx):
    """Show all tags used in the quote file.
    """
    quotefile = ctx.obj['QUOTEFILE']

    tags = api.read_tags(quotefile)
    for tag in tags:
        print(tag)


@jotquote.command()
@click.option('--number', '-n', help=HELP_SETTAGS_N_ARG)
@click.option('--hash', '-s', help=HELP_SETTAGS_S_ARG)
@click.argument('newtags')
@click.pass_context
def settags(ctx, number, hash, newtags):
    """Set new tags for a given quote, replacing any existing quotes.  The subcommand
    has one required argument, NEWTAGS, which is a comma-separated list of tags.
    """
    quotefile = ctx.obj['QUOTEFILE']
    quotenum = _parse_number_arg(number)
    tags = api.parse_tags(newtags)
    api.settags(quotefile, n=quotenum, hash=hash, newtags=tags)


@jotquote.command()
@click.pass_context
def webserver(ctx):
    """Start a web server to display quote of the day."""

    # Lazy import to avoid importing web packages when using pure cli
    import jotquote.web
    jotquote.web.run_server()


@jotquote.command()
@click.option('--tags', '-t', help=HELP_RANDOM_T_ARG)
@click.option('--keyword', '-k', help=HELP_RANDOM_K_ARG)
@click.pass_context
def random(ctx, tags, keyword):
    """Display a random quote.  By default any quote in the quote file may be
    shown, however the -t and -k options can be used to narrow the candidates
    to quotes with specific tag(s) or quotes containing a keyword, respectively."""
    quotefile = ctx.obj['QUOTEFILE']
    _print_random(quotefile, tags, keyword)


@jotquote.command()
@click.pass_context
def today(ctx):
    """Display a random quote, seeding the random number generator with the
    date to produce a random quote that remains the same on a given day.
    """
    quotefile = ctx.obj['QUOTEFILE']

    quotes = api.read_quotes(quotefile)

    if len(quotes) > 0:
        # Get random random quote based on date and number of quotes
        index = api.get_random_choice(len(quotes))
        quote = quotes[index]

        print_quote_short(quote)


@jotquote.command()
@click.pass_context
def info(ctx):
    """Show location of config file and quote file."""

    quotefile = ctx.obj['QUOTEFILE']

    # This import is required to read that package version below
    import jotquote

    print('Version: {}'.format(jotquote.__version__))
    print('Settings file: {}'.format(api.CONFIG_FILE))
    print('Quote file: {}'.format(quotefile))

    # The info subcommand should still work even if quote file not found.
    if os.path.exists(quotefile):
        quotes = api.read_quotes(quotefile)
        print('Number of quotes: {}'.format(str(len(quotes))))
        print('Time quote file last modified: {}'.format(time.ctime(os.path.getmtime(quotefile))))


@jotquote.group()
def quotemap():
    """Manage the quotemap file."""
    pass


@quotemap.command()
@click.argument('quotefile', type=click.Path(exists=True))
@click.argument('newquotemap', type=click.Path())
@click.option('--oldquotemap', type=click.Path(), default=None, help='Path to existing quotemap file to read from.')
@click.option('--days', default=3652, type=int, help='Number of days into the future to generate (default: 3652).')
def rebuild(quotefile, newquotemap, oldquotemap, days):
    """Rebuild a quotemap file for the given number of days.

    NEWQUOTEMAP is the path to write the rebuilt quotemap; must not already exist.
    """
    if oldquotemap and not os.path.exists(oldquotemap):
        raise click.ClickException("the quotemap file '{}' was not found.".format(oldquotemap))
    if os.path.exists(newquotemap):
        raise click.ClickException("the output file '{}' already exists.".format(newquotemap))
    api.rebuild_quotemap(quotefile, oldquotemap, newquotemap, days=days)


@jotquote.command()
@click.option('--fix', is_flag=True, help='Auto-fix issues that can be corrected safely.')
@click.option('--select', 'select_checks', default='', help='Comma-separated list of checks to run (disables all others).')
@click.option('--ignore', 'ignore_checks', default='', help='Comma-separated list of checks to skip.')
@click.option('--format', 'output_format', type=click.Choice(['text', 'json']), default='text', help='Output format.')
@click.option('--quiet', '-q', is_flag=True, help='Suppress per-issue output; only show summary.')
@click.pass_context
def lint(ctx, fix, select_checks, ignore_checks, output_format, quiet):
    """Check the quote file for quality issues."""
    import json as jsonmod

    from jotquote import lint as lintmod

    if select_checks and ignore_checks:
        raise click.ClickException('--select and --ignore are mutually exclusive.')

    quotefile = ctx.obj['QUOTEFILE']
    config = api.get_config()

    # Determine active check set
    all_checks = lintmod.ALL_CHECKS
    if select_checks:
        checks = {c.strip() for c in select_checks.split(',') if c.strip()}
        invalid = checks - all_checks
        if invalid:
            raise click.ClickException('Unknown check(s): {}'.format(', '.join(sorted(invalid))))
    elif ignore_checks:
        ignore = {c.strip() for c in ignore_checks.split(',') if c.strip()}
        invalid = ignore - all_checks
        if invalid:
            raise click.ClickException('Unknown check(s): {}'.format(', '.join(sorted(invalid))))
        checks = all_checks - ignore
    else:
        raw = config.get('jotquote.lint', 'enabled_checks', fallback='')
        checks = {c.strip() for c in raw.split(',') if c.strip()} if raw.strip() else all_checks

    quotes = api.read_quotes(quotefile)
    issues = lintmod.lint_quotes(quotes, checks, config)

    fix_count = 0
    if fix:
        quotes, fix_count = lintmod.apply_fixes(quotes, issues)
        if fix_count > 0:
            api.write_quotes(quotefile, quotes)
            quotes = api.read_quotes(quotefile)
            issues = lintmod.lint_quotes(quotes, checks, config)

    if output_format == 'json':
        result = [
            {
                'line': i.line_number,
                'check': i.check,
                'field': i.field,
                'message': i.message,
                'fixable': i.fixable,
            }
            for i in issues
        ]
        click.echo(jsonmod.dumps(result, indent=2))
    else:
        if not quiet:
            for issue in issues:
                fixable_str = ' (fixable)' if issue.fixable else ''
                click.echo('line {}: [{}] {}{}'.format(issue.line_number, issue.check, issue.message, fixable_str))
        issue_count = len(issues)
        if fix and fix_count > 0:
            click.echo('{} fix{} applied.'.format(fix_count, 'es' if fix_count != 1 else ''))
        if issue_count == 0:
            click.echo('No issues found.')
        else:
            click.echo('{} issue{} found.'.format(issue_count, 's' if issue_count != 1 else ''))

    sys.exit(1 if issues else 0)


def _add_quotes(quotefile, newquote_str, extended):
    """Adds the new quote(s) to the quote file."""

    if newquote_str == '-':
        if not extended:
            quotes = api.parse_quotes(sys.stdin, 'stdin', simple_format=True)
        else:
            quotes = api.parse_quotes(sys.stdin, 'stdin', simple_format=False)

        total_count = api.add_quotes(quotefile, quotes)
        new_count = len(quotes)
    else:
        # Parse quote and rewrite quote file with new quote.
        if not extended:
            quote = api.parse_quote(newquote_str, simple_format=True)
        else:
            quote = api.parse_quote(newquote_str, simple_format=False)

        total_count = api.add_quote(quotefile, quote)
        new_count = 1

    if new_count == 1:
        print('{0} quote added for total of {1}.'.format(str(new_count), str(total_count)))
        config = api.get_config()
        if config[api.APP_NAME].getboolean('show_author_count', fallback=False):
            all_quotes = api.read_quotes(quotefile)
            count = sum(1 for q in all_quotes if q.author == quote.author)
            print('You now have {0} quote{1} by {2}.'.format(count, '' if count == 1 else 's', quote.author))
    else:
        print('{0} quotes added for total of {1}.'.format(str(new_count), str(total_count)))


def _print_random(quotefile, tags, keyword):
    """Given path to quote file, prints a random quote that optionally meets
    given tags and keyword.
    """
    quotes = api.read_quotes(quotefile)

    if len(quotes) > 0:
        selected = _select_quotes(quotes, tags=tags, keyword=keyword, rand=True)

        # Zero or one will be returned when rand=True
        if len(selected) == 1:
            quote = quotes[selected[0]]
            print_quote_short(quote)


def print_quote_short(quote):
    publication = quote.publication
    if publication is not None and publication != '':
        pubstring = ' (' + publication + ')'
    else:
        pubstring = ''
    print('{0}  - {1}{2}'.format(quote.quote, quote.author, pubstring))


def print_quote_long(quote, quotenum):
    print('{0}: {1}'.format(str(quotenum), quote.quote))
    print('    author: {0}'.format(quote.author))
    print('    publication: {0}'.format(quote.publication))
    print('    tags: {0}'.format(', '.join(quote.tags)))
    print('    hash: {0}'.format(quote.get_hash()))


def print_quote_extended(quote):
    """Print the quote in the same format as used in the quote file."""
    print(api.format_quote(quote))


def _parse_number_arg(number):
    if number is None:
        return None

    if len(number) == 0:
        return None

    if number[0].isdigit():
        return int(number[0])
    else:
        raise click.ClickException("the value '{}' is not a valid number, the -n option "
                                   "requires an integer line number.".format(number[0]))


def _select_quotes(quotes, tags=None, keyword=None, number=None, hash_arg=None, rand=False):
    """Given a list of Quote objects and crtieria, returns a list containing
    index numbers to list items that meet criteria.
    """

    # Validate the number argument is within range
    if number is not None:
        if number > len(quotes):
            raise click.ClickException('the number argument {0} is too large, there are only '
                                       '{1} quotes in the file.'.format(str(number), str(len(quotes))))
    taglist = []
    if tags is not None:
        taglist = api.parse_tags(tags)

    # Get quotes that meet all criteria
    selected_quotes = []
    for index in range(0, len(quotes)):
        quote = quotes[index]
        if ((keyword is None or quote.has_keyword(keyword))
                and (tags is None or quote.has_tags(taglist))
                and (number is None or number == index + 1)
                and (hash_arg is None or hash_arg == quote.get_hash())):
            selected_quotes.append(index)

    # If there is a hash collision (unlikely), show an error.
    if hash_arg is not None and len(selected_quotes) > 1:
        raise click.ClickException("a hash collision occurred, more than one quote in the quote file matches hash '{}'.".format(hash_arg))

    # If random argument given, choose single quote from selected quotes
    if rand and len(selected_quotes) > 0:
        randomlib.seed()
        random_quote = randomlib.choice(selected_quotes)
        selected_quotes = [random_quote]

    return selected_quotes


def main():
    return jotquote(obj={})


if __name__ == '__main__':
    main()
