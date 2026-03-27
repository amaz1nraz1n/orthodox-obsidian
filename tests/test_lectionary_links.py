"""
Contract tests for lectionary pericope wikilink generation.

Phase 1 gate: pericope links resolve correctly + cross-chapter range safety.
"""
import pytest
from extract_lectionary import pericope_to_wikilinks, OCMC_BOOK_TO_CANON


# ── Book name mapping ────────────────────────────────────────────────────────

def test_book_mapping_corinthians():
    assert OCMC_BOOK_TO_CANON["1 Corinthians"] == "I Corinthians"

def test_book_mapping_john():
    assert OCMC_BOOK_TO_CANON["John"] == "John"

def test_book_mapping_all_present():
    ocmc_books = [
        "1 Corinthians", "1 John", "1 Peter", "1 Thessalonians", "1 Timothy",
        "2 Corinthians", "2 John", "2 Peter", "2 Thessalonians", "2 Timothy",
        "3 John", "Acts", "Colossians", "Ephesians", "Galatians", "Hebrews",
        "James", "John", "Jude", "Luke", "Mark", "Matthew", "Philemon",
        "Philippians", "Romans", "Titus",
    ]
    for b in ocmc_books:
        assert b in OCMC_BOOK_TO_CANON, f"Missing mapping for {b!r}"


# ── Single block: same chapter ───────────────────────────────────────────────

def test_single_block_same_chapter():
    # 1 Corinthians 1:1-9 → [[I Corinthians 1#v1|1:1-9]]
    blocks = [{"book": "I Corinthians", "chapter": 1, "verse_from": 1, "verse_to": 9}]
    visible, hidden = pericope_to_wikilinks(blocks)
    assert visible == "[[I Corinthians 1#v1|1:1-9]]"

def test_single_block_single_verse():
    blocks = [{"book": "John", "chapter": 1, "verse_from": 1, "verse_to": 1}]
    visible, hidden = pericope_to_wikilinks(blocks)
    assert visible == "[[John 1#v1|1:1]]"


# ── Multi-block: cross-chapter ───────────────────────────────────────────────

def test_cross_chapter_same_book():
    # 1 Cor 1:18-31; 2:1-2 → [[I Corinthians 1#v18|1:18]]–[[I Corinthians 2#v2|2:2]]
    blocks = [
        {"book": "I Corinthians", "chapter": 1, "verse_from": 18, "verse_to": 31},
        {"book": "I Corinthians", "chapter": 2, "verse_from": 1, "verse_to": 2},
    ]
    visible, hidden = pericope_to_wikilinks(blocks)
    assert "[[I Corinthians 1#v18|" in visible
    assert "[[I Corinthians 2#v2|" in visible

def test_cross_chapter_hidden_range_links():
    """Intermediate verses in cross-chapter pericope get hidden wikilinks."""
    blocks = [
        {"book": "John", "chapter": 1, "verse_from": 1, "verse_to": 3},
        {"book": "John", "chapter": 2, "verse_from": 1, "verse_to": 2},
    ]
    visible, hidden = pericope_to_wikilinks(blocks)
    # Hidden block must contain wikilinks for v2, v3 (v1 is in visible), v2 of ch2 (if to > 1)
    assert "[[John 1#v2]]" in hidden
    assert "[[John 1#v3]]" in hidden
    assert "[[John 2#v2]]" in hidden

def test_single_block_hidden_range_links():
    """Intermediate verses within a single block get hidden links."""
    blocks = [{"book": "Romans", "chapter": 8, "verse_from": 1, "verse_to": 5}]
    visible, hidden = pericope_to_wikilinks(blocks)
    assert "[[Romans 8#v2]]" in hidden
    assert "[[Romans 8#v3]]" in hidden
    assert "[[Romans 8#v4]]" in hidden
    assert "[[Romans 8#v5]]" in hidden

def test_single_verse_no_hidden_links():
    """Single verse has no hidden links."""
    blocks = [{"book": "John", "chapter": 3, "verse_from": 16, "verse_to": 16}]
    visible, hidden = pericope_to_wikilinks(blocks)
    assert hidden == ""
