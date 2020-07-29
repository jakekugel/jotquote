# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil
import tempfile
import time
import unittest
from configparser import ConfigParser

import mock
from click.testing import CliRunner
from mock import patch

import tests.test_util
from jotquote import api
from jotquote import cli


class TestQuoteCli(unittest.TestCase):
    """This test class contains tests that work at the CLI level, so they
    can be considered end-to-end tests.  These should not be as numerous as
    the tests in api_test.py module.
    """

    @classmethod
    def setUpClass(cls):
        # Add the src directory to PYTHONPATH variable.  This allows CLI to find
        # the development version of jotquote package.  Global class attributes set
        # here can be accessed from self, who knew?
        cls.my_env = os.environ.copy()
        cls.my_env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), '..', 'src')

    def setUp(self):
        # Create a temporary directory for use by the current unit test
        self.tempdir = tempfile.mkdtemp(prefix='jotquote.unittest.')

        # Create a test ConfigParser object
        self.config = ConfigParser()
        self.config.add_section('jotquote')
        self.config[api.APP_NAME]['quote_file'] = 'notset'
        self.config[api.APP_NAME]['line_separator'] = 'platform'
        self.config[api.APP_NAME]['web_port'] = '80'
        self.config[api.APP_NAME]['web_ip'] = '0.0.0.0'

        # Monkey-patch the api.get_config function to return our test ConfigParser
        self.origin_get_config = api.get_config
        api.get_config = mock.Mock(return_value=self.config)

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        api.get_config = self.origin_get_config

    def test_list(self):
        """The list subcommand should print quotes in simple format."""
        # Setup path to temporary file
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli with feature under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list'], obj={})

        # Check results
        assert result.exit_code == 0

        # Check results
        expected = "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.  - Linus Torvalds\n" + \
                   "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall.  - Mitch Hedberg\n" + \
                   "Ask for what you want and be prepared to get it.  - Maya Angelou\n" + \
                   "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n"
        self.assertEquals(expected, result.output)

    def test_list_by_tag(self):
        """The list subcommand should return quotes with matching tag."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-t', 'funny'], obj={})

        # Check 0 return code
        assert result.exit_code == 0

        # Check three quotes returned
        self.assertEquals(2, result.output.count('\n'))

    def test_list_by_tags(self):
        """The list subcommand should only return quotes matching multiple tags."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-t', 'hedberg,funny'], obj={})

        # Check 0 return code
        assert result.exit_code == 0

        # Check two quotes returned
        self.assertEquals(1, result.output.count('\n'))

    def test_list_by_tags_none_found(self):
        """The list subcommand should return no quotes if none match tags."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-t', 'keillor,funny,bananas'], obj={})

        # Check zero return code
        assert result.exit_code == 0

        # Check no quotes returned
        self.assertEquals(0, result.output.count('\n'))

    def test_list_by_keyword(self):
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-k', 'danger'], obj={})

        # Check results
        assert result.exit_code == 0
        # Check results
        self.assertEquals(1, result.output.count('\n'))

    def test_list_by_keyword_none_found(self):
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-k', 'nonexistent'], obj={})

        # Check results
        assert result.exit_code == 0
        # Check results
        self.assertEquals(0, result.output.count('\n'))

    def test_list_by_number(self):
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli with feature under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-n', '3'], obj={})

        # Check results
        assert result.exit_code == 0
        # Check results
        self.assertEquals("Ask for what you want and be prepared to get it.  - Maya Angelou",
                          result.output.strip())

    def test_list_by_hash(self):
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli with feature under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '--hash', '763188b907212a72'], obj={})

        # Check results
        assert result.exit_code == 0
        # Check results
        self.assertEquals("Ask for what you want and be prepared to get it.  - Maya Angelou",
                          result.output.strip())

    def test_list_by_number_out_of_range(self):
        """The list subcommand should return error if number out of range."""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call list subcommand of cli, passing arguments by mocking sys.argv
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-n', '7'], obj={})

        assert result.exit_code == 1

        self.assertEquals('Error: the number argument 7 is too large, there are only '
                          '4 quotes in the file.\n', result.output)

    def test_list_by_invalid_number(self):
        """The list subcommand should fail if the -n option passed non-number"""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path
        output = ''

        # Call list subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-n', 'notanumber'], obj={})

        assert result.exit_code == 1

        # Verify results
        expected = "Error: the value 'notanumber' is not a valid number, " + \
                   "the -n option requires an integer line number.\n"
        self.assertEquals(expected, result.output)

    def test_list_invalid_tag(self):
        """The list subcommand shouldn't accept exclamation characters in tag."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-t', 'badtag!'], obj={})

        # Verify results
        assert result.exit_code == 1
        self.assertEquals("Error: invalid tag 'badtag!': only numbers, letters, and commas are allowed in tags\n",
                          result.output)

    def test_list_extended(self):
        """The list subcommand should accept -e option to display extended format."""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli with feature under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '--hash', '763188b907212a72', '-e'], obj={})

        # Check results
        assert result.exit_code == 0
        # Check results
        self.assertEquals(
            "Ask for what you want and be prepared to get it. | Maya Angelou |  | life",
            result.output.strip())

    def test_list_extended_and_long(self):
        """The list subcommand should return error if both -e and -l options given."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli with feature under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-e', '-l'], obj={})

        # Check results
        assert result.exit_code == 1
        # Check results
        self.assertEquals("Error: the 'extended' option and the 'long' option are mutually exclusive.\n",
                          result.output)

    def test_random(self):
        """Test that the random subcommand returns single line of output."""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call random subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['random'], obj={})

        # Check results
        # Check results
        assert result.exit_code == 0

        # Confirm a single result returned.
        self.assertEquals(1, result.output.count('\n'))

    def test_random_with_tags(self):
        """Test that the random subcommand returns single line of output."""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call random subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['random', '-t', 'franklin'], obj={})

        # Check results
        assert result.exit_code == 0

        # Confirm a single line of output was returned.
        self.assertEquals('They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n', result.output)

    def test_random_with_tags_nomatch(self):
        """Test that the random subcommand returns nothing if no matching tag"""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call random subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['random', '-t', 'book'], obj={})

        # Check results
        assert result.exit_code == 0

        # Confirm no output.
        self.assertEquals('', result.output)

    def test_random_with_keyword(self):
        """Test that the random subcommand returns something when keyword given"""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call random subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['random', '-k', 'Franklin'], obj={})

        # Check results
        assert result.exit_code == 0
        # Confirm no output.
        self.assertEquals('They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n', result.output)

    def test_random_with_keyword_nomatch(self):
        """Test that the random subcommand returns nothing if keyword doesn't match"""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call random subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['random', '-k', 'parakeet'], obj={})

        # Check results
        assert result.exit_code == 0
        # Confirm no output.
        self.assertEquals('', result.output)

    def test_add(self):
        """Test the add subcommand works with normal arguments"""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli, pass arguments by mocking sys.argv
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['add', ' We accept the love we think we deserve.-Stephen Chbosky'],
                               obj={})
        print(result.output)

        # Check results
        assert result.exit_code == 0
        self.assertEquals('1 quote added for total of 5.\n', result.output)
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list'], obj={})
        expected = "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.  - Linus Torvalds\n" + \
                   "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall.  - Mitch Hedberg\n" + \
                   "Ask for what you want and be prepared to get it.  - Maya Angelou\n" + \
                   "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n" + \
                   "We accept the love we think we deserve.  - Stephen Chbosky\n"
        self.assertEquals(expected, result.output)

    def test_add_when_quote_already_in_file(self):
        """The add subcommand should return error if quote is already in the quote file.
        """

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['add', '  Ask for what you want and be prepared to get it.  - Maya Angelou'], obj={})

        assert result.exit_code == 1
        print(result.output)
        self.assertEquals(
            "Error: the quote \"Ask for what you want and be prepared to get it.\" is already " +
            "in the quote file {0}.\n".format(path), result.output)

    def test_add_stdin(self):
        """Test add subcommand with input from stdin"""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Run command with add subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['add', '-'],
                               input='Ask for what you want and be prepared to get it.-Maya Angelou\n',
                               obj={})

        # Check results
        assert result.exit_code == 0
        # Check correct output on stdout
        self.assertEquals("1 quote added for total of 2.\n", result.output)

        # Check file modifications correct
        with open(path, "r") as modified_quotefile:
            returned = modified_quotefile.readlines()

        expected = ['They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n',
                    'Ask for what you want and be prepared to get it. | Maya Angelou |  | \n']
        self.assertEquals(expected, returned)

    def test_add_with_no_author(self):
        """The add subcommand should return error if author not included with quote."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call add subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['add', '  We accept the love we think we deserve.-'], obj={})

        assert result.exit_code == 1
        self.assertEquals("Error: unable to parse the author and publication.  "
            "Try 'Quote - Author (Publication)', or 'Quote - Author, Publication'\n", result.output)

    def test_add_with_publication(self):
        """The add subcommand should accept a publication after author if provided in parentheses."""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Run subcommand being tested
        runner = CliRunner()
        result = runner.invoke(cli.jotquote,
                               ['add', '  We accept the love we think we deserve.-Stephen Chbosky (Publication)'],
                               obj={})

        # Check results
        assert result.exit_code == 0
        # Check no output
        self.assertEquals('1 quote added for total of 5.', result.output.strip())
        # Check that quote added
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-n', '5', '-l'], obj={})
        expected = "5: We accept the love we think we deserve.\n" + \
                   "    author: Stephen Chbosky\n" + \
                   "    publication: Publication\n" + \
                   "    tags: \n" + \
                   "    hash: 53e070059e1c14f7\n"
        self.assertEquals(expected, result.output)

    def test_bulk_add_from_stdin(self):
        """Test add of multiple quotes from stdin"""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path
        input = "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it. - Linus Torvalds" + os.linesep + \
                "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. - Mitch Hedberg" + os.linesep + \
                "Ask for what you want and be prepared to get it. - Maya Angelou" + os.linesep

        # Exercise CLI add feature that is under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['add', '-'], input=input, obj={})

        # Check results
        assert result.exit_code == 0
        # Check correct output on stdout
        self.assertEquals('3 quotes added for total of 4.\n', result.output)
        # Check file modifications correct
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
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['list', '-l'], obj={})

        # Check zero return code
        assert result.exit_code == 0
        self.assertEquals(expected, result.output)

    def test_add_extended_format(self):
        """The add subcommand with -e option should allow extended format to be passed."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path
        test_input = 'Ask for what you want and be prepared to get it. | Maya Angelou |  | \n'

        # Exercise CLI add feature that is under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['add', '-e', '-'],
                               input=test_input, obj={})

        # Check zero return code
        print(result.output)
        assert result.exit_code == 0
        # Check correct output on stdout
        self.assertEquals("1 quote added for total of 2.\n", result.output)

        # Check file modifications correct
        with open(path, "r") as modified_quotefile:
            returned = modified_quotefile.readlines()

        expected = ['They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n',
                    'Ask for what you want and be prepared to get it. | Maya Angelou |  | \n']
        self.assertEquals(expected, returned)

    def test_add_extended_format_with_error(self):
        """Test add subcommand with extended format, error case"""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise add subcommand with -e
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['add', '-e', '-'], input='This is not properly formatted', obj={})

        # Check return code
        assert result.exit_code == 1
        # Check expected error message
        expected = "Error: syntax error on line 1 of stdin: did not find 3 '|' characters.  " + \
                   "Line with error: \"This is not properly formatted\"\n"
        self.assertEquals(expected, result.output)

        # Check file not modified
        with open(path, "r") as modified_quotefile:
            returned = modified_quotefile.readlines()
        expected = ['They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.|Ben Franklin||U\n']
        self.assertEquals(expected, returned)

    def test_showalltags(self):
        """Test showalltags subcommand"""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise showalltags subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['showalltags'], obj={})

        # Check return code
        assert result.exit_code == 0
        # Check correct output on stdout
        expected = "franklin\nfreedom\nfunny\nhedberg\nlife\n"
        self.assertEquals(expected, result.output)

    def test_missing_subcommand(self):
        """A random quote should be displayed if no subcommand."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call with no subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, [], obj={})

        # Check results
        assert result.exit_code == 0
        # Check correct output on stdout
        expected = "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.  - Ben Franklin\n"
        self.assertEquals(expected, result.output)

    def test_codepage_conversion(self):
        """Characters in non-standard codepage should round trip OK to file and back."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        quotestring = 'δηψ.-Greek Author'

        # Call cli, pass arguments by mocking sys.argv
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['add', quotestring], obj={})

        # Check results
        assert result.exit_code == 0
        # Check that quote added
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
        self.assertEquals(expected, text_data)

    @mock.patch('jotquote.web.main')
    def test_webserver(self, mock_main):
        """Test webserver subcommand calls web.main"""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise webserver subcommand
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['webserver'], obj={})

        # Check zero return code
        assert result.exit_code == 0
        self.assertTrue(mock_main.called)

    def test_settags(self):
        """The settags subcommand should modify tags on given quote."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise CLI add feature that is under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['settags', '-s', '763188b907212a72', 'tag1,tag2'], obj={})

        # Check zero return code
        print(result.output)
        assert result.exit_code == 0
        # Check correct output on stdout
        self.assertEquals("", result.output)

        # Check file modifications correct
        with open(path, "r") as modified_quotefile:
            returned = modified_quotefile.readlines()

        expected = [
            "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it. | Linus Torvalds |  | U\n",
            "The depressing thing about tennis is that no matter how good I get, I'll never be as good as a wall. | Mitch Hedberg |  | U\n",
            "Ask for what you want and be prepared to get it. | Maya Angelou |  | tag1, tag2\n",
            "They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety. | Ben Franklin |  | U\n"]
        self.assertEquals(expected, returned)

    def test_settags_invalid_args(self):
        """The settags subcommand should display error if both -s and -n given."""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise CLI add feature that is under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['settags', '-s', 'abcdef', '-n', '1', 'tag1,tag2'], obj={})

        # Check that an error message was displayed about invalid arguments
        assert result.exit_code == 1
        # Check expected error message
        expected = "Error: both the -s and -n option were included, but only one allowed.\n"
        self.assertEquals(expected, result.output)

    @patch('jotquote.api.CONFIG_FILE', '/fake/config/file.conf')
    def test_jotquote_info(self):
        """The info subcommand should show path to config file, path to quote file, and
        number of quotes.
        """

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise CLI add feature that is under test
        runner = CliRunner()
        result = runner.invoke(cli.jotquote, ['info'], obj={})

        # Check zero return code
        self.assertEquals(result.exit_code, 0)
        # Check correct output on stdout
        import jotquote
        self.assertEquals(
            "Version: {}\n"
            "Settings file: /fake/config/file.conf\n"
            "Quote file: {}\n"
            "Number of quotes: 4\n"
            "Time quote file last modified: {}\n".format(jotquote.__version__, path, time.ctime(os.path.getmtime(path))),
            result.output)

    # def test_random(self):
    #     """Manual test to ensure quotes randomly picked with even distribution."""

    #     # Setup
    #     path = os.path.join(self.tempdir, "large-file.txt")
    #     open(path, 'w').close()
    #     self.config[api.APP_NAME]['quote_file'] = path

    #     runner = CliRunner()

    #     for index in range(20):
    #         quotestring = '{0} - author'.format(str(index))
    #         result = runner.invoke(cli.jotquote, ['add', quotestring], obj={})
    #         if result.exit_code != 0:
    #             print(result.output)
    #             self.assertEqual(0, result.exit_code)

    #     mydict = {}
    #     for index in range(500):
    #         result = runner.invoke(cli.jotquote, ['random'], obj={})
    #         if result.exit_code != 0:
    #             print(result.output)
    #             self.assertEqual(0, result.exit_code)
    #         quotenum = int(result.output.split('-')[0])
    #         try:
    #             count = mydict[quotenum]
    #         except KeyError:
    #             count = 0
    #         count = count + 1
    #         mydict[quotenum] = count

    #     for index in range(20):
    #         try:
    #             count = mydict[index]
    #         except KeyError:
    #             count = 0
    #         print("{0}: {1}".format(str(index), count))

    #     self.assertEqual(1, 2)
