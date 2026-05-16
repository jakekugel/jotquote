# -*- coding: utf-8 -*-
# Test about content provider for integration tests.

_SENTINEL = '<h1>Test About Content</h1>'


def get_about_content():
    """Return a minimal HTML fragment for integration testing.

    Returns str (HTML fragment).
    """
    return _SENTINEL
