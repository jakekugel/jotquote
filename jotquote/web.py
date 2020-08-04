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

    now = datetime.datetime.now()
    date1 = now.strftime("%A, %B %d, %Y")

    quotes = get_quotes()
    if quotes is None:
        return render_template("unavailable.html", date1=date1)

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
    return render_template("quote.html", quote=quotestring, author=author, date1=date1,
                           publication=publication, quotenum=(index + 1), totalquotes=len(quotes),
                           space_tags=space_tags, comma_tags=comma_tags, hash=hashstring, show_tags=False)


def get_quotes():
    """Get cached list of quotes from application context.  If not set, read"""
    quotes = getattr(g, '_quotes', None)

    # Ensure that path to quote file read from configuration file
    if 'QUOTE_FILE' not in app.config:
        config = api.get_config()
        app.config['QUOTE_FILE'] = config.get('jotquote', 'quote_file')

    try:
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
    except BaseException as exception:
        app.logger.error("unable to read quote file '{0}'.  Details: {1}".format(app.config['QUOTE_FILE'], str(exception)))
        setattr(g, '_quotes', None)
        setattr(g, '_cached_mtime', None)
        return None

    return quotes


def run_server():
    """Set up flask app and run it.

    This function is called when the 'jotquote webserver' command is called.
    When this method is used, the port and IP address from the config file
    are used.  However, it is possible to start the web server using a
    WSGI container.  In that case, this function is not called, and the
    WSGI container determines the port and IP address used.
    """

    # Load needed configuration from settings.conf file
    config = api.get_config()
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
