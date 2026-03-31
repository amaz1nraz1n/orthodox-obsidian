"""Tests for new taxonomy callout types in ObsidianRenderer — Phase 3."""

import re

import pytest

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.domain.models import ChapterNotes, NoteType, StudyNote


@pytest.fixture
def renderer():
    return ObsidianRenderer()


def _notes(**kwargs) -> ChapterNotes:
    """Build a ChapterNotes with one StudyNote per requested slot."""
    n = ChapterNotes(book="John", chapter=1, source="OSB")
    note = StudyNote(verse_number=1, ref_str="1:1", content="Test content.")
    for slot in kwargs:
        getattr(n, slot).append(note)
    return n


# ── One test per new callout type ─────────────────────────────────────────────

def test_translator_note_renders_tn_callout(renderer):
    output = renderer.render_notes(_notes(translator_notes=True))
    assert "[!tn]" in output


def test_alternative_renders_alt_callout(renderer):
    output = renderer.render_notes(_notes(alternatives=True))
    assert "[!alt]" in output


def test_background_note_renders_bg_callout(renderer):
    output = renderer.render_notes(_notes(background_notes=True))
    assert "[!bg]" in output


def test_parallel_passage_renders_parallel_callout(renderer):
    output = renderer.render_notes(_notes(parallel_passages=True))
    assert "[!parallel]" in output


# ── Existing callout types unaffected ─────────────────────────────────────────

def test_footnote_still_renders_plain(renderer):
    output = renderer.render_notes(_notes(footnotes=True))
    # footnotes have no callout label — content appears directly
    assert "Test content." in output
    assert "[!tn]" not in output


def test_variant_still_renders_info_callout(renderer):
    output = renderer.render_notes(_notes(variants=True))
    assert "[!info]" in output


def test_citation_still_renders_cite_callout(renderer):
    output = renderer.render_notes(_notes(citations=True))
    assert "[!cite]" in output


def test_cross_reference_still_renders_quote_callout(renderer):
    output = renderer.render_notes(_notes(cross_references=True))
    assert "[!quote]" in output


def test_liturgical_still_renders_liturgy_callout(renderer):
    output = renderer.render_notes(_notes(liturgical=True))
    assert "[!liturgy]" in output


# ── Sort order across all families ───────────────────────────────────────────

def test_all_note_families_sort_by_verse_order(renderer):
    """Notes from all 9 families must appear in verse order, not family order."""
    n = ChapterNotes(book="John", chapter=1, source="OSB")
    # Assign different verse numbers across families so sort order is detectable
    families = [
        ("footnotes",        5),
        ("variants",         2),
        ("cross_references", 8),
        ("liturgical",       1),
        ("citations",        6),
        ("translator_notes", 3),
        ("alternatives",     9),
        ("background_notes", 4),
        ("parallel_passages", 7),
    ]
    for slot, verse in families:
        getattr(n, slot).append(
            StudyNote(verse_number=verse, ref_str=f"1:{verse}", content=f"v{verse} note.")
        )
    output = renderer.render_notes(n)
    headings = re.findall(r"### \[\[John 1#v(\d+)", output)
    verse_nums = [int(h) for h in headings]
    assert verse_nums == sorted(verse_nums), f"Out of order: {verse_nums}"


# ── NET render_net_notes picks up translator_notes ────────────────────────────

def test_net_render_includes_translator_notes(renderer):
    n = ChapterNotes(book="John", chapter=1, source="NET")
    n.add_note(NoteType.TRANSLATOR, StudyNote(verse_number=1, ref_str="1:1", content="Greek nuance note."))
    output = renderer.render_net_notes(n)
    assert "[!tn]" in output
    assert "Greek nuance note." in output


def test_net_translator_notes_sort_with_other_note_types(renderer):
    n = ChapterNotes(book="John", chapter=1, source="NET")
    n.add_note(NoteType.FOOTNOTE, StudyNote(verse_number=3, ref_str="1:3", content="Footnote v3."))
    n.add_note(NoteType.TRANSLATOR, StudyNote(verse_number=1, ref_str="1:1", content="TN v1."))
    output = renderer.render_net_notes(n)
    headings = re.findall(r"### \[\[John 1#v(\d+)", output)
    verse_nums = [int(h) for h in headings]
    assert verse_nums == sorted(verse_nums)
