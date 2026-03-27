"""
Regression tests: Lexham English Septuagint notes companion rendering contracts.

Contracts guarded:
  1. Companion frontmatter includes hub and source: "Lexham" fields.
  2. Notes render interleaved in verse order.
  3. Each verse group has exactly one heading: ### [[Book Ch#vN|Abbr Ch:N]]
  4. Translation notes use [!tn] callout.
  5. No category section headings (e.g. "## Translation Notes").
  6. render_net_notes remains source-aware: Lexham notes get source: "Lexham",
     NET notes still get source: "NET".
"""
import re

import pytest

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.domain.models import ChapterNotes, StudyNote


@pytest.fixture
def renderer() -> ObsidianRenderer:
    return ObsidianRenderer()


# ── Contract 1: frontmatter ───────────────────────────────────────────────────


def test_lexham_notes_frontmatter_hub(renderer, genesis1_lexham_notes):
    output = renderer.render_net_notes(genesis1_lexham_notes)
    assert 'hub: "[[Genesis 1]]"' in output


def test_lexham_notes_frontmatter_source(renderer, genesis1_lexham_notes):
    output = renderer.render_net_notes(genesis1_lexham_notes)
    assert 'source: "Lexham"' in output


def test_lexham_notes_frontmatter_not_net(renderer, genesis1_lexham_notes):
    output = renderer.render_net_notes(genesis1_lexham_notes)
    assert 'source: "NET"' not in output


# ── Contract 6: source-awareness doesn't break existing NET output ─────────────


def test_net_notes_source_unaffected(renderer, john1_net_notes):
    """render_net_notes must still emit source: NET for NET notes after the fix."""
    output = renderer.render_net_notes(john1_net_notes)
    assert 'source: "NET"' in output
    assert 'source: "Lexham"' not in output


# ── Contract 2: verse order ───────────────────────────────────────────────────


def test_lexham_notes_render_in_verse_order(renderer, genesis1_lexham_notes):
    output = renderer.render_net_notes(genesis1_lexham_notes)
    verse_nums = [int(m) for m in re.findall(r'### \[\[Genesis 1#v(\d+)', output)]
    assert verse_nums == sorted(verse_nums), f"Verse headings out of order: {verse_nums}"


# ── Contract 3: heading format ────────────────────────────────────────────────


def test_lexham_notes_headings_link_to_hub_anchors(renderer, genesis1_lexham_notes):
    output = renderer.render_net_notes(genesis1_lexham_notes)
    assert "### [[Genesis 1#v1|" in output
    assert "### [[Genesis 1#v6|" in output
    assert "### [[Genesis 1#v20|" in output


def test_lexham_notes_each_verse_appears_once(renderer, genesis1_lexham_notes):
    output = renderer.render_net_notes(genesis1_lexham_notes)
    v6_headings = re.findall(r'### \[\[Genesis 1#v6\|', output)
    assert len(v6_headings) == 1


# ── Contract 4: callout type ──────────────────────────────────────────────────


def test_lexham_notes_uses_tn_callout(renderer, genesis1_lexham_notes):
    output = renderer.render_net_notes(genesis1_lexham_notes)
    assert "[!tn]" in output


def test_lexham_notes_content_present(renderer, genesis1_lexham_notes):
    output = renderer.render_net_notes(genesis1_lexham_notes)
    assert 'Lit. "of the water and of the water"' in output
    assert 'Or "sky"' in output


# ── Contract 5: no category headings ─────────────────────────────────────────


def test_lexham_notes_no_category_section_headings(renderer, genesis1_lexham_notes):
    output = renderer.render_net_notes(genesis1_lexham_notes)
    for banned in ("## Translation", "## Footnotes", "## Notes"):
        assert banned not in output, f"Category heading {banned!r} must not appear"
