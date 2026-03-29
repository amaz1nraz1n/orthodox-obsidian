"""
Core domain models for Orthodox Scripture vault building.

These are plain data objects with no dependencies on any specific source format
or output format. All extractors produce these; all renderers consume them.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Canonical note type names — used as keys in ChapterNotes, renderer _CALLOUT
# dicts, and source adapter _NOTE_TYPE_TO_MARKER dicts.
NOTE_TYPES = (
    "footnote",        # Study/commentary note (OSB main notes)
    "background_note", # Historical/geographical context
    "variant",         # Textual variant / manuscript difference
    "translator_note", # Linguistic or translation note
    "alternative",     # Alternative reading
    "cross_reference", # Cross-reference to another passage
    "parallel_passage",# Synoptic/parallel passage link
    "liturgical",      # Liturgical usage note
    "citation",        # Patristic citation
)


@dataclass
class Verse:
    number: int
    text: str


@dataclass
class Chapter:
    book: str
    number: int
    verses: Dict[int, Verse] = field(default_factory=dict)
    pericopes: Dict[int, str] = field(default_factory=dict)  # first_verse → title
    after_markers: Dict[int, List[str]] = field(default_factory=dict)  # verse_num → markers after that verse (e.g. Diapsalma/Selah)

    def sorted_verses(self) -> List[Verse]:
        return [self.verses[n] for n in sorted(self.verses)]


@dataclass
class Book:
    name: str
    chapters: Dict[int, Chapter] = field(default_factory=dict)

    def max_chapter(self) -> int:
        return max(self.chapters.keys()) if self.chapters else 0


@dataclass
class StudyNote:
    """A single per-verse footnote from a study source."""
    verse_number: int
    ref_str: str              # e.g. "1:14" or "1:14-16"
    content: str              # Markdown-formatted note body
    verse_end: Optional[int] = None  # Future-proofing: Not currently utilized by Obsidian,
                                     # but exists to support potential future range-linking.
    note_id: Optional[str] = None  # EPUB element ID for per-callout deep-linking (e.g. "fn4706")


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
    articles: List[StudyArticle] = field(default_factory=list)
    footnotes: List[StudyNote] = field(default_factory=list)
    variants: List[StudyNote] = field(default_factory=list)
    cross_references: List[StudyNote] = field(default_factory=list)
    liturgical: List[StudyNote] = field(default_factory=list)
    citations: List[StudyNote] = field(default_factory=list)
    translator_notes: List[StudyNote] = field(default_factory=list)
    alternatives: List[StudyNote] = field(default_factory=list)
    background_notes: List[StudyNote] = field(default_factory=list)
    parallel_passages: List[StudyNote] = field(default_factory=list)
    chapter_intro: Optional[ChapterIntro] = None

    def sorted_footnotes(self) -> List[StudyNote]:
        return sorted(self.footnotes, key=lambda n: n.verse_number)

    def sorted_variants(self) -> List[StudyNote]:
        return sorted(self.variants, key=lambda n: n.verse_number)

    def sorted_cross_references(self) -> List[StudyNote]:
        return sorted(self.cross_references, key=lambda n: n.verse_number)

    def sorted_liturgical(self) -> List[StudyNote]:
        return sorted(self.liturgical, key=lambda n: n.verse_number)

    def sorted_citations(self) -> List[StudyNote]:
        return sorted(self.citations, key=lambda n: n.verse_number)

    def sorted_translator_notes(self) -> List[StudyNote]:
        return sorted(self.translator_notes, key=lambda n: n.verse_number)

    def sorted_alternatives(self) -> List[StudyNote]:
        return sorted(self.alternatives, key=lambda n: n.verse_number)

    def sorted_background_notes(self) -> List[StudyNote]:
        return sorted(self.background_notes, key=lambda n: n.verse_number)

    def sorted_parallel_passages(self) -> List[StudyNote]:
        return sorted(self.parallel_passages, key=lambda n: n.verse_number)
