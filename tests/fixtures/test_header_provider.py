# -*- coding: utf-8 -*-
# Test header provider for integration tests.


def get_headers(max_age):
    """Return Cache-Control and a custom header for testing.

    max_age (int) -- cache duration in seconds.
    Returns dict mapping header names to header values.
    """
    return {
        'Cache-Control': f'public, max-age={max_age}',
        'X-Custom-Test': 'hello',
    }
