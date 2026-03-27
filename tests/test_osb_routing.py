"""Tests for OSB adapter slot routing — Phase 4.

Verifies that alternative.html, background.html, and translation.html
content lands in the correct ChapterNotes slots after re-routing.

Integration tests (marked with @pytest.mark.integration) read the real OSB
EPUB and are skipped automatically if the file is not present on disk.
"""

import os

import pytest
import yaml

from vault_builder.domain.models import ChapterNotes, StudyNote

_SOURCES_YAML = os.path.join(os.path.dirname(__file__), "..", "sources.yaml")


def _osb_epub_path() -> str:
    with open(_SOURCES_YAML) as f:
        return yaml.safe_load(f)["sources"]["osb"]["path"]


_osb_present = pytest.mark.skipif(
    not os.path.exists(_osb_epub_path()),
    reason="OSB EPUB not present on disk",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_notes(**slot_counts) -> ChapterNotes:
    """Build a ChapterNotes with the specified number of notes per slot."""
    n = ChapterNotes(book="John", chapter=1, source="OSB")
    for slot, count in slot_counts.items():
        for i in range(count):
            getattr(n, slot).append(
                StudyNote(verse_number=i + 1, ref_str=f"1:{i+1}", content=f"{slot} note {i+1}.")
            )
    return n


# ── Slot isolation: each new type stays in its own slot ───────────────────────

def test_alternatives_not_in_variants():
    notes = _make_notes(alternatives=2)
    assert len(notes.alternatives) == 2
    assert len(notes.variants) == 0


def test_alternatives_not_in_footnotes():
    notes = _make_notes(alternatives=1)
    assert len(notes.footnotes) == 0


def test_background_notes_not_in_footnotes():
    notes = _make_notes(background_notes=2)
    assert len(notes.background_notes) == 2
    assert len(notes.footnotes) == 0


def test_background_notes_not_in_variants():
    notes = _make_notes(background_notes=1)
    assert len(notes.variants) == 0


def test_translator_notes_not_in_variants():
    notes = _make_notes(translator_notes=2)
    assert len(notes.translator_notes) == 2
    assert len(notes.variants) == 0


def test_translator_notes_not_in_footnotes():
    notes = _make_notes(translator_notes=1)
    assert len(notes.footnotes) == 0


# ── Existing slots unaffected by re-routing ───────────────────────────────────

def test_footnotes_slot_unaffected():
    notes = _make_notes(footnotes=3, alternatives=1, background_notes=1, translator_notes=1)
    assert len(notes.footnotes) == 3


def test_variants_slot_unaffected():
    notes = _make_notes(variants=2, alternatives=1, translator_notes=1)
    assert len(notes.variants) == 2


def test_all_six_slots_independent():
    notes = _make_notes(
        footnotes=1, variants=1, alternatives=1,
        background_notes=1, translator_notes=1, citations=1,
    )
    assert len(notes.footnotes) == 1
    assert len(notes.variants) == 1
    assert len(notes.alternatives) == 1
    assert len(notes.background_notes) == 1
    assert len(notes.translator_notes) == 1
    assert len(notes.citations) == 1


# ── Renderer callout verification ─────────────────────────────────────────────

def test_alternatives_render_alt_callout():
    from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
    renderer = ObsidianRenderer()
    notes = _make_notes(alternatives=1)
    output = renderer.render_notes(notes)
    assert "[!alt]" in output
    assert "[!info]" not in output  # must NOT appear as a variant


def test_background_notes_render_bg_callout():
    from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
    renderer = ObsidianRenderer()
    notes = _make_notes(background_notes=1)
    output = renderer.render_notes(notes)
    assert "[!bg]" in output
    assert "background_notes note 1." in output


def test_translator_notes_render_tn_callout():
    from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
    renderer = ObsidianRenderer()
    notes = _make_notes(translator_notes=1)
    output = renderer.render_notes(notes)
    assert "[!tn]" in output
    assert "[!info]" not in output  # must NOT appear as a variant


# ── Integration: real OSB EPUB ────────────────────────────────────────────────

@_osb_present
def test_real_epub_galatians4_alternative_slot():
    """Galatians 4:4 has 'Or *made*' in alternative.html — must land in alternatives."""
    from vault_builder.adapters.sources.osb_epub import OsbEpubSource
    src = OsbEpubSource(_osb_epub_path(), sample_only=False)
    gal4 = next((n for n in src.read_notes() if n.book == "Galatians" and n.chapter == 4), None)
    assert gal4 is not None, "No notes found for Galatians 4"
    assert any("made" in n.content.lower() for n in gal4.alternatives), \
        "expected 'Or *made*' in alternatives slot"
    assert not any("made" in n.content.lower() for n in gal4.variants), \
        "alternative must NOT be in variants slot"


@_osb_present
def test_real_epub_revelation1_background_slot():
    """Revelation 1:9 has Patmos geography in background.html — must land in background_notes."""
    from vault_builder.adapters.sources.osb_epub import OsbEpubSource
    src = OsbEpubSource(_osb_epub_path(), sample_only=False)
    rev1 = next((n for n in src.read_notes() if n.book == "Revelation" and n.chapter == 1), None)
    assert rev1 is not None, "No notes found for Revelation 1"
    assert any("Patmos" in n.content for n in rev1.background_notes), \
        "expected Patmos note in background_notes slot"
    assert not any("Patmos" in n.content for n in rev1.footnotes), \
        "background note must NOT be in footnotes slot"
