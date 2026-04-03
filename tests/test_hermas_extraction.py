"""
PER-61: Shepherd of Hermas extraction tests.

Covers:
  1. _hermas_book() — boundary mapping and within-book numbering
  2. _collect_hermas_all_notes() — displaced footnote pre-pass
  3. Integration: read_documents() yields correct books, chapters, verses, notes
     (skipped when EPUB is absent)
"""

from __future__ import annotations

import os
import zipfile
from unittest.mock import MagicMock

import pytest
import yaml

from vault_builder.adapters.sources.apostolic_fathers_epub import (
    ApostolicFathersEpubSource,
    _HERMAS_BOOK_BOUNDARIES,
    _HERMAS_HTML,
    _collect_hermas_all_notes,
    _hermas_book,
)

_SOURCES_YAML = os.path.join(os.path.dirname(__file__), "..", "sources.yaml")


def _af_epub_path() -> str:
    with open(_SOURCES_YAML) as f:
        return yaml.safe_load(f)["sources"]["apostolic-fathers"]["path"]


_epub_present = pytest.mark.skipif(
    not os.path.exists(_af_epub_path()),
    reason="Apostolic Fathers EPUB not present on disk",
)


# ── 1. _hermas_book() ─────────────────────────────────────────────────────────

def test_hermas_book_visions_first():
    assert _hermas_book(1) == ("Shepherd of Hermas — Visions", 1)


def test_hermas_book_visions_last():
    assert _hermas_book(25) == ("Shepherd of Hermas — Visions", 25)


def test_hermas_book_commandments_first():
    assert _hermas_book(26) == ("Shepherd of Hermas — Commandments", 1)


def test_hermas_book_commandments_last():
    assert _hermas_book(49) == ("Shepherd of Hermas — Commandments", 24)


def test_hermas_book_parables_first():
    assert _hermas_book(50) == ("Shepherd of Hermas — Parables", 1)


def test_hermas_book_parables_last():
    assert _hermas_book(114) == ("Shepherd of Hermas — Parables", 65)


def test_hermas_book_out_of_range_raises():
    with pytest.raises(ValueError, match="115"):
        _hermas_book(115)


def test_hermas_book_boundaries_are_contiguous():
    """No gaps or overlaps in the boundary table."""
    for i in range(len(_HERMAS_BOOK_BOUNDARIES) - 1):
        _, last, _ = _HERMAS_BOOK_BOUNDARIES[i]
        next_first, _, _ = _HERMAS_BOOK_BOUNDARIES[i + 1]
        assert last + 1 == next_first, f"Gap between boundary {i} and {i+1}"


# ── 2. _collect_hermas_all_notes() ────────────────────────────────────────────

@_epub_present
def test_hermas_notes_prepass_captures_displaced_footnote():
    """Footnote for seq ch 1 v 7 appears physically after seq ch 2 paragraph."""
    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
    import warnings
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    with zipfile.ZipFile(_af_epub_path()) as zf:
        html = zf.read(_HERMAS_HTML).decode("utf-8")
    soup = BeautifulSoup(html, "lxml")
    notes = _collect_hermas_all_notes(soup)

    assert 1 in notes
    assert 7 in notes[1]
    assert any("what way" in frag.lower() for frag in notes[1][7])


@_epub_present
def test_hermas_notes_prepass_multi_chapter_paragraph():
    """A single noindenta can reference multiple seq chapters (e.g. 8.1 and 9.1)."""
    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
    import warnings
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    with zipfile.ZipFile(_af_epub_path()) as zf:
        html = zf.read(_HERMAS_HTML).decode("utf-8")
    soup = BeautifulSoup(html, "lxml")
    notes = _collect_hermas_all_notes(soup)

    # p[32]: "8.1 brothers and sisters Gk adelphoi.  9.1 brothers..."
    assert 8 in notes and 1 in notes[8]
    assert 9 in notes and 1 in notes[9]


# ── 3. Integration: read_documents() ─────────────────────────────────────────

@_epub_present
def test_hermas_visions_chapter_1_yields_verse_text():
    src = ApostolicFathersEpubSource(
        _af_epub_path(),
        sample_only=True,
        sample_chapters={("Shepherd of Hermas — Visions", 1)},
    )
    docs = {(ch.book, ch.number): ch for ch, _ in src.read_documents()}
    assert ("Shepherd of Hermas — Visions", 1) in docs
    ch = docs[("Shepherd of Hermas — Visions", 1)]
    assert ch.sorted_verses()[0].number == 1
    assert "Rhoda" in ch.sorted_verses()[0].text


@_epub_present
def test_hermas_visions_chapter_1_has_displaced_footnote():
    """Footnote for Vision 1.7 must appear despite being placed after ch 2 para."""
    src = ApostolicFathersEpubSource(
        _af_epub_path(),
        sample_only=True,
        sample_chapters={("Shepherd of Hermas — Visions", 1)},
    )
    notes_map = {(n.book, n.chapter): n for _, n in src.read_documents()}
    notes = notes_map[("Shepherd of Hermas — Visions", 1)]
    footnotes = notes.footnotes
    assert any(f.verse_number == 7 for f in footnotes)
    assert any("what way" in f.content.lower() for f in footnotes if f.verse_number == 7)


@_epub_present
def test_hermas_commandments_chapter_1_within_book_numbering():
    """Sequential chapter 26 must appear as Commandments chapter 1."""
    src = ApostolicFathersEpubSource(
        _af_epub_path(),
        sample_only=True,
        sample_chapters={("Shepherd of Hermas — Commandments", 1)},
    )
    docs = {(ch.book, ch.number): ch for ch, _ in src.read_documents()}
    assert ("Shepherd of Hermas — Commandments", 1) in docs
    ch = docs[("Shepherd of Hermas — Commandments", 1)]
    assert ch.sorted_verses()[0].number == 1
    assert "believe" in ch.sorted_verses()[0].text.lower()


@_epub_present
def test_hermas_parables_chapter_1_within_book_numbering():
    """Sequential chapter 50 must appear as Parables chapter 1."""
    src = ApostolicFathersEpubSource(
        _af_epub_path(),
        sample_only=True,
        sample_chapters={("Shepherd of Hermas — Parables", 1)},
    )
    docs = {(ch.book, ch.number): ch for ch, _ in src.read_documents()}
    assert ("Shepherd of Hermas — Parables", 1) in docs


@_epub_present
def test_hermas_full_run_chapter_count():
    """Full extraction must yield exactly 114 Hermas chapters across 3 books."""
    src = ApostolicFathersEpubSource(_af_epub_path(), sample_only=False)
    hermas_chapters = [
        (ch.book, ch.number)
        for ch, _ in src.read_documents()
        if "Hermas" in ch.book
    ]
    assert len(hermas_chapters) == 114
    visions      = [c for c in hermas_chapters if "Visions"      in c[0]]
    commandments = [c for c in hermas_chapters if "Commandments" in c[0]]
    parables     = [c for c in hermas_chapters if "Parables"     in c[0]]
    assert len(visions)      == 25
    assert len(commandments) == 24
    assert len(parables)     == 65
