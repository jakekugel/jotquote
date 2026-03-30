# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import logging
import os

import click
from flask import Flask, abort, g, make_response, render_template, request

from jotquote import api

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 24 hours

_LOG_FORMAT = '%(levelname)s %(message)s'

# Configure the root logger at module load time so the format applies regardless
# of whether the app is launched via 'jotquote webserver' or a WSGI server directly.
logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)

# Named logger for HTTP access lines; propagates to the root handler configured above.
_access_logger = logging.getLogger('jotquote.access')
_access_logger.setLevel(logging.INFO)


def _sanitize_for_log(value):
    """Remove newline and carriage return characters to prevent log injection."""
    return value.replace('\r', '').replace('\n', '')


@app.after_request
def log_request(response):
    _access_logger.info(
        '%s %s %s',
        request.method,
        _sanitize_for_log(request.full_path.rstrip('?')),
        response.status_code,
    )
    return response


@app.route('/')
def rootpage():
    return showpage()


@app.route('/<date_path_param>')
def datepage(date_path_param):
    # Validate: must be exactly 8 digits
    if len(date_path_param) != 8 or not date_path_param.isdigit():
        abort(404)
    return showpage(date_path_param=date_path_param)


def showpage(date_path_param=None):
    """Render the template"""

    now = datetime.datetime.now()

    # Calculate max-age: configured cap or seconds until midnight, whichever is less
    midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_until_midnight = int((midnight - now).total_seconds())
    config, _ = api.get_config()
    cap_minutes = int(config[api.SECTION_WEB].get('cache_minutes', '240'))
    page_title = config[api.SECTION_WEB].get('page_title', 'jotquote')
    show_stars = config[api.SECTION_WEB].get('show_stars', 'false').lower() == 'true'
    light_fg = config[api.SECTION_WEB].get('light_foreground_color', '#000000')
    light_bg = config[api.SECTION_WEB].get('light_background_color', '#ffffff')
    dark_fg = config[api.SECTION_WEB].get('dark_foreground_color', '#ffffff')
    dark_bg = config[api.SECTION_WEB].get('dark_background_color', '#000000')
    max_age = min(cap_minutes * 60, seconds_until_midnight)

    # Determine display date
    if date_path_param:
        try:
            display_date = datetime.datetime.strptime(date_path_param, '%Y%m%d')
        except ValueError:
            abort(404)
        date1 = display_date.strftime('%A, %B %d, %Y')
    else:
        date1 = now.strftime('%A, %B %d, %Y')

    quotes = get_quotes()
    if quotes is None:
        response = make_response(
            render_template(
                'unavailable.html',
                date1=date1,
                page_title=page_title,
                light_fg=light_fg,
                light_bg=light_bg,
                dark_fg=dark_fg,
                dark_bg=dark_bg,
            )
        )
        response.headers['Cache-Control'] = f'public, max-age={max_age}'
        return response

    # Try to load quotemap and find a mapped quote
    permalink = None
    quotemap_file = config[api.SECTION_WEB].get('quotemap_file', '')
    quotemap = {}
    if quotemap_file:
        try:
            quotemap = api.read_quotemap(quotemap_file)
        except click.ClickException as e:
            app.logger.error('quotemap error: %s', e.format_message())
            if date_path_param:
                abort(404)

    lookup_date = date_path_param if date_path_param else now.strftime('%Y%m%d')
    mapped_quote = None
    if lookup_date in quotemap:
        hash_value = quotemap[lookup_date]['hash']
        mapped_quote = api.get_first_match(quotes, hash_arg=hash_value)
        if mapped_quote is None:
            app.logger.warning("quotemap hash '%s' for date %s not found in quotes", hash_value, lookup_date)
            if date_path_param:
                abort(404)

    if mapped_quote:
        quote = mapped_quote
        index = quotes.index(quote)
        # Show permalink on root page when today's quote comes from quotemap
        if date_path_param is None:
            permalink = f'/{lookup_date}'
        # For date URLs, content is static — use full cache cap
        if date_path_param:
            max_age = cap_minutes * 60
    elif date_path_param:
        # Date route requested but date not in quotemap — 404
        abort(404)
    else:
        # Root route, fall back to seeded RNG
        index = api.get_random_choice(len(quotes))
        quote = quotes[index]

    stars = quote.get_num_stars()
    response = make_response(
        render_template(
            'quote.html',
            quote=quote.quote,
            author=quote.author,
            date1=date1,
            publication=quote.publication,
            quotenum=(index + 1),
            totalquotes=len(quotes),
            page_title=page_title,
            stars=stars,
            show_stars=show_stars,
            permalink=permalink,
            light_fg=light_fg,
            light_bg=light_bg,
            dark_fg=dark_fg,
            dark_bg=dark_bg,
        )
    )
    response.headers['Cache-Control'] = f'public, max-age={max_age}'
    return response


def get_quotes():
    """Get cached list of quotes from application context.  If not set, read"""
    quotes = getattr(g, '_quotes', None)

    # Ensure that path to quote file read from configuration file
    if 'QUOTE_FILE' not in app.config:
        config, _ = api.get_config()
        app.config['QUOTE_FILE'] = config.get(api.SECTION_GENERAL, 'quote_file')

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
        app.logger.error(
            "unable to read quote file '{0}'.  Details: {1}".format(app.config['QUOTE_FILE'], str(exception))
        )
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
    WSGI server determines the host and port.  Logging is configured at module
    load time, so the format applies regardless of launch method.
    """

    # Load needed configuration from settings.conf file
    config, migrated = api.get_config()
    if migrated:
        app.logger.warning(
            'settings.conf uses the deprecated [jotquote] section. '
            'Please update to [general], [lint], and [web] sections.'
        )
    listen_port = config.get(api.SECTION_WEB, 'port')
    listen_ip = config.get(api.SECTION_WEB, 'ip')

    if not listen_port:
        listen_port = 5544

    if not listen_ip:
        listen_ip = '127.0.0.1'

    from waitress import serve

    serve(app, host=listen_ip, port=int(listen_port))
