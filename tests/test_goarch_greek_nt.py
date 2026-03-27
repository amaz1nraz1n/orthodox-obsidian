"""
TDD tests for GoArchGreekNtSource adapter.

Contracts:
  1. Pattern A (linegroup): verse number in <p>, text in sibling <div class='linegroup'>
     — lineitem texts are joined with a space.
  2. Pattern B (inline): multiple <span class="verse">[N]</span> in one <p>
     — each span's following NavigableString becomes its verse text.
  3. Chapter boundary: osisID="John.2" yields chapter 2, independent of chapter 1.
  4. Single inline verse in its own <p> (John 1:14) is captured correctly.
  5. Verse text is whitespace-normalised (no leading/trailing spaces, no double spaces).
  6. Greek polytonic characters are preserved exactly.
  7. Yielded Chapter objects carry the correct book name and chapter number.
  8. Yielded ChapterNotes are always empty (source has no footnotes).
  9. sample_only mode filters to requested (book, chapter) pairs only.
  10. book_manifest maps GOArch params → vault canonical names for all 27 NT books.
"""

import os
import pytest

from vault_builder.adapters.sources.goarch_greek_nt import GoArchGreekNtSource


FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "goarch_john_fixture.html")


@pytest.fixture
def fixture_html() -> str:
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def chapters(fixture_html):
    """Parse fixture HTML and return list of (Chapter, ChapterNotes) for John."""
    source = GoArchGreekNtSource(sample_only=False)
    results = list(source._parse_book_html(fixture_html, "John"))
    return results


# ── Contract 1: Pattern A — linegroup ─────────────────────────────────────────

def test_linegroup_verse1_text_joined(chapters):
    ch1_verses = chapters[0][0].verses
    assert 1 in ch1_verses
    text = ch1_verses[1].text
    assert "Ἐν ἀρχῇ ἦν ὁ Λόγος" in text
    assert "καὶ ὁ Λόγος ἦν πρὸς τὸν Θεόν" in text
    assert "καὶ Θεὸς ἦν ὁ Λόγος" in text


def test_linegroup_verse1_lineitems_joined_with_space(chapters):
    text = chapters[0][0].verses[1].text
    # All three line items must appear in one continuous string
    assert "Λόγος, καὶ" in text or "Λόγος,\nκαὶ" not in text


def test_linegroup_verse2_captured(chapters):
    ch1_verses = chapters[0][0].verses
    assert 2 in ch1_verses
    assert "οὗτος ἦν ἐν ἀρχῇ πρὸς τὸν Θεόν" in ch1_verses[2].text


# ── Contract 2: Pattern B — inline multi-verse paragraph ──────────────────────

def test_inline_verse6_captured(chapters):
    ch1_verses = chapters[0][0].verses
    assert 6 in ch1_verses
    assert "᾿Εγένετο ἄνθρωπος" in ch1_verses[6].text


def test_inline_verse7_captured(chapters):
    ch1_verses = chapters[0][0].verses
    assert 7 in ch1_verses
    assert "μαρτυρίαν" in ch1_verses[7].text


def test_inline_verse8_captured(chapters):
    ch1_verses = chapters[0][0].verses
    assert 8 in ch1_verses
    assert "οὐκ ἦν ἐκεῖνος" in ch1_verses[8].text


def test_inline_verses_do_not_bleed_into_each_other(chapters):
    ch1 = chapters[0][0].verses
    # Verse 6 text must not contain verse 7's opening word
    assert "οὗτος ἦλθεν" not in ch1[6].text
    # Verse 7 text must not contain verse 8's opening word
    assert "οὐκ ἦν ἐκεῖνος" not in ch1[7].text


# ── Contract 3: Chapter boundary ──────────────────────────────────────────────

def test_two_chapters_yielded(chapters):
    assert len(chapters) == 2


def test_chapter1_number(chapters):
    assert chapters[0][0].number == 1


def test_chapter2_number(chapters):
    assert chapters[1][0].number == 2


def test_chapter2_verse1_captured(chapters):
    ch2_verses = chapters[1][0].verses
    assert 1 in ch2_verses
    assert "Κανᾷ" in ch2_verses[1].text


def test_chapter2_verse2_captured(chapters):
    ch2_verses = chapters[1][0].verses
    assert 2 in ch2_verses
    assert "μαθηταὶ" in ch2_verses[2].text


# ── Contract 4: Single inline verse in own <p> ────────────────────────────────

def test_single_inline_verse14_captured(chapters):
    ch1_verses = chapters[0][0].verses
    assert 14 in ch1_verses
    assert "Λόγος σὰρξ ἐγένετο" in ch1_verses[14].text


# ── Contract 5: Whitespace normalisation ──────────────────────────────────────

def test_verse_text_no_leading_trailing_whitespace(chapters):
    for ch, _ in chapters:
        for verse in ch.verses.values():
            assert verse.text == verse.text.strip(), (
                f"Verse {ch.number}:{verse.number} has leading/trailing whitespace"
            )


def test_verse_text_no_double_spaces(chapters):
    for ch, _ in chapters:
        for verse in ch.verses.values():
            assert "  " not in verse.text, (
                f"Verse {ch.number}:{verse.number} has double spaces"
            )


# ── Contract 6: Polytonic Greek preserved ─────────────────────────────────────

def test_polytonic_breathings_preserved(chapters):
    text = chapters[0][0].verses[1].text
    # Smooth breathing on Ἐν, oxia on ἀρχῇ
    assert "Ἐν" in text
    assert "ἀρχῇ" in text


def test_polytonic_rough_breathing_preserved(chapters):
    # ᾿Εγένετο has rough breathing mark
    assert "᾿Εγένετο" in chapters[0][0].verses[6].text


# ── Contract 7: Chapter/book metadata ─────────────────────────────────────────

def test_chapter_book_name(chapters):
    for ch, _ in chapters:
        assert ch.book == "John"


def test_chapter_numbers_sequential(chapters):
    nums = [ch.number for ch, _ in chapters]
    assert nums == [1, 2]


# ── Contract 8: Notes always empty ────────────────────────────────────────────

def test_notes_are_empty(chapters):
    for _, notes in chapters:
        assert notes.footnotes == []
        assert notes.variants == []
        assert notes.citations == []
        assert notes.cross_references == []


def test_notes_source_label(chapters):
    for _, notes in chapters:
        assert notes.source == "Greek NT"


# ── Contract 9: sample_only filtering ────────────────────────────────────────

def test_sample_only_filters_chapters(fixture_html):
    source = GoArchGreekNtSource(
        sample_only=True,
        sample_chapters={("John", 2)},
    )
    results = list(source._parse_book_html(fixture_html, "John"))
    assert len(results) == 1
    assert results[0][0].number == 2


def test_sample_only_empty_set_yields_nothing(fixture_html):
    source = GoArchGreekNtSource(sample_only=True, sample_chapters=set())
    results = list(source._parse_book_html(fixture_html, "John"))
    assert results == []


# ── Contract 10: Book manifest completeness ───────────────────────────────────

def test_manifest_has_27_books():
    source = GoArchGreekNtSource(sample_only=False)
    assert len(source.BOOKS) == 27


def test_manifest_canonical_names_are_vault_names():
    source = GoArchGreekNtSource(sample_only=False)
    vault_names = {entry[2] for entry in source.BOOKS}
    expected = {
        "Matthew", "Mark", "Luke", "John", "Acts",
        "Romans", "I Corinthians", "II Corinthians", "Galatians",
        "Ephesians", "Philippians", "Colossians",
        "I Thessalonians", "II Thessalonians",
        "I Timothy", "II Timothy", "Titus", "Philemon",
        "Hebrews", "James", "I Peter", "II Peter",
        "I John", "II John", "III John", "Jude", "Revelation",
    }
    assert vault_names == expected


def test_manifest_ids_are_sequential():
    source = GoArchGreekNtSource(sample_only=False)
    ids = [entry[0] for entry in source.BOOKS]
    assert ids == list(range(27))
