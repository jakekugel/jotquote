# -*- coding: utf-8 -*-
# Test quote resolver for integration tests.
# Reads date-to-hash mappings from the TEST_RESOLVER_MAP environment variable.
# Format: "YYYYMMDD=hash,YYYYMMDD=hash"

import os


def resolve(date_str):
    """Return the hash for the given date string, or None.

    date_str (str) -- date in YYYYMMDD format.
    Returns str or None.
    """
    mapping = os.environ.get('TEST_RESOLVER_MAP', '')
    for entry in mapping.split(','):
        if '=' in entry:
            date, hash_val = entry.split('=', 1)
            if date.strip() == date_str:
                return hash_val.strip()
    return None
