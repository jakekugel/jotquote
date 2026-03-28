# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
import time
from unittest.mock import patch

from click.testing import CliRunner

import tests.test_util
from jotquote import api, cli


def test_list(config, tmp_path):
    """The list subcommand should print quotes in simple format."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list'], obj={})

    assert result.exit_code == 0
    expected = (
        "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.  - Linus Torvalds\n"
        + "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall.  - Mitch Hedberg\n"
        + 'Ask for what you want and be prepared to get it.  - Maya Angelou\n'
        + 'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n'
    )
    assert result.output == expected


def test_list_by_tag(config, tmp_path):
    """The list subcommand should return quotes with matching tag."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-t', 'funny'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 2


def test_list_by_tags(config, tmp_path):
    """The list subcommand should only return quotes matching multiple tags."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-t', 'hedberg,funny'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 1


def test_list_by_tags_none_found(config, tmp_path):
    """The list subcommand should return no quotes if none match tags."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-t', 'keillor,funny,bananas'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 0


def test_list_by_keyword(config, tmp_path):
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-k', 'danger'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 1


def test_list_by_keyword_none_found(config, tmp_path):
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-k', 'nonexistent'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 0


def test_list_by_number(config, tmp_path):
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-n', '3'], obj={})

    assert result.exit_code == 0
    assert result.output.strip() == 'Ask for what you want and be prepared to get it.  - Maya Angelou'


def test_list_by_hash(config, tmp_path):
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '--hash', '763188b907212a72'], obj={})

    assert result.exit_code == 0
    assert result.output.strip() == 'Ask for what you want and be prepared to get it.  - Maya Angelou'


def test_list_by_number_out_of_range(config, tmp_path):
    """The list subcommand should return error if number out of range."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-n', '7'], obj={})

    assert result.exit_code == 1
    assert result.output == 'Error: the number argument 7 is too large, there are only 4 quotes in the file.\n'


def test_list_by_invalid_number(config, tmp_path):
    """The list subcommand should fail if the -n option passed non-number"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-n', 'notanumber'], obj={})

    assert result.exit_code == 1
    expected = (
        "Error: the value 'notanumber' is not a valid number, " + 'the -n option requires an integer line number.\n'
    )
    assert result.output == expected


def test_list_invalid_tag(config, tmp_path):
    """The list subcommand shouldn't accept exclamation characters in tag."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-t', 'badtag!'], obj={})

    assert result.exit_code == 1
    assert result.output == "Error: invalid tag 'badtag!': only numbers, letters, and commas are allowed in tags\n"


def test_list_extended(config, tmp_path):
    """The list subcommand should accept -e option to display extended format."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '--hash', '763188b907212a72', '-e'], obj={})

    assert result.exit_code == 0
    assert result.output.strip() == 'Ask for what you want and be prepared to get it. | Maya Angelou |  | life'


def test_list_extended_and_long(config, tmp_path):
    """The list subcommand should return error if both -e and -l options given."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-e', '-l'], obj={})

    assert result.exit_code == 1
    assert result.output == "Error: the 'extended' option and the 'long' option are mutually exclusive.\n"


def test_random(config, tmp_path):
    """Test that the random subcommand returns single line of output."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 1


def test_random_with_tags(config, tmp_path):
    """Test that the random subcommand returns single line of output."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random', '-t', 'franklin'], obj={})

    assert result.exit_code == 0
    assert (
        result.output
        == 'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n'
    )


def test_random_with_tags_nomatch(config, tmp_path):
    """Test that the random subcommand returns nothing if no matching tag"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random', '-t', 'book'], obj={})

    assert result.exit_code == 0
    assert result.output == ''


def test_random_with_keyword(config, tmp_path):
    """Test that the random subcommand returns something when keyword given"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random', '-k', 'Franklin'], obj={})

    assert result.exit_code == 0
    assert (
        result.output
        == 'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n'
    )


def test_random_with_keyword_nomatch(config, tmp_path):
    """Test that the random subcommand returns nothing if keyword doesn't match"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random', '-k', 'parakeet'], obj={})

    assert result.exit_code == 0
    assert result.output == ''


def test_add(config, tmp_path):
    """Test the add subcommand works with normal arguments"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(
        cli.jotquote, ['add', '--no-lint', ' We accept the love we think we deserve.-Stephen Chbosky'], obj={}
    )

    assert result.exit_code == 0
    assert result.output == '1 quote added for total of 5.\n'
    result = runner.invoke(cli.jotquote, ['list'], obj={})
    expected = (
        "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.  - Linus Torvalds\n"
        + "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall.  - Mitch Hedberg\n"
        + 'Ask for what you want and be prepared to get it.  - Maya Angelou\n'
        + 'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n'
        + 'We accept the love we think we deserve.  - Stephen Chbosky\n'
    )
    assert result.output == expected


def test_add_when_quote_already_in_file(config, tmp_path):
    """The add subcommand should return error if quote is already in the quote file."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(
        cli.jotquote, ['add', '--no-lint', '  Ask for what you want and be prepared to get it.  - Maya Angelou'], obj={}
    )

    assert result.exit_code == 1
    assert result.output == (
        'Error: the quote "Ask for what you want and be prepared to get it." is already '
        + 'in the quote file {0}.\n'.format(path)
    )


def test_add_stdin(config, tmp_path):
    """Test add subcommand with input from stdin"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(
        cli.jotquote,
        ['add', '--no-lint', '-'],
        input='Ask for what you want and be prepared to get it.-Maya Angelou\n',
        obj={},
    )

    assert result.exit_code == 0
    assert result.output == '1 quote added for total of 2.\n'

    with open(path, 'r') as modified_quotefile:
        returned = modified_quotefile.readlines()

    expected = [
        'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n',
        'Ask for what you want and be prepared to get it. | Maya Angelou |  | \n',
    ]
    assert returned == expected


def test_add_with_no_author(config, tmp_path):
    """The add subcommand should return error if author not included with quote."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '--no-lint', '  We accept the love we think we deserve.-'], obj={})

    assert result.exit_code == 1
    assert result.output == (
        'Error: unable to parse the author and publication.  '
        "Try 'Quote - Author (Publication)', or 'Quote - Author, Publication'\n"
    )


def test_add_with_publication(config, tmp_path):
    """The add subcommand should accept a publication after author if provided in parentheses."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(
        cli.jotquote,
        ['add', '--no-lint', '  We accept the love we think we deserve.-Stephen Chbosky (Publication)'],
        obj={},
    )

    assert result.exit_code == 0
    assert result.output.strip() == '1 quote added for total of 5.'
    result = runner.invoke(cli.jotquote, ['list', '-n', '5', '-l'], obj={})
    expected = (
        '5: We accept the love we think we deserve.\n'
        + '    author: Stephen Chbosky\n'
        + '    publication: Publication\n'
        + '    tags: \n'
        + '    hash: 53e070059e1c14f7\n'
    )
    assert result.output == expected


def test_bulk_add_from_stdin(config, tmp_path):
    """Test add of multiple quotes from stdin"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    config[api.APP_NAME]['quote_file'] = path
    stdin_input = (
        "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it. - Linus Torvalds"
        + os.linesep
        + "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. - Mitch Hedberg"
        + os.linesep
        + 'Ask for what you want and be prepared to get it. - Maya Angelou'
        + os.linesep
    )

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '--no-lint', '-'], input=stdin_input, obj={})

    assert result.exit_code == 0
    assert result.output == '3 quotes added for total of 4.\n'
    expected = (
        '1: They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.\n'
        + '    author: Ben Franklin\n'
        + '    publication: \n'
        + '    tags: U\n'
        + '    hash: 25382c2519fb23bd\n'
        + "2: The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.\n"
        + '    author: Linus Torvalds\n'
        + '    publication: \n'
        + '    tags: \n'
        + '    hash: bbfc7839cd5c3559\n'
        + "3: The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall.\n"
        + '    author: Mitch Hedberg\n'
        + '    publication: \n'
        + '    tags: \n'
        + '    hash: 3002f948f63dad3d\n'
        + '4: Ask for what you want and be prepared to get it.\n'
        + '    author: Maya Angelou\n'
        + '    publication: \n'
        + '    tags: \n'
        + '    hash: 763188b907212a72\n'
    )
    result = runner.invoke(cli.jotquote, ['list', '-l'], obj={})
    assert result.exit_code == 0
    assert result.output == expected


def test_add_extended_format(config, tmp_path):
    """The add subcommand with -e option should allow extended format to be passed."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    config[api.APP_NAME]['quote_file'] = path
    test_input = 'Ask for what you want and be prepared to get it. | Maya Angelou |  | \n'

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '--no-lint', '-e', '-'], input=test_input, obj={})

    assert result.exit_code == 0
    assert result.output == '1 quote added for total of 2.\n'

    with open(path, 'r') as modified_quotefile:
        returned = modified_quotefile.readlines()

    expected = [
        'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n',
        'Ask for what you want and be prepared to get it. | Maya Angelou |  | \n',
    ]
    assert returned == expected


def test_add_extended_format_with_error(config, tmp_path):
    """Test add subcommand with extended format, error case"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(
        cli.jotquote, ['add', '--no-lint', '-e', '-'], input='This is not properly formatted', obj={}
    )

    assert result.exit_code == 1
    expected = (
        "Error: syntax error on line 1 of stdin: did not find 3 '|' characters.  "
        + 'Line with error: "This is not properly formatted"\n'
    )
    assert result.output == expected

    with open(path, 'r') as modified_quotefile:
        returned = modified_quotefile.readlines()
    expected = [
        'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.|Ben Franklin||U\n'
    ]
    assert returned == expected


def test_showalltags(config, tmp_path):
    """Test showalltags subcommand"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['showalltags'], obj={})

    assert result.exit_code == 0
    assert result.output == 'franklin\nfreedom\nfunny\nhedberg\nlife\n'


def test_missing_subcommand(config, tmp_path):
    """A random quote should be displayed if no subcommand."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes5.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, [], obj={})

    assert result.exit_code == 0
    assert (
        result.output
        == 'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n'
    )


def test_codepage_conversion(config, tmp_path):
    """Characters in non-standard codepage should round trip OK to file and back."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '--no-lint', 'δηψ.-Greek Author'], obj={})

    assert result.exit_code == 0
    with open(path, 'rb') as quotefile:
        data = quotefile.read()
    text_data = data.decode('utf-8')
    expected = (
        "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. "
        "Yes, that's it. | Linus Torvalds |  | funny"
        + os.linesep
        + "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. | Mitch Hedberg |  | funny, hedberg"
        + os.linesep
        + 'Ask for what you want and be prepared to get it. '
        '| Maya Angelou |  | life'
        + os.linesep
        + 'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | franklin, freedom'
        + os.linesep
        + 'δηψ. | Greek Author |  | '
        + os.linesep
    )
    assert text_data == expected


@patch('jotquote.web.run_server')
def test_webserver(mock_run_server, config, tmp_path):
    """Test webserver subcommand calls web.run_server"""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['webserver'], obj={})

    assert result.exit_code == 0
    assert mock_run_server.called


def test_settags(config, tmp_path):
    """The settags subcommand should modify tags on given quote."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['settags', '-s', '763188b907212a72', 'tag1,tag2'], obj={})

    assert result.exit_code == 0
    assert result.output == ''

    with open(path, 'r') as modified_quotefile:
        returned = modified_quotefile.readlines()

    expected = [
        "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it. | Linus Torvalds |  | U\n",
        "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. | Mitch Hedberg |  | U\n",
        'Ask for what you want and be prepared to get it. | Maya Angelou |  | tag1, tag2\n',
        'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n',
    ]
    assert returned == expected


def test_settags_invalid_args(config, tmp_path):
    """The settags subcommand should display error if both -s and -n given."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['settags', '-s', 'abcdef', '-n', '1', 'tag1,tag2'], obj={})

    assert result.exit_code == 1
    assert result.output == 'Error: both the -s and -n option were included, but only one allowed.\n'


@patch('jotquote.api.CONFIG_FILE', '/fake/config/file.conf')
def test_jotquote_info(config, tmp_path):
    """The info subcommand should show path to config file, path to quote file, and number of quotes."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['info'], obj={})

    assert result.exit_code == 0
    import jotquote

    assert result.output == (
        'Version: {}\n'
        'Settings file: /fake/config/file.conf\n'
        'Quote file: {}\n'
        'Number of quotes: 4\n'
        'Time quote file last modified: {}\n'.format(jotquote.__version__, path, time.ctime(os.path.getmtime(path)))
    )


def test_show_author_count(config, tmp_path):
    """add subcommand prints author count when show_author_count=true."""
    config[api.APP_NAME]['show_author_count'] = 'true'
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '--no-lint', 'New wisdom quote - Ben Franklin'], obj={})

    assert result.exit_code == 0
    assert '1 quote added for total of 5.' in result.output
    assert 'You now have 2 quotes by Ben Franklin.' in result.output


def test_show_author_count_singular(config, tmp_path):
    """add subcommand uses singular 'quote' when author has exactly one quote."""
    config[api.APP_NAME]['show_author_count'] = 'true'
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '--no-lint', 'A brand new thought - New Author'], obj={})

    assert result.exit_code == 0
    assert 'You now have 1 quote by New Author.' in result.output


def test_show_author_count_disabled(config, tmp_path):
    """add subcommand does not print author count when show_author_count is not set."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '--no-lint', 'New wisdom quote - Ben Franklin'], obj={})

    assert result.exit_code == 0
    assert result.output == '1 quote added for total of 5.\n'


# ---------------------------------------------------------------------------
# lint subcommand
# ---------------------------------------------------------------------------


def test_lint_clean_file(config, tmp_path):
    """lint returns exit code 0 and 'No issues found.' when no checks are run."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    # Run with only ascii check to avoid spurious spelling/star/tag failures on fixture data
    result = runner.invoke(cli.jotquote, ['lint', '--select', 'ascii'], obj={})

    assert result.exit_code == 0
    assert 'No issues found.' in result.output


def test_lint_detects_issues(config, tmp_path):
    """lint reports issues and exits with code 1."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes9.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['lint', '--select', 'no-tags'], obj={})

    assert result.exit_code == 1
    assert 'issue' in result.output


def test_lint_select_and_ignore_mutually_exclusive(config, tmp_path):
    """lint raises error when both --select and --ignore are used."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['lint', '--select', 'ascii', '--ignore', 'spelling'], obj={})

    assert result.exit_code != 0
    assert 'mutually exclusive' in result.output


def test_lint_ignore(config, tmp_path):
    """lint --ignore skips the specified check."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['lint', '--select', 'ascii', '--ignore', 'spelling'], obj={})

    # Should fail due to mutual exclusion, so use a valid combo instead
    result = runner.invoke(
        cli.jotquote,
        ['lint', '--ignore', 'spelling,no-tags,author-antipatterns,multiple-stars,ascii,smart-quotes,no-author'],
        obj={},
    )

    assert result.exit_code == 0
    assert 'No issues found.' in result.output


def test_lint_unknown_check(config, tmp_path):
    """lint rejects unknown check names."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes2.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['lint', '--select', 'nonexistent-check'], obj={})

    assert result.exit_code != 0
    assert 'Unknown check' in result.output


def test_lint_fix_smart_quotes(config, tmp_path):
    """lint --fix replaces smart quotes in the quote file."""
    import shutil, os

    src = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')

    # Append a quote with a smart quote
    with open(src, 'a', encoding='utf-8') as f:
        f.write('\u201cSmart quote test\u201d | Test Author | | funny\n')

    config[api.APP_NAME]['quote_file'] = src

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['lint', '--select', 'smart-quotes', '--fix'], obj={})

    assert '1 fix applied.' in result.output or 'fix' in result.output
    # Verify file no longer has smart quotes
    content = open(src, encoding='utf-8').read()
    assert '\u201c' not in content
    assert '\u201d' not in content


# ---------------------------------------------------------------------------
# lint-on-add
# ---------------------------------------------------------------------------


def test_add_lint_warnings_shown_and_confirmed(config, tmp_path):
    """add shows lint warnings and adds quote when user confirms with 'y'."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path
    config[api.APP_NAME]['lint_on_add'] = 'true'

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '\u201cSmart quote test\u201d - Test Author'], input='y\n', obj={})

    assert result.exit_code == 0
    assert 'Warning:' in result.output
    assert '1 quote added' in result.output


def test_add_lint_warnings_declined(config, tmp_path):
    """add shows lint warnings and aborts when user declines with 'N'."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path
    config[api.APP_NAME]['lint_on_add'] = 'true'

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '\u201cSmart quote test\u201d - Test Author'], input='N\n', obj={})

    assert result.exit_code == 1
    assert 'Warning:' in result.output
    assert 'quote added' not in result.output


def test_add_lint_no_warnings_when_clean(config, tmp_path):
    """add does not show warnings or prompt when quote passes all checks."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path
    config[api.APP_NAME]['lint_enabled_checks'] = 'smart-quotes, smart-dashes, double-spaces'

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', 'A clean quote - Test Author'], obj={})

    assert result.exit_code == 0
    assert 'Warning:' not in result.output
    assert '1 quote added' in result.output


def test_add_lint_respects_enabled_checks(config, tmp_path):
    """add only runs checks listed in lint_enabled_checks."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path
    config[api.APP_NAME]['lint_enabled_checks'] = 'ascii'

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', 'A plain quote without tags - Test Author'], obj={})

    assert result.exit_code == 0
    assert 'Warning:' not in result.output
    assert '1 quote added' in result.output


def test_add_no_lint_flag_skips_checks(config, tmp_path):
    """add --no-lint skips lint checks entirely."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '--no-lint', '\u201cSmart quote test\u201d - Test Author'], obj={})

    assert result.exit_code == 0
    assert 'Warning:' not in result.output
    assert '1 quote added' in result.output


def test_add_lint_exception_propagates(config, tmp_path, monkeypatch):
    """Exceptions from lint_quotes propagate to the caller."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path
    config[api.APP_NAME]['lint_on_add'] = 'true'

    from jotquote import lint as lintmod

    monkeypatch.setattr(lintmod, 'lint_quotes', lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('boom')))

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', 'A plain quote - Test Author'], obj={})

    assert result.exit_code != 0


def test_add_lint_on_add_false_skips_checks(config, tmp_path):
    """add does not run lint checks when lint_on_add is false."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path
    config[api.APP_NAME]['lint_on_add'] = 'false'

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '\u201cSmart quote test\u201d - Test Author'], obj={})

    assert result.exit_code == 0
    assert 'Warning:' not in result.output
    assert '1 quote added' in result.output


def test_add_lint_on_add_true_runs_checks(config, tmp_path):
    """add runs lint checks when lint_on_add is true."""
    path = tests.test_util.init_quotefile(str(tmp_path), 'quotes1.txt')
    config[api.APP_NAME]['quote_file'] = path
    config[api.APP_NAME]['lint_on_add'] = 'true'

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '\u201cSmart quote test\u201d - Test Author'], input='y\n', obj={})

    assert result.exit_code == 0
    assert 'Warning:' in result.output
    assert '1 quote added' in result.output
