# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from __future__ import unicode_literals

import os
import re
import shutil
import sys
import tempfile
import unittest
# Disable PyCharm linter, the configparser module is available in 2.7
# noinspection PyCompatibility
from configparser import ConfigParser

import click
import mock

import tests.test_util
from popquote import api


class TestPopquote(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for use by the current unit test
        self.tempdir = tempfile.mkdtemp(prefix='popquote.unittest.')

        # Create a test ConfigParser object
        self.config = ConfigParser()
        self.config.add_section(api.APP_NAME)
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

    def test_read_quotes(self):
        """Test read_quotes() basic functionality"""
        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")

        # Call function being tested
        quotes = api.read_quotes(path)

        # Check results
        self.assertEqual(4, len(quotes))

    def test_read_quotes_fnf(self):
        """read_quotes() should raise exception if file not found."""
        path = os.path.join(self.tempdir, "fakename.txt")
        with self.assertRaisesRegexp(Exception, re.escape("The quote file '{0}' was not found.".format(path))):
            api.read_quotes(path)

    def test_read_quotes_empty_file(self):
        """read_quotes() should work if empty file."""
        path = os.path.join(self.tempdir, "emptyfile.txt")
        # Create empty file
        open(path, 'a').close()
        quotes = api.read_quotes(path)
        self.assertEqual(0, len(quotes))

    def test_read_quotes_no_final_newline(self):
        """read_quotes() should work even if no final newline"""
        path = tests.test_util.init_quotefile(self.tempdir, "quotes2.txt")
        quotes = api.read_quotes(path)
        self.assertEqual(4, len(quotes))

    def test_read_quotes_blank_lines(self):
        """read_quotes() should allow blank lines"""
        path = tests.test_util.init_quotefile(self.tempdir, "quotes3.txt")
        quotes = api.read_quotes(path)
        self.assertEqual(4, len(quotes))

    def test_read_quotes_commented_lines(self):
        """read_quotes() should allow lines commented with #"""

        path = tests.test_util.init_quotefile(self.tempdir, "quotes4.txt")
        quotes = api.read_quotes(path)
        self.assertEqual(4, len(quotes))

    def test_read_quotes_with_extra_pipe_character_in_quotefile(self):
        """read_quotes() should raise exception if there is extra pipe character on line."""
        path = tests.test_util.init_quotefile(self.tempdir, "quotes6.txt")

        with self.assertRaisesRegexp(Exception, re.escape(
                "syntax error on line 1 of {0}: did not find 3 '|' characters.  Line with error: \"A book is a gift "
                "you can open again and again.|Garrison Keillor||U|\"".format(path))):
            api.read_quotes(path)

    def test_read_quotes_with_double_quote_in_quotefile(self):
        """read_quotes() should raise exception if there is a double-quote character in the quote."""
        path = tests.test_util.init_quotefile(self.tempdir, "quotes7.txt")
        with self.assertRaisesRegexp(Exception, re.escape(
                "syntax error on line 2 of {0}: the quote included an embedded double quote "
                "character, but only single quote characters (\') allowed in quotes.  Line with error: \"A book is a "
                "gift you can open again and \" again.|Garrison Keillor||U\"".format(path))):
            api.read_quotes(path)

    def test_parse_quotes(self):
        """parse_quotes() should parse a pipe-delimited quote string."""
        quote = api.parse_quote("  This is a quote. |  Author  | Publication   | tag1, tag2 , tag3  ",
                                simple_format=False)
        self.assertEqual("This is a quote.", quote.quote)
        self.assertEqual("Author", quote.author)
        self.assertEqual("Publication", quote.publication)
        self.assertEqual(3, len(quote.tags))

    def test_parse_quotes_doublequote(self):
        """parse_quote() should raise exception if there is double quote in quote being parsed."""
        with self.assertRaisesRegexp(Exception, re.escape(
                "the quote included an embedded double quote character, but only single quote characters (') "
                "allowed in quotes")):
            api.parse_quote("  This is a quote\". |  Author  | Publication   | tag1, tag2 , tag3  ",
                            simple_format=False)

    def test_parse_quotes_not_three_vertical_bars(self):
        """parse_quote() should raise exception if there are not three pipe characters"""
        with self.assertRaisesRegexp(Exception, re.escape("did not find 3 '|' characters")):
            api.parse_quote("  This is a quote||", simple_format=False)

    def test_parse_quotes_no_quote(self):
        """parse_quote() should raise exception if the quote field is empty."""
        with self.assertRaisesRegexp(Exception, 'a quote was not found'):
            api.parse_quote("|  Author  | Publication   | tag1, tag2 , tag3  ", simple_format=False)

    def test_parse_quotes_no_author(self):
        """parse_quote() should raise exception if there is no author."""
        with self.assertRaisesRegexp(Exception, re.escape('an author was not included with the quote.  Expecting '
                                                          'quote in the format \"<quote> - <author>\".')):
            api.parse_quote("This is a quote. | | Publication   | tag1, tag2 , tag3  ", simple_format=False)

    def test_parse_quotes_alphanumerics_only_in_tags(self):
        """parse_quote() should raise exception if there are invalid characters in tags."""
        with self.assertRaisesRegexp(click.ClickException, "invalid tag 'tag3!': only numbers, letters, and commas are allowed in tags"):
            api.parse_quote("This is a quote. | Author | Publication   | tag1, tag2 , tag3!  ",
                            simple_format=False)

    def test_parse_simple_quote(self):
        """parse_quote() should work when parsing a quote in simple format."""
        quote = api.parse_quote("  We accept the love we think we deserve.  - Stephen Chbosky", simple_format=True)
        self.assertEqual("We accept the love we think we deserve.", quote.quote)
        self.assertEqual("Stephen Chbosky", quote.author)
        self.assertEqual(None, quote.publication)
        self.assertEqual(0, len(quote.tags))

    def test_parse_simple_quote_with_double_quote(self):
        """Not allowed to have double quote character in quote itself"""
        with self.assertRaisesRegexp(Exception, "the quote included an embedded double quote character, "
                                                "but only single quote characters \('\) allowed in quotes"):
            api.parse_quote("  We accept the love we think we \" deserve.  - Stephen Chbosky",
                            simple_format=True)

    def test_parse_simple_quote_with_double_quote_in_author(self):
        """It is supported to have a double quote character in the author."""
        quote = api.parse_quote("  Hey, grades are not cool, learning is cool. - Arthur \"Fonzie\" Fonzarelli",
                                simple_format=True)

        # Check that it parsed correctly
        self.assertEquals("Arthur \"Fonzie\" Fonzarelli", quote.author)

    def test_parse_simple_quote_with_no_hyphen(self):
        """Test that parse_quote() raises exception if there is not a hyphen."""
        with self.assertRaisesRegexp(Exception, re.escape('the quote line does not contain exactly one hyphen.  '
                                     'Expected format: "<quote> - <author> [(publication)]"')):
            api.parse_quote("  We accept the love we think we deserve. Stephen Chbosky", simple_format=True)

    def test_parse_simple_quote_with_no_quote(self):
        """parse_quote() should raise exception if parsing simple format and there is no quote before hyphen."""
        with self.assertRaisesRegexp(Exception, re.escape("a quote was not found")):
            api.parse_quote(" - Hamlet  ", simple_format=True)

    def test_parse_simple_quote_with_no_author(self):
        """parse_quote() should raise exception if parsing simple format and no author after hyphen."""
        with self.assertRaisesRegexp(Exception, "an author was not included with the quote.  Expecting quote in " 
                                                "the format \"<quote> - <author>\""):
            api.parse_quote(" Quote -   ", simple_format=True)

    def test_parse_simple_quote_with_pipe_character(self):
        """pares_quote() should raise exception if parsing simple format and there is a pipe character."""
        with self.assertRaisesRegexp(Exception, "the quote included an embedded pipe character (|)"):
            api.parse_quote(" Quote with | character - Author", simple_format=True)

    def test_add_quote(self):
        """add_quote() method should add single quote to end of quote file."""

        # Set up for test
        path = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")
        quote = api.Quote("  This is an added quote.", "Another author", "Publication", ["tag1, tag2"])

        # Call method being tested
        api.add_quote(path, quote)

        # Check results.  Read the resulting text file and verify
        with open(path, 'rb') as file:
            data = file.read()
        text_data = data.decode('utf-8')
        expected = u'A book is a gift you can open again and again. | Garrison Keillor |  | U' + os.linesep + \
                   u'This is an added quote. | Another author | Publication | tag1, tag2' + os.linesep
        self.assertEquals(expected, text_data)

    def test_add_quote_but_file_not_found(self):
        """Test that add_quote() raises exception if quote file does not exist."""
        quote = api.Quote("  This is an added quote.", "Another author", "Publication", ["tag1, tag2"])
        quotefile = os.path.join(self.tempdir, "fakename.txt")

        with self.assertRaisesRegexp(Exception, re.escape("The quote file '{0}' does not exist.".format(quotefile))):
            api.add_quote(quotefile, quote)

    def test_add_quote_but_quote_object_not_passed(self):
        """Test that add_quote() raises exception if object passed is not Quote object."""
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        with self.assertRaisesRegexp(Exception, "The quote parameter must be type class Quote."):
            api.add_quote(path, None)

    def test_add_quote_but_file_contains_quote_already(self):
        """Test that add_quote() raises exception if new quote already in quote file."""
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        quote = api.Quote("  This is an added quote.", "Another author", "Publication", ["tag1, tag2"])
        api.add_quote(path, quote)

        with self.assertRaisesRegexp(Exception, re.escape(
                'the quote "This is an added quote." is already in the quote file {0}.'.format(path))):
            api.add_quote(path, quote)

    def test_check_for_duplicates_with_duplicates(self):
        """The _check_for_duplicates function should raise exception if there are duplicate quotes."""
        quotes = [api.Quote("  This is an added quote.", "Another author", "Publication", ["tag1, tag2"]),
                  api.Quote("  This is an added quote.", "Another author2", "Publication", ["tag1, tag2"]),
                  api.Quote("  This is an added quote.", "Another author3", "Publication", ["tag1, tag2"])]

        with self.assertRaisesRegexp(Exception, "a duplicate quote was found on line 2 of 'stdin'.  "
                                                          "Quote: \"This is an added quote.\"."):

            api._check_for_duplicates(quotes, "stdin")

    def test_check_for_duplicates(self):
        quotes = [api.Quote("  This is an added quote.", "Another author", "Publication", ["tag1, tag2"]),
                  api.Quote("  This is a different added quote.", "Another author2", "Publication", ["tag1, tag2"]),
                  api.Quote("  This is yet another added quote.", "Another author3", "Publication", ["tag1, tag2"])]

        api._check_for_duplicates(quotes, "testcase")

    def test_parse_tags(self):
        tagstring = "  tag1  , tag2 , tag3  , "
        tags = api.parse_tags(tagstring)

        self.assertEqual("tag1", tags[0])
        self.assertEqual("tag2", tags[1])
        self.assertEqual("tag3", tags[2])

    def test_parse_tags_complex(self):
        tagstring = "    , tag2 , tag3  ,,  , , tag2 , tag1 "
        tags = api.parse_tags(tagstring)

        self.assertEqual("tag1", tags[0])
        self.assertEqual("tag2", tags[1])
        self.assertEqual("tag3", tags[2])

    def test_parse_tags_with_underscores(self):
        tagstring = "    , tag_2 , tag3_  ,,  , , tag2 , tag1 "
        tags = api.parse_tags(tagstring)

        self.assertEqual("tag1", tags[0])
        self.assertEqual("tag2", tags[1])
        self.assertEqual("tag3_", tags[2])
        self.assertEqual("tag_2", tags[3])

    def test_parse_tags_invalid(self):
        """The parse_tags() method should raise exception if invalid character in tag"""
        tagstring = "tag1, tag2, tag3!"

        with self.assertRaisesRegexp(Exception, "invalid tag 'tag3!': only numbers, letters, and commas are "
                                     "allowed in tags"):
            api.parse_tags(tagstring)

    def test_write_quotes(self):
        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        quotes = api.read_quotes(path)
        quote = api.Quote("Another new quote", "author", None, [])
        quotes.append(quote)

        api.write_quotes(path, quotes)

        quotes = api.read_quotes(path)
        self.assertEqual("Another new quote", quotes[len(quotes) - 1].quote)
        self.assertEqual("author", quotes[len(quotes) - 1].author)

    def test_write_quotes_unix(self):
        """ If property line_separator = unix, then line separator should be \n."""

        # Set up the
        self.config[api.APP_NAME]['line_separator'] = 'unix'

        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        quotes = api.read_quotes(path)

        # Call write_quotes to write file
        api.write_quotes(path, quotes)

        # Verify unix line separator used when file written
        with open(path, "rb") as openfile:
            whole_file = openfile.read().decode("utf-8")
        expected = "The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. Yes, that's it. | Linus Torvalds |  | U\n" + \
                   "God writes a lot of comedy... the trouble is, he's stuck with so many bad actors who don't know how to play funny. | Garrison Keillor |  | U\n" + \
                   "I believe in looking reality straight in the eye and denying it. | Garrison Keillor |  | U\n" + \
                   "A book is a gift you can open again and again. | Garrison Keillor |  | U\n"
        self.assertEqual(expected, whole_file)

    def test_write_quotes_windows(self):
        """ If line_separator = windows, then line separator should be \r\n."""

        # Set up the test config object
        self.config[api.APP_NAME]['line_separator'] = 'windows'

        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        quotes = api.read_quotes(path)

        # Call write_quotes to write file
        api.write_quotes(path, quotes)

        # Verify unix line separator used when file written.  Need to verify
        # by reading in binary mode, otherwise the file.read() function will
        # convert newline characters to '\n'
        with open(path, "rb") as binfile:
            whole_file = binfile.read()
        expected = b"The Linux philosophy is 'Laugh in the face of danger'. Oops. Wrong One. 'Do it yourself'. " + \
                   b"Yes, that's it. | Linus Torvalds |  | U\r\n" + \
                   b"God writes a lot of comedy... the trouble is, he's stuck with so many bad actors who don't " + \
                   b"know how to play funny. | Garrison Keillor |  | U\r\n" + \
                   b"I believe in looking reality straight in the eye and denying it. | Garrison Keillor |  | U\r\n" + \
                   b"A book is a gift you can open again and again. | Garrison Keillor |  | U\r\n"
        self.assertEqual(expected, whole_file)

    def test_write_quotes_invalid(self):
        """The write_quotes() function should raise exception if invalid line_separator config property."""

        # Set up the
        self.config[api.APP_NAME]['line_separator'] = 'VAX-VMS'

        path = tests.test_util.init_quotefile(self.tempdir, "quotes1.txt")
        quotes = api.read_quotes(path)

        # Call write_quotes to write file
        with self.assertRaisesRegexp(Exception,
                                     "the value 'VAX-VMS' is not valid value for the line_separator property.  Valid "
                                     "values are 'platform', 'windows', or 'unix'."):
            api.write_quotes(path, quotes)

    def test_write_quotes_fnf(self):
        """write_quotes() should raise exception if quote file does not exist."""

        # Setup: create a pathname to file that does not exist
        path = os.path.join(self.tempdir, "fakename.txt")
        quote = api.Quote("Another new quote", "author", None, [])
        quotes = [quote]

        # Call function under test, check that exception raised
        with self.assertRaisesRegexp(Exception, re.escape("the quote file '{0}' was not found.".format(path))):
            api.write_quotes(path, quotes)

    # This is a performance test, need to decide what to do with these
    # def test_large_file(self):
    #     """Should be performant reading and writing 10000 quotes."""
    #
    #     # Setup: create quote file with 10,000 quotes
    #     largefile = os.path.join(self.tempdir, "large-quotefile.txt")
    #     open(largefile, 'a').close()
    #     quotes = []
    #     for index in range(10000):
    #         quote = api.Quote("Another new quote %s" % str(index), "author", None,
    #                           ["tag1", "tag2", "asdsadas", "ewrewr"])
    #         quotes.append(quote)
    #
    #     # Time how long it takes to write and then read back 10,000 quotes
    #     start = time.time()
    #     api.write_quotes(largefile, quotes)
    #     quotes = api.read_quotes(largefile)
    #     end = time.time()
    #
    #     # Check results
    #     if (end - start) > 2.0:
    #         self.fail("Took longer than 2 seconds (%s seconds) to write and read back 10,000 quotes." % (end - start))

    def test_has_tag(self):
        quote = api.Quote("New quote", "New author", "New publication", ["tag1", "tag3", "tag5"])

        self.assertTrue(quote.has_tag("tag1"))
        self.assertFalse(quote.has_tag("tagA"))

    def test_has_tags(self):
        quote = api.Quote("New quote", "New author", "New publication", ["tag1", "tag3", "tag5"])

        self.assertTrue(quote.has_tags(["tag1", "tag3"]))
        self.assertFalse(quote.has_tags(["tag1", "tagA"]))
        self.assertTrue(quote.has_tags([]))

    def test_has_keyword(self):

        quote = api.Quote("New quote", "New author", "New publication", ["tag1", "tag3", "tag5"])

        self.assertTrue(quote.has_keyword("quote"))
        self.assertTrue(quote.has_keyword("author"))
        self.assertTrue(quote.has_keyword("publication"))
        self.assertTrue(quote.has_keyword("tag3"))
        self.assertFalse(quote.has_keyword("tagA"))

    def test_get_random_value_1(self):
        days = 5
        numvalues = 10
        index = api._get_random_value(days, numvalues)
        if sys.version_info >= (3, 2):
            self.assertEqual(4, index)
        else:
            self.assertEqual(7, index)

    def test_get_random_value_2(self):
        days = 3
        numvalues = 15
        index = api._get_random_value(days, numvalues)
        if sys.version_info >= (3, 2):
            self.assertEqual(5, index)
        else:
            self.assertEqual(8, index)

    def test_get_random_value_3(self):
        days = 199
        numvalues = 100
        index = api._get_random_value(days, numvalues)
        if sys.version_info >= (3, 2):
            self.assertEqual(49, index)
        else:
            self.assertEqual(84, index)

    def test_get_random_value_4(self):
        items = [None] * 12  # Initialize list to length 8
        items[0] = api._get_random_value(0, 8)
        items[1] = api._get_random_value(1, 8)
        items[2] = api._get_random_value(2, 8)
        items[3] = api._get_random_value(3, 8)
        items[4] = api._get_random_value(4, 8)
        items[5] = api._get_random_value(5, 8)
        items[6] = api._get_random_value(6, 8)
        items[7] = api._get_random_value(7, 8)
        items[8] = api._get_random_value(8, 8)
        items[9] = api._get_random_value(9, 8)
        items[10] = api._get_random_value(10, 8)
        items[11] = api._get_random_value(11, 8)

        if sys.version_info >= (3, 2):
            self.assertEqual(4, items[0])
            self.assertEqual(1, items[1])
            self.assertEqual(5, items[2])
            self.assertEqual(2, items[3])
            self.assertEqual(0, items[4])
            self.assertEqual(3, items[5])
            self.assertEqual(7, items[6])
            self.assertEqual(6, items[7])
            self.assertEqual(4, items[8])
            self.assertEqual(1, items[9])
            self.assertEqual(5, items[10])
            self.assertEqual(2, items[11])
        else:
            self.assertEquals([0, 3, 4, 7, 1, 2, 5, 6, 0, 3, 4, 7], items)

    def test_duplicate_quotes(self):
        """The read_quotes() function should raise exception if there are duplicate quotes."""

        # Setup
        path = tests.test_util.init_quotefile(self.tempdir, "quotes8.txt")

        # Call function being tested
        with self.assertRaisesRegexp(Exception, re.escape("a duplicate quote was found on line 5 of '{}'.  Quote: \"God "
                                     "writes a lot of comedy... the trouble is, he's stuck with so many bad actors "
                                     "who don't know how to play funny.\"".format(path))):
            api.read_quotes(path)

    # def _get_test_data_to_temp(self, data_filename):
    #     test_module_directory = os.path.dirname(__file__)
    #     test_data_source = os.path.join(test_module_directory, "testdata", data_filename);
    #     test_data_target = os.path.join(self.tempdir, data_filename)
    # 
    #     shutil.copyfile(test_data_source, test_data_target)
    #     return test_data_target
