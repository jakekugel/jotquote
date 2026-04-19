# -*- coding: utf-8 -*-
#  This file is licensed under the terms of the MIT License.  See the LICENSE
# file in the root of this repository for complete details.

import re

from jotquote import api


def test_get_index_200(editor_client, config):
    """GET / returns HTTP 200."""
    client, quote_file = editor_client
    rv = client.get('/')
    assert rv.status_code == 200


def test_page_title_default(editor_client, config):
    """Default page title is 'jotquote'."""
    client, quote_file = editor_client
    rv = client.get('/')
    assert b'<title>jotquote</title>' in rv.data


def test_page_title_custom(editor_client, config):
    """Custom page_title config is reflected in <title>."""
    config[api.SECTION_WEB]['page_title'] = 'My Editor'
    client, quote_file = editor_client
    rv = client.get('/')
    assert b'<title>My Editor</title>' in rv.data


def test_quote_fields_in_textareas(editor_client, config):
    """Quote, author fields appear in textarea elements."""
    client, quote_file = editor_client
    rv = client.get('/')
    body = rv.data.decode('utf-8')
    assert 'name="quote"' in body
    assert 'name="author"' in body
    assert 'name="publication"' in body


def test_tags_in_textarea(editor_client, config):
    """Tags appear in the tags textarea."""
    client, quote_file = editor_client
    rv = client.get('/')
    body = rv.data.decode('utf-8')
    assert 'name="tags"' in body
    # quotes1.txt quotes have tag 'U'
    assert '>U<' in body


def test_lint_issues_displayed(editor_client, config):
    """Lint issues appear in the page when checks trigger."""
    config[api.SECTION_LINT]['enabled_checks'] = 'no-tags'
    # Create a quote file with a tagless quote
    client, quote_file = editor_client
    with open(quote_file, 'w', encoding='utf-8') as f:
        f.write('A test quote|Test Author||\n')
    rv = client.get('/')
    body = rv.data.decode('utf-8')
    assert 'lint-error' in body


def test_sha256_in_hidden_field(editor_client, config):
    """SHA256 checksum is present in a hidden input."""
    client, quote_file = editor_client
    rv = client.get('/')
    body = rv.data.decode('utf-8')
    sha256 = api.get_sha256(quote_file)
    assert sha256 in body
    assert 'name="sha256"' in body


def test_save_button_disabled(editor_client, config):
    """Save button has the disabled attribute."""
    client, quote_file = editor_client
    rv = client.get('/')
    assert b'id="save-btn" disabled' in rv.data


def test_no_matching_quote(editor_client, config):
    """Empty quote file returns 'No matching quote found'."""
    client, quote_file = editor_client
    with open(quote_file, 'w', encoding='utf-8') as f:
        f.write('')
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'No matching quote found' in rv.data


def test_post_save_redirects(editor_client, config):
    """POST /<line_num> with valid data returns a redirect to /."""
    client, quote_file = editor_client
    quotes = api.read_quotes(quote_file)
    quote = quotes[0]
    line_num = quote.get_line_number()
    sha256 = api.get_sha256(quote_file)

    rv = client.post(
        '/{}'.format(line_num),
        data={
            'quote': quote.quote,
            'author': quote.author,
            'publication': '',
            'tags': ', '.join(quote.tags),
            'sha256': sha256,
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert rv.headers['Location'] == f'/{line_num}'


def test_post_save_updates_file(editor_client, config):
    """After POST, the quote file reflects the updated values."""
    client, quote_file = editor_client
    quotes = api.read_quotes(quote_file)
    quote = quotes[0]
    line_num = quote.get_line_number()
    sha256 = api.get_sha256(quote_file)

    client.post(
        '/{}'.format(line_num),
        data={
            'quote': 'Updated quote text',
            'author': 'Updated Author',
            'publication': 'Updated Pub',
            'tags': 'tag1, tag2',
            'sha256': sha256,
        },
        follow_redirects=False,
    )

    updated_quotes = api.read_quotes(quote_file)
    updated = [q for q in updated_quotes if q.get_line_number() == line_num][0]
    assert updated.quote == 'Updated quote text'
    assert updated.author == 'Updated Author'
    assert updated.publication == 'Updated Pub'
    assert updated.tags == ['tag1', 'tag2']


def test_post_save_sha256_mismatch(editor_client, config):
    """POST with wrong SHA256 renders an error message instead of redirecting."""
    client, quote_file = editor_client
    quotes = api.read_quotes(quote_file)
    quote = quotes[0]
    line_num = quote.get_line_number()

    rv = client.post(
        '/{}'.format(line_num),
        data={
            'quote': quote.quote,
            'author': quote.author,
            'publication': '',
            'tags': ', '.join(quote.tags),
            'sha256': 'bogus_sha256',
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200
    assert b'modified since it was last read' in rv.data


def test_theme_colors(editor_client, config):
    """Dark/light CSS variables are rendered from config."""
    config[api.SECTION_WEB]['dark_foreground_color'] = '#aabbcc'
    config[api.SECTION_WEB]['light_background_color'] = '#ddeeff'
    client, quote_file = editor_client
    rv = client.get('/')
    body = rv.data.decode('utf-8')
    assert '#aabbcc' in body
    assert '#ddeeff' in body


def test_prev_disabled_on_first_quote(editor_client):
    """Previous button is disabled when the first quote is shown."""
    client, quote_file = editor_client
    quotes = api.read_quotes(quote_file)
    first_line = quotes[0].get_line_number()
    rv = client.get(f'/{first_line}')
    body = rv.data.decode('utf-8')
    assert re.search(r'id="prev-btn"[^>]*disabled', body)


def test_next_disabled_on_last_quote(editor_client):
    """Next button is disabled when the last quote is shown."""
    client, quote_file = editor_client
    quotes = api.read_quotes(quote_file)
    last_line = quotes[-1].get_line_number()
    rv = client.get(f'/{last_line}')
    body = rv.data.decode('utf-8')
    assert re.search(r'id="next-btn"[^>]*disabled', body)


def test_nav_buttons_enabled_on_middle_quote(editor_client):
    """Both Previous and Next are enabled for a middle quote."""
    client, quote_file = editor_client
    quotes = api.read_quotes(quote_file)
    # quotes1.txt has 4 quotes; pick the second one
    mid_line = quotes[1].get_line_number()
    rv = client.get(f'/{mid_line}')
    assert rv.status_code == 200
    body = rv.data.decode('utf-8')
    prev_idx = body.index('id="prev-btn"')
    next_idx = body.index('id="next-btn"')
    assert 'disabled' not in body[prev_idx : prev_idx + 100]
    assert 'disabled' not in body[next_idx : next_idx + 100]


def test_get_line_num_shows_correct_quote(editor_client):
    """GET /<line_num> renders the quote at that line number."""
    client, quote_file = editor_client
    quotes = api.read_quotes(quote_file)
    quote = quotes[1]
    rv = client.get(f'/{quote.get_line_number()}')
    assert rv.status_code == 200
    # Check the author name (no special characters to worry about in escaping)
    assert quote.author.encode('utf-8') in rv.data


def test_get_line_num_invalid_returns_404(editor_client):
    """GET /<line_num> with a non-existent line number returns 404."""
    client, quote_file = editor_client
    rv = client.get('/99999')
    assert rv.status_code == 404


def test_next_line_num_in_button(editor_client):
    """Next button href points to the next quote's line number."""
    client, quote_file = editor_client
    quotes = api.read_quotes(quote_file)
    first_line = quotes[0].get_line_number()
    second_line = quotes[1].get_line_number()
    rv = client.get(f'/{first_line}')
    body = rv.data.decode('utf-8')
    assert f"window.location='/{second_line}'" in body


def test_prev_line_num_in_button(editor_client):
    """Previous button href points to the previous quote's line number."""
    client, quote_file = editor_client
    quotes = api.read_quotes(quote_file)
    second_line = quotes[1].get_line_number()
    first_line = quotes[0].get_line_number()
    rv = client.get(f'/{second_line}')
    body = rv.data.decode('utf-8')
    assert f"window.location='/{first_line}'" in body


# ---------------------------------------------------------------------------
# Error-navigation buttons
# ---------------------------------------------------------------------------
# Quote file layout used in these tests (no-tags check enabled):
#   line 1: no tags  → lint error
#   line 2: has tags → clean
#   line 3: no tags  → lint error
#   line 4: has tags → clean


def _write_error_nav_quotes(quote_file):
    """Write a 4-quote file where lines 1 and 3 have no-tags lint errors."""
    with open(quote_file, 'w', encoding='utf-8') as f:
        f.write('Quote one | Author One | |\n')
        f.write('Quote two | Author Two | | tag1\n')
        f.write('Quote three | Author Three | |\n')
        f.write('Quote four | Author Four | | tag2\n')


def test_next_error_from_clean_quote(editor_client, config):
    """Next with error jumps to the first quote after current that has a lint error."""
    config[api.SECTION_LINT]['enabled_checks'] = 'no-tags'
    client, quote_file = editor_client
    _write_error_nav_quotes(quote_file)
    quotes = api.read_quotes(quote_file)
    # Start at line 2 (clean); next error should be line 3
    line2 = quotes[1].get_line_number()
    line3 = quotes[2].get_line_number()
    rv = client.get(f'/{line2}')
    body = rv.data.decode('utf-8')
    assert f"window.location='/{line3}'" in body


def test_prev_error_from_clean_quote(editor_client, config):
    """Prev with error jumps to the nearest quote before current that has a lint error."""
    config[api.SECTION_LINT]['enabled_checks'] = 'no-tags'
    client, quote_file = editor_client
    _write_error_nav_quotes(quote_file)
    quotes = api.read_quotes(quote_file)
    # Start at line 4 (clean); prev error should be line 3
    line4 = quotes[3].get_line_number()
    line3 = quotes[2].get_line_number()
    rv = client.get(f'/{line4}')
    body = rv.data.decode('utf-8')
    assert f"window.location='/{line3}'" in body


def test_next_error_disabled_when_none_after(editor_client, config):
    """Next with error is disabled when no later quote has a lint error."""
    config[api.SECTION_LINT]['enabled_checks'] = 'no-tags'
    client, quote_file = editor_client
    _write_error_nav_quotes(quote_file)
    quotes = api.read_quotes(quote_file)
    # Start at line 3 (error); no error exists after line 3 (line 4 is clean)
    line3 = quotes[2].get_line_number()
    rv = client.get(f'/{line3}')
    body = rv.data.decode('utf-8')
    assert re.search(r'id="next-error-btn"[^>]*disabled', body)


def test_prev_error_disabled_when_none_before(editor_client, config):
    """Prev with error is disabled when no earlier quote has a lint error."""
    config[api.SECTION_LINT]['enabled_checks'] = 'no-tags'
    client, quote_file = editor_client
    _write_error_nav_quotes(quote_file)
    quotes = api.read_quotes(quote_file)
    # Start at line 1 (error); no error exists before line 1
    line1 = quotes[0].get_line_number()
    rv = client.get(f'/{line1}')
    body = rv.data.decode('utf-8')
    assert re.search(r'id="prev-error-btn"[^>]*disabled', body)


def test_error_buttons_both_disabled_when_no_errors(editor_client, config):
    """Both error-nav buttons are disabled when no quotes have lint errors."""
    config[api.SECTION_LINT]['enabled_checks'] = 'no-tags'
    client, quote_file = editor_client
    # All quotes have tags — no lint errors
    with open(quote_file, 'w', encoding='utf-8') as f:
        f.write('Quote one | Author | | tag1\n')
        f.write('Quote two | Author | | tag2\n')
    quotes = api.read_quotes(quote_file)
    rv = client.get(f'/{quotes[0].get_line_number()}')
    body = rv.data.decode('utf-8')
    assert re.search(r'id="prev-error-btn"[^>]*disabled', body)
    assert re.search(r'id="next-error-btn"[^>]*disabled', body)


def test_error_nav_skips_current_quote(editor_client, config):
    """Error-nav buttons do not navigate to the current quote, even if it has an error."""
    config[api.SECTION_LINT]['enabled_checks'] = 'no-tags'
    client, quote_file = editor_client
    _write_error_nav_quotes(quote_file)
    quotes = api.read_quotes(quote_file)
    # Start at line 1 (error); next error should skip self and land on line 3
    line1 = quotes[0].get_line_number()
    line3 = quotes[2].get_line_number()
    rv = client.get(f'/{line1}')
    body = rv.data.decode('utf-8')
    assert f"window.location='/{line3}'" in body


# ---------------------------------------------------------------------------
# Lint cache tests
# ---------------------------------------------------------------------------


def test_lint_cache_hit_avoids_relint(editor_client, config, monkeypatch):
    """Two GET requests without file change should only lint once (cache hit)."""
    from unittest.mock import patch

    from jotquote.web import editor as web_editor

    client, quote_file = editor_client
    with patch.object(web_editor.lint, 'lint_quotes', wraps=web_editor.lint.lint_quotes) as mock_lint:
        client.get('/')
        client.get('/')
        assert mock_lint.call_count == 1


def test_lint_cache_miss_on_file_change(editor_client, config, monkeypatch):
    """Modifying the file between requests causes a cache miss and re-lint."""
    from unittest.mock import patch

    from jotquote.web import editor as web_editor

    client, quote_file = editor_client
    with patch.object(web_editor.lint, 'lint_quotes', wraps=web_editor.lint.lint_quotes) as mock_lint:
        client.get('/')
        assert mock_lint.call_count == 1
        # Modify the file
        with open(quote_file, 'a', encoding='utf-8') as f:
            f.write('New quote | New Author | | newtag\n')
        client.get('/')
        assert mock_lint.call_count == 2


def test_lint_cache_miss_on_check_change(editor_client, config, monkeypatch):
    """Changing enabled checks causes a cache miss and re-lint."""
    from unittest.mock import patch

    from jotquote.web import editor as web_editor

    client, quote_file = editor_client
    config[api.SECTION_LINT]['enabled_checks'] = 'no-tags'
    with patch.object(web_editor.lint, 'lint_quotes', wraps=web_editor.lint.lint_quotes) as mock_lint:
        client.get('/')
        assert mock_lint.call_count == 1
        config[api.SECTION_LINT]['enabled_checks'] = 'no-author'
        client.get('/')
        assert mock_lint.call_count == 2
