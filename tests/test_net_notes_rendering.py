"""
Regression tests: NET Bible notes companion rendering contracts.

Contracts guarded:
  1. Companion frontmatter includes hub and source: "NET" fields.
  2. Notes from all families render interleaved in verse order.
  3. Each verse group has exactly one heading: ### [[Book Ch#vN|Abbr Ch:N]]
  4. Callouts use NET-specific labels ([!tn], [!tc], [!sn], [!map]).
  5. Multiple note families on the same verse appear under one heading.
  6. No category section headings (e.g. "## Translator's Notes").
"""
import re

import pytest

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer


@pytest.fixture
def renderer() -> ObsidianRenderer:
    return ObsidianRenderer()


# ── Contract 1: frontmatter ───────────────────────────────────────────────────


def test_net_notes_frontmatter_hub(renderer, john1_net_notes):
    output = renderer.render_net_notes(john1_net_notes)
    assert 'hub: "[[John 1]]"' in output


def test_net_notes_frontmatter_source(renderer, john1_net_notes):
    output = renderer.render_net_notes(john1_net_notes)
    assert 'source: "NET"' in output


# ── Contract 2: verse order ───────────────────────────────────────────────────


def test_net_notes_render_in_verse_order(renderer, john1_net_notes):
    output = renderer.render_net_notes(john1_net_notes)
    verse_nums = [int(m) for m in re.findall(r'### \[\[John 1#v(\d+)', output)]
    assert verse_nums == sorted(verse_nums), f"Verse headings out of order: {verse_nums}"


def test_net_notes_each_verse_appears_once(renderer, john1_net_notes):
    output = renderer.render_net_notes(john1_net_notes)
    # v1 has both a tn and a tc — must produce exactly one ### heading for v1
    v1_headings = re.findall(r'### \[\[John 1#v1\|', output)
    assert len(v1_headings) == 1, f"Expected exactly 1 heading for v1, got {len(v1_headings)}"


# ── Contract 3: heading format ────────────────────────────────────────────────


def test_net_notes_heading_links_to_hub_anchor(renderer, john1_net_notes):
    output = renderer.render_net_notes(john1_net_notes)
    assert "### [[John 1#v1|" in output
    assert "### [[John 1#v3|" in output
    assert "### [[John 1#v5|" in output


# ── Contract 4: NET callout labels ───────────────────────────────────────────


def test_net_notes_tn_callout(renderer, john1_net_notes):
    output = renderer.render_net_notes(john1_net_notes)
    assert "[!tn]" in output


def test_net_notes_tc_callout(renderer, john1_net_notes):
    output = renderer.render_net_notes(john1_net_notes)
    assert "[!tc]" in output


def test_net_notes_sn_callout(renderer, john1_net_notes):
    output = renderer.render_net_notes(john1_net_notes)
    assert "[!sn]" in output


# ── Contract 5: multi-family grouping ────────────────────────────────────────


def test_net_notes_tn_and_tc_under_same_verse_heading(renderer, john1_net_notes):
    """v1 has both a tn and tc note — both must appear after the single v1 heading."""
    output = renderer.render_net_notes(john1_net_notes)
    v1_idx = output.index("### [[John 1#v1|")
    # Find the next verse heading after v1 (v3)
    v3_idx = output.index("### [[John 1#v3|")
    v1_block = output[v1_idx:v3_idx]
    assert "[!tn]" in v1_block, "tn callout missing from v1 block"
    assert "[!tc]" in v1_block, "tc callout missing from v1 block"


# ── Contract 6: no category headings ─────────────────────────────────────────


def test_net_notes_no_category_section_headings(renderer, john1_net_notes):
    output = renderer.render_net_notes(john1_net_notes)
    for banned in ("## Translator", "## Text-critical", "## Study", "## Map"):
        assert banned not in output, f"Category heading {banned!r} must not appear"
