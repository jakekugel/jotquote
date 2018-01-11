# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

from __future__ import unicode_literals

import datetime
import os
import sys

from flask import Flask, render_template, g

from jotquote import api

app = Flask(__name__)


@app.route('/')
def rootpage():
    return showpage(settags=False)


@app.route('/tags')
def tagspage():
    return showpage(settags=True)


def showpage(settags=False):
    """Render the template"""

    quotes = get_quotes()

    # Get random random quote based on date and number of quotes
    index = api.get_random_choice(len(quotes))
    quote = quotes[index]

    # Get fields for rendering html
    quotestring = quote.quote
    author = quote.author
    publication = quote.publication

    # Setting hash variable to something other than none will cause rendered page to contain 'quote settags' command
    if settags:
        hashstring = quote.get_hash()
    else:
        hashstring = None
    space_tags = " ".join(quote.tags)
    comma_tags = ",".join(quote.tags)
    now = datetime.datetime.now()
    date1 = now.strftime("%A, %B %d, %Y")
    return render_template("quote.html", quote=quotestring, author=author, date1=date1,
                           publication=publication, quotenum=(index + 1), totalquotes=len(quotes),
                           space_tags=space_tags, comma_tags=comma_tags, hash=hashstring)


def get_quotes():
    """Get cached list of quotes from application context.  If not set, read"""
    quotes = getattr(g, '_quotes', None)

    if quotes is None:
        # Quotes not cached yet, read quote file
        quotes = api.read_quotes(app.config['QUOTE_FILE'])
        setattr(g, '_quotes', quotes)
        mtime = os.stat(app.config['QUOTE_FILE']).st_mtime
        setattr(g, '_cached_mtime', mtime)
    else:
        # Quotes had been previously cached, check if file modified
        mtime = os.stat(app.config['QUOTE_FILE']).st_mtime
        cached_mtime = getattr(g, '_cached_mtime', None)
        if mtime != cached_mtime:
            setattr(g, '_cached_mtime', mtime)
            quotes = api.read_quotes(app.config['QUOTE_FILE'])
            setattr(g, '_quotes', quotes)

    return quotes


def main():
    """Set up flask app and run it."""

    # Load needed configuration from settings.conf file
    config = api.get_config()
    app.config['QUOTE_FILE'] = config.get('jotquote', 'quote_file')
    listen_port = config.get('jotquote', 'web_port')
    listen_ip = config.get('jotquote', 'web_ip')

    if not listen_port:
        listen_port = 5544

    # A hack to deal with Python 2.7 quirk:
    if sys.version_info < (3, 0, 0):
        if isinstance(listen_port, basestring):  # noqa: F821
            listen_port = int(listen_port)

    if not listen_ip:
        listen_ip = "127.0.0.1"
    app.run(host=listen_ip, port=listen_port)


if __name__ == '__main__':
    main()
