"""
Regression tests: hub file rendering contracts.

Contracts guarded:
  1. OT hub modes bar includes Lexham; NT hub does not.
  2. Each verse has an inline <span class="vn"> number.
  3. Each verse has a hidden ^vN block ID on the same line.
  4. Verse heading is ###### vN.
"""
import re

import pytest

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer


@pytest.fixture
def renderer():
    return ObsidianRenderer()


# ── Contract 1: modes bar Lexham presence ─────────────────────────────────────

def test_ot_hub_modes_bar_includes_lexham(renderer, genesis1_chapter):
    output = renderer.render_hub(genesis1_chapter, max_chapter=50)
    assert "Lexham" in output, "OT hub must link to Lexham companion in modes bar"


def test_nt_hub_modes_bar_excludes_lexham(renderer, john1_chapter):
    output = renderer.render_hub(john1_chapter, max_chapter=21)
    assert "Lexham" not in output, "NT hub must NOT include Lexham in modes bar"


def test_ot_hub_modes_bar_has_all_standard_modes(renderer, genesis1_chapter):
    output = renderer.render_hub(genesis1_chapter, max_chapter=50)
    for mode in ("Lexham", "LXX", "NET", "Study Notes"):
        assert mode in output, f"OT hub modes bar must include {mode!r}"
    assert "Alter" not in output, "OT hub must not link Alter directly (use +)"
    assert "NET Notes" not in output, "OT hub must not link NET Notes directly (use +)"
    assert "Lexham Notes" not in output, "OT hub must not link Lexham Notes directly"
    assert "EOB" not in output, "OT hub must not link to EOB"
    assert "Greek NT" not in output, "OT hub must not link to Greek NT"


def test_nt_hub_modes_bar_has_all_standard_modes(renderer, john1_chapter):
    output = renderer.render_hub(john1_chapter, max_chapter=21)
    for mode in ("EOB", "Greek NT", "NET", "Study Notes"):
        assert mode in output, f"NT hub modes bar must include {mode!r}"
    assert "EOB Notes" not in output, "NT hub must not link EOB Notes directly"
    assert "NET Notes" not in output, "NT hub must not link NET Notes directly (use +)"
    assert "Lexham" not in output, "NT hub must not link to Lexham"


# ── Contract 2: inline verse number styling ───────────────────────────────────

def test_hub_verse_has_inline_vn_span(renderer, genesis1_chapter):
    output = renderer.render_hub(genesis1_chapter, max_chapter=50)
    assert '<span class="vn">1</span>' in output
    assert '<span class="vn">2</span>' in output
    assert '<span class="vn">3</span>' in output


# ── Contract 3: hidden block IDs ──────────────────────────────────────────────

def test_hub_verse_has_block_id(renderer, genesis1_chapter):
    output = renderer.render_hub(genesis1_chapter, max_chapter=50)
    for vnum in (1, 2, 3):
        assert f"^v{vnum}" in output, f"Hub must include hidden block ID ^v{vnum}"


# ── Contract 4: verse heading format ─────────────────────────────────────────

def test_hub_verse_heading_format(renderer, genesis1_chapter):
    output = renderer.render_hub(genesis1_chapter, max_chapter=50)
    for vnum in (1, 2, 3):
        assert f"###### v{vnum}" in output, f"Verse heading must be '###### v{vnum}'"


# ── Contract 5: verse number does not bleed into verse text ──────────────────

def test_hub_verse_text_does_not_start_with_digit(renderer, genesis1_chapter):
    output = renderer.render_hub(genesis1_chapter, max_chapter=50)
    # Each verse line: <span class="vn">N</span> TEXT ^vN
    # TEXT must not start with a digit (regression: "1In the beginning...")
    verse_line_re = re.compile(r'<span class="vn">\d+</span> (\S)')
    for m in verse_line_re.finditer(output):
        first_char = m.group(1)
        assert not first_char.isdigit(), (
            f"Verse text starts with digit — verse number leaked into body: {m.group(0)!r}"
        )
