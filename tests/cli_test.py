# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import os
import time
from unittest.mock import patch

import pytest
from click.testing import CliRunner

import tests.test_util
from jotquote import api
from jotquote import cli


def test_list(config, tmp_path):
    """The list subcommand should print quotes in simple format."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list'], obj={})

    assert result.exit_code == 0
    expected = "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.  - Linus Torvalds\n" + \
               "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall.  - Mitch Hedberg\n" + \
               "Ask for what you want and be prepared to get it.  - Maya Angelou\n" + \
               "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n"
    assert result.output == expected


def test_list_by_tag(config, tmp_path):
    """The list subcommand should return quotes with matching tag."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-t', 'funny'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 2


def test_list_by_tags(config, tmp_path):
    """The list subcommand should only return quotes matching multiple tags."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-t', 'hedberg,funny'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 1


def test_list_by_tags_none_found(config, tmp_path):
    """The list subcommand should return no quotes if none match tags."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-t', 'keillor,funny,bananas'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 0


def test_list_by_keyword(config, tmp_path):
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-k', 'danger'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 1


def test_list_by_keyword_none_found(config, tmp_path):
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-k', 'nonexistent'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 0


def test_list_by_number(config, tmp_path):
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-n', '3'], obj={})

    assert result.exit_code == 0
    assert result.output.strip() == "Ask for what you want and be prepared to get it.  - Maya Angelou"


def test_list_by_hash(config, tmp_path):
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '--hash', '763188b907212a72'], obj={})

    assert result.exit_code == 0
    assert result.output.strip() == "Ask for what you want and be prepared to get it.  - Maya Angelou"


def test_list_by_number_out_of_range(config, tmp_path):
    """The list subcommand should return error if number out of range."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-n', '7'], obj={})

    assert result.exit_code == 1
    assert result.output == 'Error: the number argument 7 is too large, there are only 4 quotes in the file.\n'


def test_list_by_invalid_number(config, tmp_path):
    """The list subcommand should fail if the -n option passed non-number"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-n', 'notanumber'], obj={})

    assert result.exit_code == 1
    expected = "Error: the value 'notanumber' is not a valid number, " + \
               "the -n option requires an integer line number.\n"
    assert result.output == expected


def test_list_invalid_tag(config, tmp_path):
    """The list subcommand shouldn't accept exclamation characters in tag."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-t', 'badtag!'], obj={})

    assert result.exit_code == 1
    assert result.output == "Error: invalid tag 'badtag!': only numbers, letters, and commas are allowed in tags\n"


def test_list_extended(config, tmp_path):
    """The list subcommand should accept -e option to display extended format."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '--hash', '763188b907212a72', '-e'], obj={})

    assert result.exit_code == 0
    assert result.output.strip() == "Ask for what you want and be prepared to get it. | Maya Angelou |  | life"


def test_list_extended_and_long(config, tmp_path):
    """The list subcommand should return error if both -e and -l options given."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['list', '-e', '-l'], obj={})

    assert result.exit_code == 1
    assert result.output == "Error: the 'extended' option and the 'long' option are mutually exclusive.\n"


def test_random(config, tmp_path):
    """Test that the random subcommand returns single line of output."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random'], obj={})

    assert result.exit_code == 0
    assert result.output.count('\n') == 1


def test_random_with_tags(config, tmp_path):
    """Test that the random subcommand returns single line of output."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random', '-t', 'franklin'], obj={})

    assert result.exit_code == 0
    assert result.output == 'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n'


def test_random_with_tags_nomatch(config, tmp_path):
    """Test that the random subcommand returns nothing if no matching tag"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes5.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random', '-t', 'book'], obj={})

    assert result.exit_code == 0
    assert result.output == ''


def test_random_with_keyword(config, tmp_path):
    """Test that the random subcommand returns something when keyword given"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes5.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random', '-k', 'Franklin'], obj={})

    assert result.exit_code == 0
    assert result.output == 'They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n'


def test_random_with_keyword_nomatch(config, tmp_path):
    """Test that the random subcommand returns nothing if keyword doesn't match"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes5.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['random', '-k', 'parakeet'], obj={})

    assert result.exit_code == 0
    assert result.output == ''


def test_add(config, tmp_path):
    """Test the add subcommand works with normal arguments"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', ' We accept the love we think we deserve.-Stephen Chbosky'],
                           obj={})

    assert result.exit_code == 0
    assert result.output == '1 quote added for total of 5.\n'
    result = runner.invoke(cli.jotquote, ['list'], obj={})
    expected = "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.  - Linus Torvalds\n" + \
               "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall.  - Mitch Hedberg\n" + \
               "Ask for what you want and be prepared to get it.  - Maya Angelou\n" + \
               "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n" + \
               "We accept the love we think we deserve.  - Stephen Chbosky\n"
    assert result.output == expected


def test_add_when_quote_already_in_file(config, tmp_path):
    """The add subcommand should return error if quote is already in the quote file."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '  Ask for what you want and be prepared to get it.  - Maya Angelou'], obj={})

    assert result.exit_code == 1
    assert result.output == (
        "Error: the quote \"Ask for what you want and be prepared to get it.\" is already " +
        "in the quote file {0}.\n".format(path))


def test_add_stdin(config, tmp_path):
    """Test add subcommand with input from stdin"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes5.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '-'],
                           input='Ask for what you want and be prepared to get it.-Maya Angelou\n',
                           obj={})

    assert result.exit_code == 0
    assert result.output == "1 quote added for total of 2.\n"

    with open(path, "r") as modified_quotefile:
        returned = modified_quotefile.readlines()

    expected = ['They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n',
                'Ask for what you want and be prepared to get it. | Maya Angelou |  | \n']
    assert returned == expected


def test_add_with_no_author(config, tmp_path):
    """The add subcommand should return error if author not included with quote."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '  We accept the love we think we deserve.-'], obj={})

    assert result.exit_code == 1
    assert result.output == ("Error: unable to parse the author and publication.  "
        "Try 'Quote - Author (Publication)', or 'Quote - Author, Publication'\n")


def test_add_with_publication(config, tmp_path):
    """The add subcommand should accept a publication after author if provided in parentheses."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote,
                           ['add', '  We accept the love we think we deserve.-Stephen Chbosky (Publication)'],
                           obj={})

    assert result.exit_code == 0
    assert result.output.strip() == '1 quote added for total of 5.'
    result = runner.invoke(cli.jotquote, ['list', '-n', '5', '-l'], obj={})
    expected = "5: We accept the love we think we deserve.\n" + \
               "    author: Stephen Chbosky\n" + \
               "    publication: Publication\n" + \
               "    tags: \n" + \
               "    hash: 53e070059e1c14f7\n"
    assert result.output == expected


def test_bulk_add_from_stdin(config, tmp_path):
    """Test add of multiple quotes from stdin"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes5.txt")
    config[api.APP_NAME]['quote_file'] = path
    stdin_input = "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it. - Linus Torvalds" + os.linesep + \
                  "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. - Mitch Hedberg" + os.linesep + \
                  "Ask for what you want and be prepared to get it. - Maya Angelou" + os.linesep

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '-'], input=stdin_input, obj={})

    assert result.exit_code == 0
    assert result.output == '3 quotes added for total of 4.\n'
    expected = "1: They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.\n" + \
               "    author: Ben Franklin\n" + \
               "    publication: \n" + \
               "    tags: U\n" + \
               "    hash: 25382c2519fb23bd\n" + \
               "2: The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.\n" + \
               "    author: Linus Torvalds\n" + \
               "    publication: \n" + \
               "    tags: \n" + \
               "    hash: bbfc7839cd5c3559\n" + \
               "3: The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall.\n" + \
               "    author: Mitch Hedberg\n" + \
               "    publication: \n" + \
               "    tags: \n" + \
               "    hash: 3002f948f63dad3d\n" + \
               "4: Ask for what you want and be prepared to get it.\n" + \
               "    author: Maya Angelou\n" + \
               "    publication: \n" + \
               "    tags: \n" + \
               "    hash: 763188b907212a72\n"
    result = runner.invoke(cli.jotquote, ['list', '-l'], obj={})
    assert result.exit_code == 0
    assert result.output == expected


def test_add_extended_format(config, tmp_path):
    """The add subcommand with -e option should allow extended format to be passed."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes5.txt")
    config[api.APP_NAME]['quote_file'] = path
    test_input = 'Ask for what you want and be prepared to get it. | Maya Angelou |  | \n'

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '-e', '-'], input=test_input, obj={})

    assert result.exit_code == 0
    assert result.output == "1 quote added for total of 2.\n"

    with open(path, "r") as modified_quotefile:
        returned = modified_quotefile.readlines()

    expected = ['They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n',
                'Ask for what you want and be prepared to get it. | Maya Angelou |  | \n']
    assert returned == expected


def test_add_extended_format_with_error(config, tmp_path):
    """Test add subcommand with extended format, error case"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes5.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', '-e', '-'], input='This is not properly formatted', obj={})

    assert result.exit_code == 1
    expected = "Error: syntax error on line 1 of stdin: did not find 3 '|' characters.  " + \
               "Line with error: \"This is not properly formatted\"\n"
    assert result.output == expected

    with open(path, "r") as modified_quotefile:
        returned = modified_quotefile.readlines()
    expected = ['They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.|Ben Franklin||U\n']
    assert returned == expected


def test_showalltags(config, tmp_path):
    """Test showalltags subcommand"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['showalltags'], obj={})

    assert result.exit_code == 0
    assert result.output == "franklin\nfreedom\nfunny\nhedberg\nlife\n"


def test_missing_subcommand(config, tmp_path):
    """A random quote should be displayed if no subcommand."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes5.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, [], obj={})

    assert result.exit_code == 0
    assert result.output == "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n"


def test_codepage_conversion(config, tmp_path):
    """Characters in non-standard codepage should round trip OK to file and back."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['add', 'δηψ.-Greek Author'], obj={})

    assert result.exit_code == 0
    with open(path, 'rb') as quotefile:
        data = quotefile.read()
    text_data = data.decode('utf-8')
    expected = \
        "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. " \
        "Yes, that's it. | Linus Torvalds |  | funny" + os.linesep + \
        "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. | Mitch Hedberg |  | funny, hedberg" + os.linesep + \
        "Ask for what you want and be prepared to get it. " \
        "| Maya Angelou |  | life" + os.linesep + \
        "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | franklin, freedom" + os.linesep + \
        "δηψ. | Greek Author |  | " + os.linesep
    assert text_data == expected


@patch('jotquote.web.run_server')
def test_webserver(mock_run_server, config, tmp_path):
    """Test webserver subcommand calls web.run_server"""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes2.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['webserver'], obj={})

    assert result.exit_code == 0
    assert mock_run_server.called


def test_settags(config, tmp_path):
    """The settags subcommand should modify tags on given quote."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['settags', '-s', '763188b907212a72', 'tag1,tag2'], obj={})

    assert result.exit_code == 0
    assert result.output == ""

    with open(path, "r") as modified_quotefile:
        returned = modified_quotefile.readlines()

    expected = [
        "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it. | Linus Torvalds |  | U\n",
        "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. | Mitch Hedberg |  | U\n",
        "Ask for what you want and be prepared to get it. | Maya Angelou |  | tag1, tag2\n",
        "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n"]
    assert returned == expected


def test_settags_invalid_args(config, tmp_path):
    """The settags subcommand should display error if both -s and -n given."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['settags', '-s', 'abcdef', '-n', '1', 'tag1,tag2'], obj={})

    assert result.exit_code == 1
    assert result.output == "Error: both the -s and -n option were included, but only one allowed.\n"


@patch('jotquote.api.CONFIG_FILE', '/fake/config/file.conf')
def test_jotquote_info(config, tmp_path):
    """The info subcommand should show path to config file, path to quote file, and number of quotes."""
    path = tests.test_util.init_quotefile(str(tmp_path), "quotes1.txt")
    config[api.APP_NAME]['quote_file'] = path

    runner = CliRunner()
    result = runner.invoke(cli.jotquote, ['info'], obj={})

    assert result.exit_code == 0
    import jotquote
    assert result.output == (
        "Version: {}\n"
        "Settings file: /fake/config/file.conf\n"
        "Quote file: {}\n"
        "Number of quotes: 4\n"
        "Time quote file last modified: {}\n".format(jotquote.__version__, path, time.ctime(os.path.getmtime(path))))
