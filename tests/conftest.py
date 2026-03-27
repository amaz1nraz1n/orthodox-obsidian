"""
Shared fixtures for vault contract regression tests.
"""
import pytest

from vault_builder.domain.models import Chapter, ChapterNotes, StudyNote, Verse


def _chapter(book: str, number: int, verses: list[tuple[int, str]]) -> Chapter:
    ch = Chapter(book=book, number=number)
    for vnum, text in verses:
        ch.verses[vnum] = Verse(number=vnum, text=text)
    return ch


def _fn(chapter: int, verse: int, content: str) -> StudyNote:
    return StudyNote(verse_number=verse, ref_str=f"{chapter}:{verse}", content=content)


# ── Chapter fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def genesis1_chapter() -> Chapter:
    return _chapter("Genesis", 1, [
        (1, "In the beginning God made heaven and earth."),
        (2, "The earth was invisible and unfinished."),
        (3, 'Then God said, "Let there be light"; and there was light.'),
    ])


@pytest.fixture
def john1_chapter() -> Chapter:
    return _chapter("John", 1, [
        (1, "In the beginning was the Word."),
        (2, "He was in the beginning with God."),
        (3, "All things were made through Him."),
    ])


# ── Notes fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def john1_osb_notes() -> ChapterNotes:
    notes = ChapterNotes(book="John", chapter=1, source="OSB")
    # Deliberately out of verse order to assert sort behaviour
    for v, text in [(3, "Co-Creator note."), (1, "Logos note."), (5, "Darkness note."), (4, "Life note.")]:
        notes.footnotes.append(_fn(1, v, text))
    return notes


@pytest.fixture
def genesis1_lexham_chapter() -> Chapter:
    return _chapter("Genesis", 1, [
        (1, "In the beginning, God created the heavens and the earth."),
        (2, "Now the earth was formless and empty."),
    ])


@pytest.fixture
def genesis1_lexham_notes() -> ChapterNotes:
    """Lexham translation notes for Genesis 1 — deliberately unsorted to assert verse order."""
    notes = ChapterNotes(book="Genesis", chapter=1, source="Lexham")
    notes.translator_notes.append(StudyNote(verse_number=20, ref_str="1:20", content='Lit. "creeping things of living souls"'))
    notes.translator_notes.append(StudyNote(verse_number=1, ref_str="1:1", content='Or "sky"'))
    notes.translator_notes.append(StudyNote(verse_number=6, ref_str="1:6", content='Lit. "of the water and of the water"'))
    return notes


@pytest.fixture
def john1_eob_notes() -> ChapterNotes:
    """EOB endnotes for John 1 — deliberately unsorted to assert verse-order sort."""
    notes = ChapterNotes(book="John", chapter=1, source="EOB")
    notes.footnotes.append(StudyNote(verse_number=14, ref_str="1:14", content="The Word became flesh — Logos incarnation commentary."))
    notes.footnotes.append(StudyNote(verse_number=1,  ref_str="1:1",  content="Logos commentary — Greek philosophical background."))
    notes.footnotes.append(StudyNote(verse_number=3,  ref_str="1:3",  content="All things were made through Him — creation through the Logos."))
    return notes


@pytest.fixture
def psalms50_chapter() -> Chapter:
    return _chapter("Psalms", 50, [
        (1, "Have mercy on me, O God, according to Your great mercy."),
        (2, "According to the multitude of Your compassions, blot out my transgression."),
    ])


@pytest.fixture
def psalms50_notes() -> ChapterNotes:
    notes = ChapterNotes(book="Psalms", chapter=50, source="OSB")
    notes.footnotes.append(_fn(50, 1, "The great penitential psalm."))
    return notes


@pytest.fixture
def john1_net_notes() -> ChapterNotes:
    """NET notes fixture with mixed families across multiple verses (deliberately unsorted)."""
    notes = ChapterNotes(book="John", chapter=1, source="NET")
    # tn (translator's notes) → translator_notes
    notes.translator_notes.append(StudyNote(verse_number=3, ref_str="1:3", content="All things created through him."))
    notes.translator_notes.append(StudyNote(verse_number=1, ref_str="1:1", content="The Word was God's self-expression."))
    # tc (text-critical notes) → variants
    notes.variants.append(StudyNote(verse_number=1, ref_str="1:1", content="Some MSS read 'a god'."))
    # sn (study notes) → footnotes
    notes.footnotes.append(StudyNote(verse_number=5, ref_str="1:5", content="Light vs darkness motif."))
    return notes
