# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import importlib
import logging
import os

from flask import Flask, abort, g, make_response, render_template, request

from jotquote import api
from jotquote.web import helpers as web_helpers

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 24 hours

# Configure the root logger at module load time so the format applies regardless
# of whether the app is launched via 'jotquote webserver' or a WSGI server directly.
web_helpers.configure_logging()

# Named logger for HTTP access lines; propagates to the root handler configured above.
_access_logger = logging.getLogger('jotquote.access')
_access_logger.setLevel(logging.INFO)

# Named logger for startup messages.
_logger = logging.getLogger(__name__)


def _log_startup_info():
    """Log settings file path, quote file path, and package version at startup.

    Called once at module load time so the messages appear regardless of whether
    the server is launched via 'jotquote webserver' or directly via a WSGI server
    such as waitress-serve.
    """
    import jotquote

    # Compute config file path using the same logic as api.get_config()
    config_file = os.environ.get('JOTQUOTE_CONFIG') or api.CONFIG_FILE
    config, _ = api.get_config()
    quote_file = config.get(api.SECTION_GENERAL, 'quote_file')
    _logger.info('path to settings.conf file: %s', config_file)
    _logger.info('path to the quote file: %s', quote_file)
    _logger.info('jotquote package version: %s', jotquote.__version__)


_log_startup_info()

# Cached quote resolver function, loaded lazily on first request.
_resolver_fn = None
_resolver_loaded = False

# Cached header-provider function, loaded lazily on first request.
_header_fn = None
_header_loaded = False


@app.after_request
def log_request(response):
    expires_at = getattr(g, 'expires_at', None)
    if expires_at:
        _access_logger.info(
            '%s %s %s expires_at=%s',
            request.method,
            web_helpers.sanitize_for_log(request.full_path.rstrip('?')),
            response.status_code,
            expires_at,
        )
    else:
        _access_logger.info(
            '%s %s %s',
            request.method,
            web_helpers.sanitize_for_log(request.full_path.rstrip('?')),
            response.status_code,
        )
    return response


@app.route('/')
def rootpage():
    return showpage()


@app.route('/about')
def aboutpage():
    """Render the about page."""
    config, _ = api.get_config()
    about_text = config[api.SECTION_WEB].get('about', '')
    if not about_text:
        abort(404)
    page_title = config[api.SECTION_WEB].get('page_title', 'jotquote')
    colors = web_helpers.get_color_config(config)
    return render_template('about.html', about_text=about_text, page_title=page_title, **colors)


@app.route('/<date_path_param>')
def datepage(date_path_param):
    # Validate: must be exactly 8 digits
    if len(date_path_param) != 8 or not date_path_param.isdigit():
        abort(404)
    return showpage(date_path_param=date_path_param)


def showpage(date_path_param=None):
    """Render the template"""

    now = datetime.datetime.now()

    # Calculate expiration: configured cap or seconds until midnight, whichever is less
    midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_until_midnight = int((midnight - now).total_seconds())
    config, _ = api.get_config()
    expiration_seconds = int(config[api.SECTION_WEB].get('expiration_seconds', '14400'))
    page_title = config[api.SECTION_WEB].get('page_title', 'jotquote')
    show_stars = config[api.SECTION_WEB].get('show_stars', 'false').lower() == 'true'
    mode = config[api.SECTION_WEB].get('mode', 'daily')
    about_text = config[api.SECTION_WEB].get('about', '')
    colors = web_helpers.get_color_config(config)
    if mode != 'random' and date_path_param is None:
        expiration_seconds = min(expiration_seconds, seconds_until_midnight)

    # Compute cache expiration time for auto-refresh (root route only)
    if date_path_param is None:
        expires_at_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expiration_seconds)
        expires_at = expires_at_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    else:
        expires_at = None
    g.expires_at = expires_at

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
                expires_at=expires_at,
                about_text=about_text,
                **colors,
            )
        )
        _apply_headers(response, config, expiration_seconds)
        return response

    # Select quote based on mode
    permalink = None
    if mode == 'random' and date_path_param is None:
        quote = api.get_first_match(quotes, rand=True)
        index = quotes.index(quote)
    else:
        # Try the configured quote resolver
        resolver = _get_resolver(config)
        lookup_date = date_path_param if date_path_param else now.strftime('%Y%m%d')
        resolved_hash = None
        if resolver:
            try:
                resolved_hash = resolver(lookup_date)
            except Exception:
                app.logger.exception('quote resolver error for date %s', lookup_date)

        if resolved_hash:
            quote = api.get_first_match(quotes, hash_arg=resolved_hash)
            if quote:
                index = quotes.index(quote)
                # Show permalink on root page when resolver maps today's quote
                if date_path_param is None:
                    permalink = f'/{lookup_date}'
            elif date_path_param:
                abort(404)
            else:
                # Hash not found, fall back to seeded RNG
                index = api.get_random_choice(len(quotes))
                quote = quotes[index]
        elif date_path_param:
            # Date route requested but no resolver or resolver returned None — 404
            abort(404)
        else:
            # Root route, fall back to seeded RNG
            index = api.get_random_choice(len(quotes))
            quote = quotes[index]

    stars = quote.get_num_stars()
    response = make_response(
        render_template(
            'viewer.html',
            quote=quote.quote,
            author=quote.author,
            date1=date1,
            publication=quote.publication,
            quotenum=(index + 1),
            totalquotes=len(quotes),
            page_title=page_title,
            expires_at=expires_at,
            stars=stars,
            show_stars=show_stars,
            permalink=permalink,
            about_text=about_text,
            **colors,
        )
    )
    _apply_headers(response, config, expiration_seconds)
    return response


def _get_resolver(config):
    """Return the cached quote resolver function, or None.

    Loads the resolver module specified by the ``quote_resolver_extension`` property in the
    ``[web]`` section of settings.conf.  The module must define a ``resolve``
    function that accepts a date string (YYYYMMDD) and returns a 16-char MD5 hash
    string or None.

    config (ConfigParser) -- the application configuration object.
    Returns callable or None.
    """
    global _resolver_fn, _resolver_loaded
    if _resolver_loaded:
        return _resolver_fn
    _resolver_loaded = True
    module_path = config[api.SECTION_WEB].get('quote_resolver_extension', '')
    if not module_path:
        return None
    try:
        mod = importlib.import_module(module_path)
        _resolver_fn = getattr(mod, 'resolve')
    except (ImportError, AttributeError) as e:
        app.logger.error('failed to load quote resolver %r: %s', module_path, e)
    return _resolver_fn


def _reset_resolver():
    """Clear cached resolver state so the next call to _get_resolver reloads.

    Intended for use in tests only.
    """
    global _resolver_fn, _resolver_loaded
    _resolver_fn = None
    _resolver_loaded = False


def _get_header_provider(config):
    """Return the cached header-provider function, or None.

    Loads the header-provider module specified by the ``header_provider_extension``
    property in the ``[web]`` section of settings.conf.  The module must
    define a ``get_headers`` function that accepts an integer max_age and
    returns a dict of HTTP header name/value pairs.

    config (ConfigParser) -- the application configuration object.
    Returns callable or None.
    """
    global _header_fn, _header_loaded
    if _header_loaded:
        return _header_fn
    _header_loaded = True
    module_path = config[api.SECTION_WEB].get('header_provider_extension', '')
    if not module_path:
        return None
    try:
        mod = importlib.import_module(module_path)
        _header_fn = getattr(mod, 'get_headers')
    except (ImportError, AttributeError) as e:
        app.logger.error('failed to load header provider %r: %s', module_path, e)
    return _header_fn


def _reset_header_provider():
    """Clear cached header-provider state so the next call reloads.

    Intended for use in tests only.
    """
    global _header_fn, _header_loaded
    _header_fn = None
    _header_loaded = False


def _apply_headers(response, config, expiration_seconds):
    """Apply extension-point HTTP headers to the response.

    response (flask.Response) -- the response object to modify.
    config (ConfigParser) -- the application configuration object.
    expiration_seconds (int) -- cache duration in seconds.
    """
    header_provider = _get_header_provider(config)
    if header_provider is None:
        return
    try:
        headers = header_provider(expiration_seconds)
    except Exception:
        app.logger.exception('header provider error')
        return
    response.headers.update(headers)


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

        waitress-serve --host 127.0.0.1 --port 5544 jotquote.web.viewer:app
        gunicorn --bind 127.0.0.1:5544 jotquote.web.viewer:app  (Linux/Mac only)

    When using a WSGI server directly, this function is not called and the
    WSGI server determines the host and port.  Logging is configured at module
    load time, so the format applies regardless of launch method.
    """

    # Load needed configuration from settings.conf file
    config, _ = api.get_config()
    listen_port = config.get(api.SECTION_WEB, 'port')
    listen_ip = config.get(api.SECTION_WEB, 'ip')

    if not listen_port:
        listen_port = 5544

    if not listen_ip:
        listen_ip = '127.0.0.1'

    from waitress import serve

    serve(app, host=listen_ip, port=int(listen_port))
