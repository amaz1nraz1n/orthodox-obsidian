"""
Regression tests: Psalm singular naming convention.

Contracts:
  1. Hub prev/next links use [[Psalm N]] (singular), not [[Psalms N]].
  2. Hub up: frontmatter still points to [[Psalms]] (book index keeps plural).
  3. Modes bar links use [[Psalm N — Source|...]] (singular).
  4. render_text_companion hub: frontmatter uses [[Psalm N]] (singular).
  5. ObsidianWriter paths end in 'Psalm N.md', 'Psalm N — Source.md', etc.
  6. Non-Psalm books are unaffected.
"""

import pytest

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.domain.canon import book_file_prefix
from vault_builder.domain.models import Chapter, ChapterNotes, Verse


@pytest.fixture
def renderer():
    return ObsidianRenderer()


@pytest.fixture
def writer(tmp_path):
    return ObsidianWriter(output_root=str(tmp_path))


# ── Contract 0: book_file_prefix() helper ─────────────────────────────────────

def test_book_file_prefix_psalms():
    assert book_file_prefix("Psalms") == "Psalm"


def test_book_file_prefix_other_books_unchanged():
    for book in ("Genesis", "John", "Isaiah", "Revelation", "Proverbs"):
        assert book_file_prefix(book) == book


# ── Contract 1: Hub prev/next links ───────────────────────────────────────────

def test_psalm_hub_prev_link_singular(renderer, psalms50_chapter):
    output = renderer.render_hub(psalms50_chapter, max_chapter=151)
    assert 'prev: "[[Psalm 49]]"' in output, "prev link must use singular 'Psalm'"
    assert "Psalms 49" not in output


def test_psalm_hub_next_link_singular(renderer, psalms50_chapter):
    output = renderer.render_hub(psalms50_chapter, max_chapter=151)
    assert 'next: "[[Psalm 51]]"' in output, "next link must use singular 'Psalm'"
    assert 'next: "[[Psalms 51]]"' not in output


def test_psalm_hub_first_chapter_no_prev(renderer):
    ch = Chapter(book="Psalms", number=1)
    ch.verses[1] = Verse(number=1, text="Blessed is the man.")
    output = renderer.render_hub(ch, max_chapter=151)
    assert 'prev: ""' in output


def test_psalm_hub_last_chapter_no_next(renderer):
    ch = Chapter(book="Psalms", number=151)
    ch.verses[1] = Verse(number=1, text="I was small among my brothers.")
    output = renderer.render_hub(ch, max_chapter=151)
    assert 'next: ""' in output


# ── Contract 2: Hub up: still plural ──────────────────────────────────────────

def test_psalm_hub_up_link_stays_plural(renderer, psalms50_chapter):
    output = renderer.render_hub(psalms50_chapter, max_chapter=151)
    assert 'up: "[[Psalms]]"' in output, "up: must still link to [[Psalms]] (book index)"


# ── Contract 3: Modes bar singular links ──────────────────────────────────────

def test_psalm_modes_bar_osb_link_singular(renderer, psalms50_chapter):
    output = renderer.render_hub(psalms50_chapter, max_chapter=151)
    assert "[[Psalm 50|OSB]]" in output
    assert "[[Psalms 50|OSB]]" not in output


def test_psalm_modes_bar_lexham_link_singular(renderer, psalms50_chapter):
    output = renderer.render_hub(psalms50_chapter, max_chapter=151)
    assert "[[Psalm 50 \u2014 Lexham|Lexham]]" in output
    assert "[[Psalms 50 \u2014 Lexham|Lexham]]" not in output


def test_psalm_modes_bar_lxx_link_singular(renderer, psalms50_chapter):
    output = renderer.render_hub(psalms50_chapter, max_chapter=151)
    assert "[[Psalm 50 \u2014 LXX|LXX]]" in output
    assert "[[Psalms 50 \u2014 LXX|LXX]]" not in output


def test_psalm_modes_bar_net_notes_link_singular(renderer, psalms50_chapter):
    output = renderer.render_hub(psalms50_chapter, max_chapter=151)
    assert "[[Psalm 50 \u2014 NET Notes|NET Notes]]" in output
    assert "[[Psalms 50 \u2014 NET Notes|NET Notes]]" not in output


# ── Contract 4: Text companion hub: frontmatter ───────────────────────────────

def test_psalm_text_companion_hub_link_singular(renderer, psalms50_chapter):
    output = renderer.render_text_companion(psalms50_chapter, source="LXX")
    assert 'hub: "[[Psalm 50]]"' in output
    assert "[[Psalms 50]]" not in output


# ── Contract 5: ObsidianWriter file paths ─────────────────────────────────────

def test_writer_hub_path_singular(writer, psalms50_chapter):
    content = "---\n---\ntest"
    path = writer.write_hub(psalms50_chapter, content)
    assert path.endswith("Psalm 50.md"), f"Expected 'Psalm 50.md', got: {path}"
    assert "Psalms 50.md" not in path


def test_writer_text_companion_path_singular(writer, psalms50_chapter):
    content = "---\n---\ntest"
    path = writer.write_text_companion(psalms50_chapter, "LXX", content)
    assert "Psalm 50 \u2014 LXX.md" in path
    assert "Psalms 50" not in path


def test_writer_notes_path_singular(writer, psalms50_chapter):
    notes = ChapterNotes(book="Psalms", chapter=50, source="Lexham")
    content = "---\n---\ntest"
    path = writer.write_notes(notes, content)
    assert "Psalm 50 \u2014 Lexham Notes.md" in path
    assert "Psalms 50" not in path


# ── Contract 6: Non-Psalm books unaffected ────────────────────────────────────

def test_genesis_hub_uses_book_name(renderer, genesis1_chapter):
    output = renderer.render_hub(genesis1_chapter, max_chapter=50)
    assert "[[Genesis 1|OSB]]" in output or "Genesis 1" in output


def test_genesis_writer_path_unchanged(writer, genesis1_chapter):
    content = "---\n---\ntest"
    path = writer.write_hub(genesis1_chapter, content)
    assert path.endswith("Genesis 1.md")
