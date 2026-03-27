"""
Contract tests for EOB Notes companion rendering.

Covers render_notes() when source="EOB": frontmatter, nav callout,
verse ordering, heading wikilink format, and note content presence.
"""
import re
import pytest

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer


@pytest.fixture
def renderer() -> ObsidianRenderer:
    return ObsidianRenderer()


# ── Frontmatter ───────────────────────────────────────────────────────────────

def test_eob_notes_frontmatter_hub(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert 'hub: "[[John 1]]"' in out


def test_eob_notes_frontmatter_source(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert 'source: "EOB"' in out


# ── Nav callout ───────────────────────────────────────────────────────────────

def test_eob_notes_nav_has_osb_link(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert "[[John 1|OSB]]" in out


def test_eob_notes_nav_has_eob_link(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert "[[John 1 \u2014 EOB|EOB]]" in out


def test_eob_notes_nav_has_net_notes_link(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert "[[John 1 \u2014 NET Notes|NET Notes]]" in out


def test_eob_notes_nav_has_no_study_notes_link(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert "Study Notes" not in out, "Notes companion must not self-link to Study Notes"


def test_eob_notes_nav_has_no_eob_notes_self_link(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert "EOB Notes" not in out, "EOB Notes companion must not self-link to EOB Notes"


def test_eob_notes_nav_has_no_lexham_link(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert "Lexham" not in out, "NT notes companion must not link to Lexham"


# ── Verse ordering ────────────────────────────────────────────────────────────

def test_eob_notes_render_in_verse_order(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    positions = [out.index(f"1:{v}") for v in (1, 3, 14)]
    assert positions == sorted(positions), "Notes must appear in ascending verse order"


def test_eob_notes_each_verse_appears_once(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    for v in (1, 3, 14):
        assert out.count(f"|1:{v}]]") == 1, f"Verse 1:{v} heading should appear exactly once"


# ── Heading wikilink format ───────────────────────────────────────────────────

def test_eob_notes_headings_link_to_hub_anchors(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert "[[John 1#v1|1:1]]" in out
    assert "[[John 1#v3|1:3]]" in out
    assert "[[John 1#v14|1:14]]" in out


# ── Content ───────────────────────────────────────────────────────────────────

def test_eob_notes_content_present(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    assert "Logos commentary" in out
    assert "Word became flesh" in out


def test_eob_notes_no_category_section_headings(renderer, john1_eob_notes):
    out = renderer.render_notes(john1_eob_notes)
    for bad in ("## Footnotes", "## Variants", "## Citations"):
        assert bad not in out, f"Notes must not have category section heading: {bad!r}"
