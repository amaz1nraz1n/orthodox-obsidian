"""
Core domain models for Orthodox Scripture vault building.

These are plain data objects with no dependencies on any specific source format
or output format. All extractors produce these; all renderers consume them.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class NoteType(str, Enum):
    FOOTNOTE =    "footnote"         # Study/commentary note
    VARIANT =     "variant"          # Textual variant / manuscript difference
    CROSS_REF =   "cross_reference"  # Cross-reference to another passage
    LITURGICAL =  "liturgical"       # Liturgical usage note
    CITATION =    "citation"         # Patristic citation
    TRANSLATOR =  "translator_note"  # Linguistic or translation note
    ALTERNATIVE = "alternative"      # Alternative reading
    BACKGROUND =  "background_note"  # Historical/geographical context
    PARALLEL =    "parallel_passage" # Synoptic/parallel passage link


@dataclass
class Verse:
    number: int
    text: str


@dataclass
class Chapter:
    book: str
    number: int
    verses: dict[int, Verse] = field(default_factory=dict)
    pericopes: dict[int, str] = field(default_factory=dict)  # first_verse → title
    after_markers: dict[int, list[str]] = field(default_factory=dict)  # verse_num → markers after that verse (e.g. Diapsalma/Selah)

    def sorted_verses(self) -> list[Verse]:
        return [self.verses[n] for n in sorted(self.verses)]


@dataclass
class Book:
    name: str
    chapters: dict[int, Chapter] = field(default_factory=dict)

    def max_chapter(self) -> int:
        return max(self.chapters.keys()) if self.chapters else 0


@dataclass
class StudyNote:
    """A single study annotation associated with one or more verses."""
    verse_number: int
    ref_str: str              # e.g. "1:14" or "1:14-16"
    content: str              # Markdown-formatted note body
    verse_end: int | None = None  # End verse when the note spans a range (e.g. 1:3–5)
    anchor_id: str | None = None  # Stable identifier for per-callout deep-linking (e.g. EPUB fragment ID "fn4706")


@dataclass
class StudyArticle:
    """An inline thematic article (e.g. OSB gray-box study article)."""
    title: str
    content: str       # Markdown-formatted article body


@dataclass
class BookIntro:
    """Book-level introduction prose from a source."""
    book: str
    source: str
    content: str  # Markdown-formatted


@dataclass
class ChapterIntro:
    """Optional prose preamble before verse 1 of a chapter."""
    book: str
    chapter: int
    source: str
    content: str  # Markdown-formatted


@dataclass
class PartIntro:
    """Introduction spanning a group of books (e.g. 'Torah', 'Historical Books').

    No adapter is required to produce these — most sources have no part structure.
    Covers multi-book editorial introductions (e.g. Robert Alter) and personal
    vault part-level notes.
    """
    part_name: str  # e.g. "Torah", "Historical Books", "Wisdom Literature"
    source: str     # e.g. "Robert Alter", "Personal"
    content: str    # Markdown-formatted


@dataclass
class ChapterNotes:
    """All study content for a single chapter from one source."""
    book: str
    chapter: int
    source: str                              # e.g. "OSB", "EOB"
    articles: list[StudyArticle] = field(default_factory=list)
    footnotes: list[StudyNote] = field(default_factory=list)
    variants: list[StudyNote] = field(default_factory=list)
    cross_references: list[StudyNote] = field(default_factory=list)
    liturgical: list[StudyNote] = field(default_factory=list)
    citations: list[StudyNote] = field(default_factory=list)
    translator_notes: list[StudyNote] = field(default_factory=list)
    alternatives: list[StudyNote] = field(default_factory=list)
    background_notes: list[StudyNote] = field(default_factory=list)
    parallel_passages: list[StudyNote] = field(default_factory=list)
    chapter_intro: ChapterIntro | None = None

    _NOTE_LISTS: ClassVar[dict[NoteType, str]] = {
        NoteType.FOOTNOTE:    "footnotes",
        NoteType.VARIANT:     "variants",
        NoteType.CROSS_REF:   "cross_references",
        NoteType.LITURGICAL:  "liturgical",
        NoteType.CITATION:    "citations",
        NoteType.TRANSLATOR:  "translator_notes",
        NoteType.ALTERNATIVE: "alternatives",
        NoteType.BACKGROUND:  "background_notes",
        NoteType.PARALLEL:    "parallel_passages",
    }

    def sorted_notes(self, note_type: NoteType) -> list[StudyNote]:
        """Return notes of the given type sorted by verse number."""
        return sorted(getattr(self, self._NOTE_LISTS[note_type]), key=lambda n: n.verse_number)
