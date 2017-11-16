# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil
import tempfile
import unittest
from configparser import ConfigParser

import mock
from click.testing import CliRunner
from mock import patch

import tests.test_util
from popquote import api
from popquote import cli


class TestQuoteCli(unittest.TestCase):
    """This test class contains tests that work at the CLI level, so they
    can be considered end-to-end tests.  These should not be as numerous as
    the tests in api_test.py module.
    """

    @classmethod
    def setUpClass(cls):
        # Add the src directory to PYTHONPATH variable.  This allows CLI to find
        # the development version of popquote package.  Global class attributes set
        # here can be accessed from self, who knew?
        cls.my_env = os.environ.copy()
        cls.my_env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), '..', 'src')

    def setUp(self):
        # Create a temporary directory for use by the current unit test
        self.tempdir = tempfile.mkdtemp(prefix='popquote.unittest.')

        # Create a test ConfigParser object
        self.config = ConfigParser()
        self.config.add_section('popquote')
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
        result = runner.invoke(cli.popquote, ['list'], obj={})

        # Check results
        assert result.exit_code == 0

        # Check results
        expected = "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.  - Linus Torvalds\n" + \
                   "God writes a lot of comedy... the trouble is, he's stuck with so many bad actors who don't know how to play funny.  - Garrison Keillor\n" + \
                   "I believe in looking reality straight in the eye and denying it.  - Garrison Keillor\n" + \
                   "A book is a gift you can open again and again.  - Garrison Keillor\n"
        self.assertEquals(expected, result.output)

    def test_list_by_tag(self):
        """The list subcommand should return quotes with matching tag."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli under test
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['list', '-t', 'funny'], obj={})

        # Check 0 return code
        assert result.exit_code == 0

        # Check three quotes returned
        self.assertEquals(3, result.output.count('\n'))

    def test_list_by_tags(self):
        """The list subcommand should only return quotes matching multiple tags."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli under test
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['list', '-t', 'keillor,funny'], obj={})

        # Check 0 return code
        assert result.exit_code == 0

        # Check two quotes returned
        self.assertEquals(2, result.output.count('\n'))

    def test_list_by_tags_none_found(self):
        """The list subcommand should return no quotes if none match tags."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli under test
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['list', '-t', 'keillor,funny,bananas'], obj={})

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
        result = runner.invoke(cli.popquote, ['list', '-k', 'danger'], obj={})

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
        result = runner.invoke(cli.popquote, ['list', '-k', 'nonexistent'], obj={})

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
        result = runner.invoke(cli.popquote, ['list', '-n', '3'], obj={})

        # Check results
        assert result.exit_code == 0
        # Check results
        self.assertEquals("I believe in looking reality straight in the eye and denying it.  - Garrison Keillor",
                          result.output.strip())

    def test_list_by_hash(self):
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli with feature under test
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['list', '--hash', 'd81db3b61c3ab418'], obj={})

        # Check results
        assert result.exit_code == 0
        # Check results
        self.assertEquals("I believe in looking reality straight in the eye and denying it.  - Garrison Keillor",
                          result.output.strip())

    def test_list_by_number_out_of_range(self):
        """The list subcommand should return error if number out of range."""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call list subcommand of cli, passing arguments by mocking sys.argv
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['list', '-n', '7'], obj={})

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
        result = runner.invoke(cli.popquote, ['list', '-n', 'notanumber'], obj={})

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
        result = runner.invoke(cli.popquote, ['list', '-t', 'badtag!'], obj={})

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
        result = runner.invoke(cli.popquote, ['list', '--hash', 'd81db3b61c3ab418', '-e'], obj={})

        # Check results
        assert result.exit_code == 0
        # Check results
        self.assertEquals(
            "I believe in looking reality straight in the eye and denying it. | Garrison Keillor |  | funny, keillor",
            result.output.strip())

    def test_list_extended_and_long(self):
        """The list subcommand should return error if both -e and -l options given."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call cli with feature under test
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['list', '-e', '-l'], obj={})

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
        result = runner.invoke(cli.popquote, ['random'], obj={})

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
        result = runner.invoke(cli.popquote, ['random', '-t', 'book'], obj={})

        # Check results
        assert result.exit_code == 0

        # Confirm a single line of output was returned.
        self.assertEquals('A book is a gift you can open again and again.  - Garrison Keillor\n', result.output)

    def test_random_with_tags_nomatch(self):
        """Test that the random subcommand returns nothing if no matching tag"""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call random subcommand
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['random', '-t', 'book'], obj={})

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
        result = runner.invoke(cli.popquote, ['random', '-k', 'book'], obj={})

        # Check results
        assert result.exit_code == 0
        # Confirm no output.
        self.assertEquals('A book is a gift you can open again and again.  - Garrison Keillor\n', result.output)

    def test_random_with_keyword_nomatch(self):
        """Test that the random subcommand returns nothing if keyword doesn't match"""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call random subcommand
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['random', '-k', 'parakeet'], obj={})

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
        result = runner.invoke(cli.popquote, ['add', ' We accept the love we think we deserve.-Stephen Chbosky'],
                               obj={})
        print(result.output)

        # Check results
        assert result.exit_code == 0
        self.assertEquals('1 quote added for total of 5.\n', result.output)
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['list'], obj={})
        expected = "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.  - Linus Torvalds\n" + \
                   "God writes a lot of comedy... the trouble is, he's stuck with so many bad actors who don't know how to play funny.  - Garrison Keillor\n" + \
                   "I believe in looking reality straight in the eye and denying it.  - Garrison Keillor\n" + \
                   "A book is a gift you can open again and again.  - Garrison Keillor\n" + \
                   "We accept the love we think we deserve.  - Stephen Chbosky\n"
        self.assertEquals(expected, result.output)

    def test_add_when_quote_already_in_file(self):
        """The add subcommand should return error if quote is already in the quote file.
        """

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['add', '  I believe in looking reality straight in the ' +
                                              'eye and denying it. - Garrison Keillor'], obj={})

        assert result.exit_code == 1
        print(result.output)
        self.assertEquals(
            "Error: the quote \"I believe in looking reality straight in the eye and denying it.\" is already " +
            "in the quote file {0}.\n".format(path), result.output)

    def test_add_stdin(self):
        """Test add subcommand with input from stdin"""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Run command with add subcommand
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['add', '-'],
                               input='I believe in looking reality straight in the eye and denying it.-Garrison Keillor\n',
                               obj={})

        # Check results
        assert result.exit_code == 0
        # Check correct output on stdout
        self.assertEquals("1 quote added for total of 2.\n", result.output)

        # Check file modifications correct
        with open(path, "r") as modified_quotefile:
            returned = modified_quotefile.readlines()

        expected = ['A book is a gift you can open again and again. | Garrison Keillor |  | U\n',
                    'I believe in looking reality straight in the eye and denying it. | Garrison Keillor |  | \n']
        self.assertEquals(expected, returned)

    def test_add_with_no_author(self):
        """The add subcommand should return error if author not included with quote."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call add subcommand
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['add', '  We accept the love we think we deserve.-'], obj={})

        assert result.exit_code == 1
        self.assertEquals("Error: an author was not included with the quote.  Expecting quote in the format "
                          "\"<quote> - <author>\".\n", result.output)

    def test_add_with_publication(self):
        """The add subcommand should accept a publication after author if provided in parentheses."""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Run subcommand being tested
        runner = CliRunner()
        result = runner.invoke(cli.popquote,
                               ['add', '  We accept the love we think we deserve.-Stephen Chbosky (Publication)'],
                               obj={})

        # Check results
        assert result.exit_code == 0
        # Check no output
        self.assertEquals('1 quote added for total of 5.', result.output.strip())
        # Check that quote added
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['list', '-n', '5', '-l'], obj={})
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
                "God writes a lot of comedy... the trouble is, he's stuck with so many bad actors who don't know how to play funny. - Garrison Keillor" + os.linesep + \
                "I believe in looking reality straight in the eye and denying it. - Garrison Keillor" + os.linesep

        # Exercise CLI add feature that is under test
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['add', '-'], input=input, obj={})

        # Check results
        assert result.exit_code == 0
        # Check correct output on stdout
        self.assertEquals('3 quotes added for total of 4.\n', result.output)
        # Check file modifications correct
        expected = "1: A book is a gift you can open again and again.\n" + \
                   "    author: Garrison Keillor\n" + \
                   "    publication: \n" + \
                   "    tags: U\n" + \
                   "    hash: a166ebeb047ebdd9\n" + \
                   "2: The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it.\n" + \
                   "    author: Linus Torvalds\n" + \
                   "    publication: \n" + \
                   "    tags: \n" + \
                   "    hash: bbfc7839cd5c3559\n" + \
                   "3: God writes a lot of comedy... the trouble is, he's stuck with so many bad actors who don't know how to play funny.\n" + \
                   "    author: Garrison Keillor\n" + \
                   "    publication: \n" + \
                   "    tags: \n" + \
                   "    hash: 0074a7cd25c6b6a5\n" + \
                   "4: I believe in looking reality straight in the eye and denying it.\n" + \
                   "    author: Garrison Keillor\n" + \
                   "    publication: \n" + \
                   "    tags: \n" + \
                   "    hash: d81db3b61c3ab418\n"
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['list', '-l'], obj={})

        # Check zero return code
        assert result.exit_code == 0
        self.assertEquals(expected, result.output)

    def test_add_extended_format(self):
        """The add subcommand with -e option should allow extended format to be passed."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path
        test_input = 'I believe in looking reality straight in the eye and denying it. | Garrison Keillor |  | \n'

        # Exercise CLI add feature that is under test
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['add', '-e', '-'],
                               input=test_input, obj={})

        # Check zero return code
        print(result.output)
        assert result.exit_code == 0
        # Check correct output on stdout
        self.assertEquals("1 quote added for total of 2.\n", result.output)

        # Check file modifications correct
        with open(path, "r") as modified_quotefile:
            returned = modified_quotefile.readlines()

        expected = ['A book is a gift you can open again and again. | Garrison Keillor |  | U\n',
                    'I believe in looking reality straight in the eye and denying it. | Garrison Keillor |  | \n']
        self.assertEquals(expected, returned)

    def test_add_extended_format_with_error(self):
        """Test add subcommand with extended format, error case"""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise add subcommand with -e
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['add', '-e', '-'], input='This is not properly formatted', obj={})

        # Check return code
        assert result.exit_code == 1
        # Check expected error message
        expected = "Error: syntax error on line 1 of stdin: did not find 3 '|' characters.  " + \
                   "Line with error: \"This is not properly formatted\"\n"
        self.assertEquals(expected, result.output)

        # Check file not modified
        with open(path, "r") as modified_quotefile:
            returned = modified_quotefile.readlines()
        expected = ['A book is a gift you can open again and again.|Garrison Keillor||U\n']
        self.assertEquals(expected, returned)

    def test_showalltags(self):
        """Test showalltags subcommand"""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise showalltags subcommand
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['showalltags'], obj={})

        # Check return code
        assert result.exit_code == 0
        # Check correct output on stdout
        expected = "book\nfunny\nkeillor\n"
        self.assertEquals(expected, result.output)

    def test_missing_subcommand(self):
        """An random quote should be displayed if no subcommand."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Call with no subcommand
        runner = CliRunner()
        result = runner.invoke(cli.popquote, [], obj={})

        # Check results
        assert result.exit_code == 0
        # Check correct output on stdout
        expected = "A book is a gift you can open again and again.  - Garrison Keillor\n"
        self.assertEquals(expected, result.output)

    def test_codepage_conversion(self):
        """Characters in non-standard codepage should round trip OK to file and back."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        quotestring = 'δηψ.-Greek Author'

        # Call cli, pass arguments by mocking sys.argv
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['add', quotestring], obj={})

        # Check results
        assert result.exit_code == 0
        # Check that quote added
        with open(path, 'rb') as quotefile:
            data = quotefile.read()
        text_data = data.decode('utf-8')
        expected = \
            "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. " \
            "Yes, that's it. | Linus Torvalds |  | funny" + os.linesep + \
            "God writes a lot of comedy... the trouble is, he's stuck with " \
            "so many bad actors who don't know how to play funny. | Garrison" \
            " Keillor |  | funny, keillor" + os.linesep + \
            "I believe in looking reality straight in the eye and denying it. " \
            "| Garrison Keillor |  | funny, keillor" + os.linesep + \
            "A book is a gift you can open again and again. | Garrison Keillor |  | book, keillor" + os.linesep + \
            "δηψ. | Greek Author |  | " + os.linesep
        self.assertEquals(expected, text_data)

    @mock.patch('popquote.web.main')
    def test_webserver(self, mock_main):
        """Test webserver subcommand calls web.main"""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise webserver subcommand
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['webserver'], obj={})

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
        result = runner.invoke(cli.popquote, ['settags', '-s', 'd81db3b61c3ab418', 'tag1,tag2'], obj={})

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
            "God writes a lot of comedy... the trouble is, he's stuck with so many bad actors who don't know how to play funny. | Garrison Keillor |  | U\n",
            "I believe in looking reality straight in the eye and denying it. | Garrison Keillor |  | tag1, tag2\n",
            "A book is a gift you can open again and again. | Garrison Keillor |  | U\n"]
        self.assertEquals(expected, returned)

    def test_settags_invalid_args(self):
        """The settags subcommand should display error if both -s and -n given."""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise CLI add feature that is under test
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['settags', '-s', 'abcdef', '-n', '1', 'tag1,tag2'], obj={})

        # Check that an error message was displayed about invalid arguments
        assert result.exit_code == 1
        # Check expected error message
        expected = "Error: both the -s and -n option were included, but only one allowed.\n"
        self.assertEquals(expected, result.output)

    @patch('popquote.api.CONFIG_FILE', '/fake/config/file.conf')
    def test_popquote_info(self):
        """The info subcommand should show path to config file, path to quote file, and
        number of quotes.
        """

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        self.config[api.APP_NAME]['quote_file'] = path

        # Exercise CLI add feature that is under test
        runner = CliRunner()
        result = runner.invoke(cli.popquote, ['info'], obj={})

        # Check zero return code
        self.assertEquals(result.exit_code, 0)
        # Check correct output on stdout
        import popquote
        self.assertEquals(
            "Version: {}\n"
            "Settings file: /fake/config/file.conf\n"
            "Quote file: {}\n"
            "Number of quotes: 4\n".format(popquote.__version__, path),
            result.output)
