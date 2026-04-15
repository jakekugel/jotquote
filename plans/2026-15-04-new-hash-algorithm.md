# Plan: New Quote Hashing Algorithm + Hash Stress Test

## Context

The current `Quote.get_hash()` (in `jotquote/api.py`) runs MD5 over the full quote text and returns the first 16 hex characters. The goal is to replace this with an acronym-based algorithm: extract the first (lowercased) letter of every alphabetic word in the quote, hash that condensed string with MD5, and return the same 16-char hex format. A CLI integration stress test will verify that 10,000 distinct quotes produce zero hash collisions.

**Backward compatibility note:** All existing hardcoded hash values will change. This affects test fixtures, resolver examples in docs, and any user-configured `quote_resolver` modules that map dates to specific hashes.

---

## 1. New Algorithm — `Quote.get_hash()` in `jotquote/api.py`

Replace the body with a single-pass traversal:

```python
def get_hash(self):
    # Single-pass: collect first lowercase letter of each alphabetic word.
    # Non-alphabetic characters act as word separators and are otherwise ignored.
    first_letters = []
    in_word = False
    for ch in self.quote:
        if ch.isalpha():
            if not in_word:
                first_letters.append(ch.lower())
                in_word = True
        else:
            in_word = False
    acronym = ''.join(first_letters)
    m = hashlib.md5()
    m.update(acronym.encode('utf-8'))
    return m.hexdigest()[0:16]
```

Edge cases handled:
- Empty quote or no alphabetic characters → `acronym = ""` → consistent hash, no crash.
- Leading punctuation → first word begins at first alphabetic character.
- Digits and hyphens mid-word → treated as word boundaries (non-alpha).

---

## 2. TDD Order

Per CLAUDE.md: write failing test first, confirm failure, then implement.

**Step 1 — Write unit test first** (in `tests/unit/test_api.py`):
```python
def test_get_hash_acronym_algorithm(self):
    """get_hash() uses first-letter-of-each-word acronym, not full text."""
    q = Quote('Hello World foo', 'Author', None, [])
    # acronym = 'hwf', md5('hwf')[:16]
    import hashlib
    expected = hashlib.md5('hwf'.encode()).hexdigest()[:16]
    assert q.get_hash() == expected
```

**Step 2 — Confirm failure** (old MD5-of-full-text returns something different).

**Step 3 — Implement** the new algorithm.

**Step 4 — Update all broken tests** (see below).

---

## 3. Existing Tests That Need Hash Value Updates

After implementing, compute new hashes by running the CLI and update these hardcoded values:

| File | What to update |
|------|----------------|
| `tests/unit/test_api.py` | `test_get_first_match_hash_arg`, `test_settags_by_hash`, `test_settags_hash_not_found_raises` |
| `tests/unit/test_cli.py` | `test_list_by_hash`, `test_list_extended` |
| `tests/unit/test_web_viewer.py` | All tests referencing `'25382c2519fb23bd'` (Ben Franklin quote hash) |
| `tests/integration/test_web_viewer.py` | `test_resolver_date_route`, `test_resolver_date_route_404` |
| `tests/fixtures/test_resolver.py` | Hardcoded hash `'25382c2519fb23bd'` in `TEST_RESOLVER_MAP` |
| `DOCUMENTATION.md` | Any example hash strings shown to users |

The new hash for the Ben Franklin quote `"They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety."` is:
- Acronym: `ttcgueloaltsdnlns`
- New hash: `hashlib.md5(b'ttcgueloaltsdnlns').hexdigest()[:16]` → compute at implementation time.

---

## 4. New Integration Stress Test — `tests/integration/test_cli.py`

Add `test_hash_stress` at the end of the file, after the existing tests.

**Test data strategy:** Use deterministic construction — each quote's 5 words have first letters encoding the index `i` in base-26 — guaranteeing 10,000 unique acronyms and thus zero hash collisions by design (as opposed to relying on random chance).

```python
def _acronym_from_index(i):
    """Return a 5-letter string that uniquely encodes integer i in base-26."""
    letters = []
    for _ in range(5):
        letters.append(chr(ord('a') + i % 26))
        i //= 26
    return ''.join(reversed(letters))


def test_hash_stress(tmp_path):
    """Generate 10,000 quotes with unique acronyms and verify zero hash collisions."""
    # Build a quote file with 10,000 entries using deterministic first-letter encoding
    lines = []
    for i in range(10_000):
        acronym = _acronym_from_index(i)
        # Each quote has 5 words whose first letters spell out the unique acronym
        words = [letter + 'xample' for letter in acronym]
        quote_text = ' '.join(words)
        lines.append('{} | Author {} | | stress'.format(quote_text, i))

    quote_file = tmp_path / 'stress.txt'
    quote_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    env = _make_env(tmp_path, quote_file)

    # Run jotquote list -l and collect all hashes
    hashes = _get_hashes(quote_file, env)

    assert len(hashes) == 10_000, 'Expected 10,000 hashes, got {}'.format(len(hashes))
    assert len(set(hashes)) == 10_000, 'Hash collisions detected: {} unique out of 10,000'.format(len(set(hashes)))
```

`_acronym_from_index` should be placed alongside the other module-level helpers.

---

## 5. Files to Modify

- `jotquote/api.py` — `Quote.get_hash()` method (~lines 108-111)
- `tests/unit/test_api.py` — add 1 new test; update hardcoded hash values in 3 tests
- `tests/unit/test_cli.py` — update hash values in 2 tests
- `tests/unit/test_web_viewer.py` — update `'25382c2519fb23bd'` references
- `tests/integration/test_cli.py` — add `_acronym_from_index()` helper + `test_hash_stress()`
- `tests/integration/test_web_viewer.py` — update `'25382c2519fb23bd'` references
- `tests/fixtures/test_resolver.py` — update hardcoded hash
- `DOCUMENTATION.md` — update any example hash strings

---

## 6. Verification

```bash
# After implementing: confirm new unit test passes
uv run pytest tests/unit/test_api.py -x -q

# Run full test suite; expect failures only in tests with stale hash values
uv run pytest tests/unit/ tests/integration/ -q

# Compute the new Ben Franklin hash to update fixtures:
uv run python -c "from jotquote.api import Quote; q = Quote('They that can give up essential liberty to obtain a little temporary safety deserve neither liberty nor safety.', 'Ben Franklin', None, []); print(q.get_hash())"

# After updating all hash values, confirm all tests pass
uv run pytest tests/unit/ tests/integration/ -q

# Lint
uv run ruff check jotquote/ tests/
```
