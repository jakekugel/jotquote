# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import logging
import os

from flask import Flask, make_response, render_template, g, request

from jotquote import api

app = Flask(__name__)

_access_logger = logging.getLogger("jotquote.access")
_access_logger.setLevel(logging.INFO)
_access_logger.propagate = False
_access_handler = logging.StreamHandler()
_access_handler.setFormatter(logging.Formatter("%(message)s"))
_access_logger.addHandler(_access_handler)


def _sanitize_for_log(value):
    """Remove newline and carriage return characters to prevent log injection."""
    return value.replace("\r", "").replace("\n", "")


@app.after_request
def log_request(response):
    _access_logger.info(
        "%s %s %s",
        request.method,
        _sanitize_for_log(request.full_path.rstrip("?")),
        response.status_code,
    )
    return response


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

    # Calculate max-age: configured cap or seconds until midnight, whichever is less
    midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_until_midnight = int((midnight - now).total_seconds())
    config = api.get_config()
    cap_minutes = int(config[api.APP_NAME].get('web_cache_minutes', '240'))
    page_title = config[api.APP_NAME].get('web_page_title', 'jotquote')
    show_stars = config[api.APP_NAME].get('web_show_stars', 'false').lower() == 'true'
    max_age = min(cap_minutes * 60, seconds_until_midnight)

    quotes = get_quotes()
    if quotes is None:
        response = make_response(render_template("unavailable.html", date1=date1, page_title=page_title))
        response.headers['Cache-Control'] = f'public, max-age={max_age}'
        return response

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
    _star_tag_map = {'1star': 1, '2stars': 2, '3stars': 3, '4stars': 4, '5stars': 5}
    stars = next((v for t, v in _star_tag_map.items() if t in quote.tags), 0)
    response = make_response(render_template("quote.html", quote=quotestring, author=author, date1=date1,
                                             publication=publication, quotenum=(index + 1), totalquotes=len(quotes),
                                             space_tags=space_tags, comma_tags=comma_tags, hash=hashstring,
                                             show_tags=False, page_title=page_title, stars=stars,
                                             show_stars=show_stars))
    response.headers['Cache-Control'] = f'public, max-age={max_age}'
    return response


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
    """Start the web server using Waitress as the WSGI server.

    This function is called when the 'jotquote webserver' command is called.
    Waitress is used as the WSGI server, which is suitable for production use.
    The host and port are read from the settings.conf configuration file.

    Alternatively, any WSGI server can be pointed directly at the 'app' object
    exported from this module.  For example:

        waitress-serve --host 127.0.0.1 --port 5544 jotquote.web:app
        gunicorn --bind 127.0.0.1:5544 jotquote.web:app  (Linux/Mac only)

    When using a WSGI server directly, this function is not called and the
    WSGI server determines the host and port.
    """

    # Load needed configuration from settings.conf file
    config = api.get_config()
    listen_port = config.get('jotquote', 'web_port')
    listen_ip = config.get('jotquote', 'web_ip')

    if not listen_port:
        listen_port = 5544

    if not listen_ip:
        listen_ip = "127.0.0.1"

    logging.basicConfig(level=logging.INFO)
    from waitress import serve
    serve(app, host=listen_ip, port=int(listen_port))
