"""
Tests for vault_builder.domain.canon.

Coverage cross-validation: ensures all canonical dicts (BOOK_TESTAMENT,
BOOK_GENRE, BOOK_CHAPTER_COUNT, BOOK_ABBREVIATIONS) cover exactly the same
set of books as BOOK_FOLDER — no silent gaps or phantom entries.
"""

import pytest

from vault_builder.domain.canon import (
    BOOK_ABBREVIATIONS,
    BOOK_CHAPTER_COUNT,
    BOOK_FOLDER,
    BOOK_GENRE,
    BOOK_TESTAMENT,
    LXX_TO_MT,
    PSALM_KATHISMA,
    book_file_prefix,
    book_folder_path,
    canonical_book_name,
)

CANONICAL_BOOKS = set(BOOK_FOLDER)


# ---------------------------------------------------------------------------
# Dict coverage — all five dicts must cover exactly BOOK_FOLDER's key set
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,mapping", [
    ("BOOK_TESTAMENT",    BOOK_TESTAMENT),
    ("BOOK_GENRE",        BOOK_GENRE),
    ("BOOK_CHAPTER_COUNT", BOOK_CHAPTER_COUNT),
    ("BOOK_ABBREVIATIONS", BOOK_ABBREVIATIONS),
])
def test_dict_covers_all_books(name, mapping):
    missing = CANONICAL_BOOKS - set(mapping)
    extra   = set(mapping) - CANONICAL_BOOKS
    assert not missing, f"{name} is missing books: {sorted(missing)}"
    assert not extra,   f"{name} has unknown books: {sorted(extra)}"


# ---------------------------------------------------------------------------
# BOOK_CHAPTER_COUNT sanity
# ---------------------------------------------------------------------------

def test_chapter_counts_are_positive():
    bad = {b: n for b, n in BOOK_CHAPTER_COUNT.items() if n < 1}
    assert not bad, f"Non-positive chapter counts: {bad}"


def test_psalms_chapter_count_includes_151():
    assert BOOK_CHAPTER_COUNT["Psalms"] == 151


# ---------------------------------------------------------------------------
# BOOK_TESTAMENT values
# ---------------------------------------------------------------------------

def test_testament_values_are_valid():
    valid = {"OT", "NT", "Deuterocanon"}
    bad = {b: v for b, v in BOOK_TESTAMENT.items() if v not in valid}
    assert not bad, f"Invalid testament values: {bad}"


# ---------------------------------------------------------------------------
# PSALM_KATHISMA coverage
# ---------------------------------------------------------------------------

def test_psalm_kathisma_covers_1_to_150():
    missing = set(range(1, 151)) - set(PSALM_KATHISMA)
    assert not missing, f"PSALM_KATHISMA missing psalms: {sorted(missing)}"


def test_psalm_kathisma_does_not_cover_151():
    assert 151 not in PSALM_KATHISMA, "Psalm 151 is outside the 20-kathisma cycle"


def test_psalm_kathisma_stasis_zero_only_for_118():
    zero_stasis = {ps for ps, (_, s) in PSALM_KATHISMA.items() if s == 0}
    assert zero_stasis == {118}, f"Unexpected stasis=0 psalms: {zero_stasis}"


# ---------------------------------------------------------------------------
# LXX_TO_MT coverage
# ---------------------------------------------------------------------------

def test_lxx_to_mt_covers_1_to_151():
    missing = set(range(1, 152)) - set(LXX_TO_MT)
    assert not missing, f"LXX_TO_MT missing psalms: {sorted(missing)}"


def test_psalm_151_has_no_mt_equivalent():
    assert LXX_TO_MT[151] is None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def test_book_folder_path_format():
    assert book_folder_path("John") == "02 - New Testament/04 - John"
    assert book_folder_path("Genesis") == "01 - Old Testament/01 - Genesis"


def test_book_folder_path_unknown_book_does_not_raise():
    result = book_folder_path("Unknown Book")
    assert "Unknown Book" in result


def test_book_file_prefix_psalms():
    assert book_file_prefix("Psalms") == "Psalm"


def test_book_file_prefix_other_books_unchanged():
    for book in ("Genesis", "John", "Revelation", "Sirach"):
        assert book_file_prefix(book) == book


def test_canonical_book_name_is_inverse_of_prefix():
    assert canonical_book_name("Psalm") == "Psalms"
    assert canonical_book_name("Genesis") == "Genesis"
    assert canonical_book_name("John") == "John"
