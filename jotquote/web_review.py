# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import datetime

from flask import Flask, redirect, render_template, request

from jotquote import api

app = Flask(__name__)

STAR_TAGS = ["1star", "2stars", "3stars", "4stars", "5stars"]
VISIBILITY_TAGS = ["personal", "family", "public"]


@app.route("/")
def index():
    config = api.get_config()
    quotefile = config.get(api.APP_NAME, "quote_file")
    page_title = config.get(api.APP_NAME, "web_page_title", fallback="jotquote")
    show_stars = config[api.APP_NAME].get("web_show_stars", "false").lower() == "true"

    quotes = api.read_quotes(quotefile)
    quote = api.get_first_match(quotes, excluded_tags=",".join(STAR_TAGS), rand=False)

    if quote is None:
        return "<p>No matching quote found.</p>", 200

    quote_tags_set = set(quote.tags)
    star_tag = next((t for t in STAR_TAGS if t in quote_tags_set), "")
    visibility_tag = next((t for t in VISIBILITY_TAGS if t in quote_tags_set), "")
    other_tags = sorted(t for t in quote_tags_set if t not in STAR_TAGS and t not in VISIBILITY_TAGS)
    date1 = datetime.datetime.now().strftime("%A, %B %d, %Y")

    return render_template(
        "review.html",
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
        other_tags="\n".join(other_tags),
    )


@app.route("/settags", methods=["POST"])
def settags():
    config = api.get_config()
    quotefile = config.get(api.APP_NAME, "quote_file")
    hash_val = request.form.get("hash")
    star_tag = request.form.get("star_tag", "")
    visibility_tag = request.form.get("visibility_tag", "")
    other_tags_raw = request.form.get("other_tags", "")

    newtags = []
    if star_tag:
        newtags.append(star_tag)
    if visibility_tag:
        newtags.append(visibility_tag)
    for part in other_tags_raw.replace(",", "\n").split("\n"):
        tag = part.strip()
        if tag:
            newtags.append(tag)

    api.settags(quotefile, n=None, hash=hash_val, newtags=newtags)
    return redirect("/")
