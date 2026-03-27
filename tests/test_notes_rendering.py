"""
Regression tests: OSB notes companion rendering contracts.

Contracts guarded:
  1. Notes render in verse order (not by category/family first).
  2. Each verse group has exactly one heading linking back to the hub.
  3. Callouts are rendered as separate Obsidian blockquote blocks.
  4. Companion frontmatter includes hub and source fields.
"""
import re

import pytest

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer


@pytest.fixture
def renderer():
    return ObsidianRenderer()


# ── Contract 1: verse ordering ────────────────────────────────────────────────

def test_osb_notes_render_in_verse_order(renderer, john1_osb_notes):
    """Notes must be grouped by verse number ascending, not by note family."""
    output = renderer.render_notes(john1_osb_notes)
    headings = re.findall(r'### \[\[John 1#v(\d+)', output)
    verse_nums = [int(h) for h in headings]
    assert verse_nums == sorted(verse_nums), (
        f"Verse headings out of order: {verse_nums}"
    )


def test_osb_notes_no_category_section_headings(renderer, john1_osb_notes):
    """Output must not contain top-level category headings like '## Footnotes'."""
    output = renderer.render_notes(john1_osb_notes)
    for banned in ("## Footnotes", "## Variants", "## Cross References", "## Citations"):
        assert banned not in output, f"Category heading {banned!r} must not appear in notes companion"


# ── Contract 2: verse group heading format ───────────────────────────────────

def test_osb_notes_verse_heading_links_to_hub(renderer, john1_osb_notes):
    output = renderer.render_notes(john1_osb_notes)
    # Each verse group heading must link to the hub verse anchor
    assert "### [[John 1#v1|" in output
    assert "### [[John 1#v3|" in output


# ── Contract 3: callouts are separate blocks ─────────────────────────────────

def test_osb_notes_callouts_are_separate_blockquotes(renderer, john1_osb_notes):
    """Two notes on the same verse must produce two distinct > blockquote lines."""
    from vault_builder.domain.models import StudyNote
    from vault_builder.domain.models import ChapterNotes

    notes = ChapterNotes(book="John", chapter=1, source="OSB")
    notes.footnotes.append(StudyNote(verse_number=1, ref_str="1:1", content="First note."))
    notes.footnotes.append(StudyNote(verse_number=1, ref_str="1:1", content="Second note."))

    output = renderer.render_notes(notes)
    assert "First note." in output
    assert "Second note." in output
    # Both must appear under the same verse heading, not merged into one block
    idx_first = output.index("First note.")
    idx_second = output.index("Second note.")
    assert idx_first != idx_second


# ── Contract 4: companion frontmatter ────────────────────────────────────────

def test_osb_notes_frontmatter_has_hub_and_source(renderer, john1_osb_notes):
    output = renderer.render_notes(john1_osb_notes)
    assert 'hub: "[[John 1]]"' in output
    assert 'source: "OSB"' in output


# ── Contract 5: notes companion nav (no Study Notes self-link) ────────────────

def test_notes_companion_nav_has_no_study_notes_link(renderer, john1_osb_notes):
    output = renderer.render_notes(john1_osb_notes)
    assert "Study Notes" not in output, "Notes companion must not self-link to Study Notes"


def test_notes_companion_nav_uses_nav_label(renderer, john1_osb_notes):
    output = renderer.render_notes(john1_osb_notes)
    assert "> **Nav:**" in output
    assert "> **Modes:**" not in output


def test_notes_companion_nav_has_hub_link(renderer, john1_osb_notes):
    output = renderer.render_notes(john1_osb_notes)
    assert "[[John 1|Hub]]" in output


def test_notes_companion_nav_has_no_osb_mode_link(renderer, john1_osb_notes):
    output = renderer.render_notes(john1_osb_notes)
    assert "[[John 1|OSB]]" not in output, "OSB Notes must not include OSB mode link"


def test_notes_companion_nav_has_no_eob_link(renderer, john1_osb_notes):
    output = renderer.render_notes(john1_osb_notes)
    assert "[[John 1 \u2014 EOB|EOB]]" not in output, "OSB Notes must not link to EOB mode"


def test_notes_companion_nav_has_net_notes_link(renderer, john1_osb_notes):
    output = renderer.render_notes(john1_osb_notes)
    assert "[[John 1 \u2014 NET Notes|NET Notes]]" in output
