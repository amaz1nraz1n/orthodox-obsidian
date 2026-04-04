"""
Tests for DbhEpubSource — DBH NT EPUB adapter.

Covers: verse parsing, GOD/god typography, footnote mapping, note type
routing, single-chapter books, and sample-scope filtering.
"""
import re
import pytest

EPUB_PATH = "./source_files/New Testament/The New Testament_ A Translation -- David Bentley Hart.epub"

_SAMPLE: set[tuple[str, int]] = {
    ("Matthew", 1),
    ("John", 1),
    ("John", 3),
    ("Romans", 8),
    ("Revelation", 1),
    ("Philemon", 1),
    ("Jude", 1),
}


@pytest.fixture(scope="module")
def source():
    from vault_builder.adapters.sources.dbh_epub import DbhEpubSource
    return DbhEpubSource(EPUB_PATH, sample_only=True, sample_chapters=_SAMPLE)


@pytest.fixture(scope="module")
def books(source):
    return {b.name: b for b in source.read_text()}


@pytest.fixture(scope="module")
def notes_list(source):
    return list(source.read_notes())


# ── Verse count ───────────────────────────────────────────────────────────────

def test_john_1_verse_count(books):
    """John 1 has 51 verses in the canonical text."""
    ch = books["John"].chapters[1]
    assert len(ch.verses) == 51


def test_matthew_1_verse_count(books):
    """Matthew 1 has 25 verses."""
    ch = books["Matthew"].chapters[1]
    assert len(ch.verses) == 25


def test_revelation_1_verse_count(books):
    """Revelation 1 has 20 verses."""
    ch = books["Revelation"].chapters[1]
    assert len(ch.verses) == 20


# ── Known verse text ──────────────────────────────────────────────────────────

def test_matthew_1_1(books):
    text = books["Matthew"].chapters[1].verses[1].text
    assert "record of the lineage" in text
    assert "Jesus the Anointed" in text


def test_john_1_1_logos(books):
    """Hart renders 'In the origin' not 'In the beginning'."""
    text = books["John"].chapters[1].verses[1].text
    assert "origin" in text
    assert "Logos" in text


def test_john_1_1_god_typography(books):
    """GOD (ὁ θεός) renders as uppercase GOD; articular 'god' renders lowercase."""
    text = books["John"].chapters[1].verses[1].text
    assert "GOD" in text
    assert "god" in text


def test_john_3_16(books):
    """Hart's famous rendering: 'cosmos', 'life of the Age', 'the Son, the only one'."""
    text = books["John"].chapters[3].verses[16].text
    assert "cosmos" in text
    assert "life of the Age" in text


def test_romans_8_contains_verses(books):
    ch = books["Romans"].chapters[8]
    assert len(ch.verses) >= 30


def test_revelation_1_1(books):
    text = books["Revelation"].chapters[1].verses[1].text
    assert "revelation" in text.lower() or "Revelation" in text


# ── Single-chapter books ──────────────────────────────────────────────────────

def test_philemon_extracted_as_chapter_1(books):
    """Philemon has no h3 chapter heading; treated as implicit chapter 1."""
    assert "Philemon" in books
    assert 1 in books["Philemon"].chapters


def test_philemon_verse_1(books):
    text = books["Philemon"].chapters[1].verses[1].text
    assert "Paul" in text


def test_jude_extracted_as_chapter_1(books):
    """Jude (Hart: 'Letter of Judas') maps to canonical 'Jude', chapter 1."""
    assert "Jude" in books
    assert 1 in books["Jude"].chapters


# ── No verse merge ────────────────────────────────────────────────────────────

def test_no_verse_merge_john_1(books):
    """No verse body should contain a bare superscript verse number pattern
    indicating a merge artefact like '2This one was present...'."""
    ch = books["John"].chapters[1]
    for vnum, verse in ch.verses.items():
        # A merged verse would start with a digit immediately before a capital
        assert not re.match(r"^\d+[A-Z]", verse.text), (
            f"Possible verse merge in John 1:{vnum}: {verse.text[:60]!r}"
        )


def test_no_verse_merge_matthew_1(books):
    ch = books["Matthew"].chapters[1]
    for vnum, verse in ch.verses.items():
        assert not re.match(r"^\d+[A-Z]", verse.text), (
            f"Possible verse merge in Matthew 1:{vnum}: {verse.text[:60]!r}"
        )


# ── Footnote type routing ─────────────────────────────────────────────────────

def test_all_notes_are_translator_type(notes_list):
    """All DBH footnotes are translator rationale → NoteType.TRANSLATOR."""
    from vault_builder.domain.models import NoteType
    for chapter_notes in notes_list:
        for note in chapter_notes.translator_notes:
            assert note is not None
        # No notes should appear in other slots
        assert not chapter_notes.footnotes, \
            f"Unexpected FOOTNOTE slot notes in {chapter_notes.book} {chapter_notes.chapter}"
        assert not chapter_notes.alternatives, \
            f"Unexpected ALTERNATIVE slot notes in {chapter_notes.book} {chapter_notes.chapter}"


def test_notes_exist_for_john_1(notes_list):
    """John 1 has 34 footnotes; at least some should be in sample."""
    john1_notes = [n for n in notes_list if n.book == "John" and n.chapter == 1]
    assert john1_notes, "No notes found for John 1"
    assert john1_notes[0].translator_notes, "John 1 notes should have translator_notes"


def test_notes_body_is_non_empty(notes_list):
    """No translator note should have an empty body."""
    for chapter_notes in notes_list:
        for note in chapter_notes.translator_notes:
            assert note.content.strip(), (
                f"Empty note body in {chapter_notes.book} {chapter_notes.chapter} v{note.verse_number}"
            )


# ── ChapterNotes source label ─────────────────────────────────────────────────

def test_notes_source_label(notes_list):
    for cn in notes_list:
        assert cn.source == "DBH"


# ── Sample scope ─────────────────────────────────────────────────────────────

def test_only_sample_books_returned(books):
    sample_books = {b for b, _ in _SAMPLE}
    for name in books:
        assert name in sample_books, f"Out-of-scope book returned: {name}"


def test_read_intros_returns_empty(source):
    assert list(source.read_intros()) == []
