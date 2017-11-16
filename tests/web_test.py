# -*- coding: utf-8 -*-
# This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from __future__ import unicode_literals

import os
import shutil
import tempfile
import unittest

from flask import g

import tests.test_util
from popquote import web


class Testpopquote(unittest.TestCase):
    """A few integration tests for the Flask app in web.py"""
    def setUp(self):
        # Create a temporary directory for use by the current unit test
        self.tempdir = tempfile.mkdtemp(prefix='popquote.unittest.')

        self.file = tests.test_util.init_quotefile(self.tempdir, "quotes5.txt")

        web.app.testing = True
        web.app.config['QUOTE_FILE'] = self.file
        self.app = web.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_page_basics(self):
        """A few sanity tests on web page"""
        rv = self.app.get('/')
        assert b'<!DOCTYPE html>' in rv.data
        assert b'<title>popquote</title>' in rv.data
        assert b'<div class="quote">A book is a gift you can open again and again.</div>' in rv.data
        assert b'<div class="author">Garrison Keillor</div>' in rv.data

    def test_page_tags(self):
        """A few sanity tests on web page"""
        rv = self.app.get('/tags')
        print(rv.data)
        assert b'<!DOCTYPE html>' in rv.data
        assert b'<title>popquote</title>' in rv.data
        assert b'<div class="quote">A book is a gift you can open again and again.</div>' in rv.data
        assert b'<div class="author">Garrison Keillor</div>' in rv.data
        assert b'<div id=\'settag\' class="command" style="display:none;">$ popquote settags -s a166ebeb047ebdd9 U</div>' in rv.data

    def test_quote_caching(self):
        """Test that quotes cached but reloaded if quote file changes"""
        with web.app.app_context():
            self.app.get('/')
            cached_time_1 = getattr(g, '_cached_mtime', None)
            self.app.get('/')
            cached_time_2 = getattr(g, '_cached_mtime', None)
            assert cached_time_1 == cached_time_2
            os.utime(self.file, (cached_time_2 + 1.0, cached_time_2 + 1.0))
            self.app.get('/')
            cached_time_3 = getattr(g, '_cache_mtime', None)
            assert cached_time_3 != cached_time_1


if __name__ == '__main__':
    unittest.main()
