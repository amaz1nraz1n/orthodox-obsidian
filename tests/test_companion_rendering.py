"""
Regression tests: text companion (Lexham, EOB) rendering contracts.

Contracts guarded:
  1. Companion frontmatter includes hub and source fields.
  2. Hub link format is [[Book Chapter]] (not a bare string).
  3. Verses render in ascending order.
  4. Each verse has an inline <span class="vn"> number.
  5. Each verse has a hidden ^vN block ID.
  6. Nav callout has correct source links and Study Notes target.
"""
import re

import pytest

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer


@pytest.fixture
def renderer():
    return ObsidianRenderer()


# ── Contract 1 & 2: frontmatter ───────────────────────────────────────────────

def test_lexham_companion_frontmatter(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert 'hub: "[[Genesis 1]]"' in output
    assert 'source: "Lexham"' in output
    assert "cssclasses: [scripture-hub]" in output


def test_eob_companion_frontmatter(renderer, john1_chapter):
    output = renderer.render_text_companion(john1_chapter, source="EOB")
    assert 'hub: "[[John 1]]"' in output
    assert 'source: "EOB"' in output
    assert "cssclasses: [scripture-hub]" in output


def test_companion_hub_link_is_wikilink(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert "[[Genesis 1]]" in output, "Hub reference must be a wikilink, not a bare string"


# ── Contract 3: verse order ───────────────────────────────────────────────────

def test_companion_verses_in_order(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    headings = [int(m) for m in re.findall(r'###### v(\d+)', output)]
    assert headings == sorted(headings), f"Verse headings out of order: {headings}"


# ── Contract 4: inline verse number styling ───────────────────────────────────

def test_companion_verse_has_inline_vn_span(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert '<span class="vn">1</span>' in output
    assert '<span class="vn">2</span>' in output


# ── Contract 5: hidden block IDs ──────────────────────────────────────────────

def test_companion_verse_has_block_id(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert "^v1" in output
    assert "^v2" in output


# ── Contract 6: nav callout ───────────────────────────────────────────────────

def test_ot_companion_nav_has_osb_link(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert "[[Genesis 1|OSB]]" in output


def test_ot_companion_nav_has_lexham_link(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert "[[Genesis 1 \u2014 Lexham|Lexham]]" in output


def test_ot_companion_nav_has_net_notes_link(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert "[[Genesis 1 \u2014 NET Notes|NET Notes]]" in output


def test_ot_companion_nav_has_lexham_notes_study_link(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert "[[Genesis 1 \u2014 Lexham Notes|Study Notes]]" in output


def test_ot_companion_nav_has_no_eob_link(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert "EOB" not in output, "OT companion must not link to EOB"


def test_nt_companion_nav_has_eob_link(renderer, john1_chapter):
    output = renderer.render_text_companion(john1_chapter, source="EOB")
    assert "[[John 1 \u2014 EOB|EOB]]" in output


def test_nt_companion_nav_has_eob_notes_study_link(renderer, john1_chapter):
    output = renderer.render_text_companion(john1_chapter, source="EOB")
    assert "[[John 1 \u2014 EOB Notes|Study Notes]]" in output


def test_nt_companion_nav_has_no_lexham_link(renderer, john1_chapter):
    output = renderer.render_text_companion(john1_chapter, source="EOB")
    assert "Lexham" not in output, "NT companion must not link to Lexham"


def test_nt_eob_companion_nav_has_greek_nt_link(renderer, john1_chapter):
    output = renderer.render_text_companion(john1_chapter, source="EOB")
    assert "[[John 1 \u2014 Greek NT|Greek NT]]" in output


def test_nt_greek_companion_nav_has_no_greek_self_link(renderer, john1_chapter):
    output = renderer.render_text_companion(john1_chapter, source="Greek NT", notes_suffix=None)
    assert "[[John 1 \u2014 Greek NT|Greek NT]]" not in output, "Greek NT companion must not self-link"


def test_ot_lexham_companion_nav_has_no_greek_nt_link(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert "Greek NT" not in output, "OT companion must not link to Greek NT"


def test_ot_lexham_companion_nav_has_lxx_link(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="Lexham")
    assert "[[Genesis 1 \u2014 LXX|LXX]]" in output


def test_ot_lxx_companion_nav_has_no_lxx_self_link(renderer, genesis1_lexham_chapter):
    output = renderer.render_text_companion(genesis1_lexham_chapter, source="LXX", notes_suffix=None)
    assert "[[Genesis 1 \u2014 LXX|LXX]]" not in output, "LXX companion must not self-link"
