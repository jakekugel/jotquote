# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime
import logging

from flask import Flask, redirect, render_template, request

from jotquote import api

app = Flask(__name__)

_LOG_FORMAT = '%(levelname)s %(name)s:%(message)s'

# Configure the root logger at module load time so the format applies regardless
# of whether the app is launched via 'jotquote webserver' or a WSGI server directly.
logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)

# Named logger for HTTP access lines; propagates to the root handler configured above.
_access_logger = logging.getLogger('jotquote.access')
_access_logger.setLevel(logging.INFO)

STAR_TAGS = ['1star', '2stars', '3stars', '4stars', '5stars']
VISIBILITY_TAGS = ['personal', 'family', 'public']


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
def index():
    config = api.get_config()
    quotefile = config.get(api.APP_NAME, 'quote_file')
    page_title = config.get(api.APP_NAME, 'web_page_title', fallback='jotquote')
    show_stars = config[api.APP_NAME].get('web_show_stars', 'false').lower() == 'true'
    light_fg = config[api.APP_NAME].get('web_light_foreground_color', '#000000')
    light_bg = config[api.APP_NAME].get('web_light_background_color', '#ffffff')
    dark_fg = config[api.APP_NAME].get('web_dark_foreground_color', '#ffffff')
    dark_bg = config[api.APP_NAME].get('web_dark_background_color', '#000000')

    quotes = api.read_quotes(quotefile)
    quote = api.get_first_match(quotes, excluded_tags=','.join(STAR_TAGS), rand=False)

    if quote is None:
        return '<p>No matching quote found.</p>', 200

    quote_tags_set = set(quote.tags)
    star_tag = next((t for t in STAR_TAGS if t in quote_tags_set), '')
    visibility_tag = next((t for t in VISIBILITY_TAGS if t in quote_tags_set), '')
    other_tags = sorted(t for t in quote_tags_set if t not in STAR_TAGS and t not in VISIBILITY_TAGS)
    date1 = datetime.datetime.now().strftime('%A, %B %d, %Y')

    return render_template(
        'review.html',
        quote=quote.quote,
        author=quote.author,
        publication=quote.publication,
        hash=quote.get_hash(),
        date1=date1,
        page_title=page_title,
        show_stars=show_stars,
        stars=quote.get_num_stars(),
        star_tags=STAR_TAGS,
        visibility_tags=VISIBILITY_TAGS,
        star_tag=star_tag,
        visibility_tag=visibility_tag,
        other_tags='\n'.join(other_tags),
        light_fg=light_fg,
        light_bg=light_bg,
        dark_fg=dark_fg,
        dark_bg=dark_bg,
    )


@app.route('/settags', methods=['POST'])
def settags():
    config = api.get_config()
    quotefile = config.get(api.APP_NAME, 'quote_file')
    hash_val = request.form.get('hash')
    star_tag = request.form.get('star_tag', '')
    visibility_tag = request.form.get('visibility_tag', '')
    other_tags_raw = request.form.get('other_tags', '')

    newtags = []
    if star_tag:
        newtags.append(star_tag)
    if visibility_tag:
        newtags.append(visibility_tag)
    for part in other_tags_raw.replace(',', '\n').split('\n'):
        tag = part.strip()
        if tag:
            newtags.append(tag)

    api.settags(quotefile, n=None, hash=hash_val, newtags=newtags)
    return redirect('/')
