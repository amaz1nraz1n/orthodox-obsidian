"""Tests for vault_builder.domain.models — Phase 1 taxonomy expansion."""

import pytest
from vault_builder.domain.models import (
    BookIntro,
    ChapterIntro,
    ChapterNotes,
    PartIntro,
    StudyNote,
)


# ── New dataclass instantiation ───────────────────────────────────────────────

def test_book_intro_instantiation():
    intro = BookIntro(book="Genesis", source="OSB", content="# Genesis\n\nIn the beginning...")
    assert intro.book == "Genesis"
    assert intro.source == "OSB"
    assert "beginning" in intro.content


def test_chapter_intro_instantiation():
    intro = ChapterIntro(book="John", chapter=1, source="DBH", content="The Prologue...")
    assert intro.book == "John"
    assert intro.chapter == 1
    assert intro.source == "DBH"
    assert intro.content == "The Prologue..."


def test_part_intro_instantiation():
    intro = PartIntro(part_name="Torah", source="Robert Alter", content="The five books of Moses...")
    assert intro.part_name == "Torah"
    assert intro.source == "Robert Alter"
    assert "Moses" in intro.content


# ── ChapterNotes new field defaults ──────────────────────────────────────────

def test_chapter_notes_new_fields_default_empty():
    notes = ChapterNotes(book="John", chapter=1, source="OSB")
    assert notes.translator_notes == []
    assert notes.alternatives == []
    assert notes.background_notes == []
    assert notes.parallel_passages == []
    assert notes.chapter_intro is None


def test_chapter_notes_existing_fields_still_default_empty():
    notes = ChapterNotes(book="John", chapter=1, source="OSB")
    assert notes.footnotes == []
    assert notes.variants == []
    assert notes.cross_references == []
    assert notes.liturgical == []
    assert notes.citations == []
    assert notes.articles == []


def test_chapter_notes_chapter_intro_field():
    intro = ChapterIntro(book="John", chapter=1, source="DBH", content="The Prologue...")
    notes = ChapterNotes(book="John", chapter=1, source="DBH", chapter_intro=intro)
    assert notes.chapter_intro is intro
    assert notes.chapter_intro.content == "The Prologue..."


# ── New sorted_ methods ───────────────────────────────────────────────────────

def _make_note(verse: int, ref: str = None) -> StudyNote:
    return StudyNote(verse_number=verse, ref_str=ref or f"1:{verse}", content=f"Note for v{verse}")


def test_sorted_translator_notes():
    notes = ChapterNotes(book="John", chapter=1, source="NET")
    notes.translator_notes = [_make_note(5), _make_note(2), _make_note(8)]
    result = notes.sorted_translator_notes()
    assert [n.verse_number for n in result] == [2, 5, 8]


def test_sorted_alternatives():
    notes = ChapterNotes(book="Genesis", chapter=1, source="OSB")
    notes.alternatives = [_make_note(3), _make_note(1)]
    result = notes.sorted_alternatives()
    assert [n.verse_number for n in result] == [1, 3]


def test_sorted_background_notes():
    notes = ChapterNotes(book="Genesis", chapter=1, source="OSB")
    notes.background_notes = [_make_note(10), _make_note(4), _make_note(7)]
    result = notes.sorted_background_notes()
    assert [n.verse_number for n in result] == [4, 7, 10]


def test_sorted_parallel_passages():
    notes = ChapterNotes(book="Matthew", chapter=3, source="OSB")
    notes.parallel_passages = [_make_note(6), _make_note(1)]
    result = notes.sorted_parallel_passages()
    assert [n.verse_number for n in result] == [1, 6]


def test_sorted_methods_return_empty_list_when_no_notes():
    notes = ChapterNotes(book="John", chapter=1, source="OSB")
    assert notes.sorted_translator_notes() == []
    assert notes.sorted_alternatives() == []
    assert notes.sorted_background_notes() == []
    assert notes.sorted_parallel_passages() == []


# ── Backward compatibility ────────────────────────────────────────────────────

def test_existing_chapter_notes_construction_unchanged():
    note = _make_note(1)
    notes = ChapterNotes(
        book="John", chapter=1, source="OSB",
        footnotes=[note],
        variants=[note],
        cross_references=[note],
        citations=[note],
        liturgical=[note],
    )
    assert len(notes.footnotes) == 1
    assert len(notes.variants) == 1
    assert len(notes.cross_references) == 1
    assert len(notes.citations) == 1
    assert len(notes.liturgical) == 1
