"""Tests for render_book_index and write_book_index."""
import pytest
from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.domain.canon import BOOK_CHAPTER_COUNT


@pytest.fixture
def renderer():
    return ObsidianRenderer()


def test_john_index_has_all_chapters(renderer):
    out = renderer.render_book_index("John")
    for ch in range(1, 22):
        assert f"[[John {ch}]]" in out


def test_psalms_index_uses_psalm_prefix(renderer):
    out = renderer.render_book_index("Psalms")
    assert "[[Psalm 1]]" in out
    assert "[[Psalm 151]]" in out
    assert "[[Psalms 1]]" not in out


def test_genesis_index_frontmatter(renderer):
    out = renderer.render_book_index("Genesis")
    assert 'testament: "OT"' in out
    assert 'genre: "Torah"' in out
    assert 'book_id: "Gen"' in out
    assert 'cssclasses: [book-index]' in out


def test_nt_index_up_link(renderer):
    out = renderer.render_book_index("Romans")
    assert 'up: "[[02 - New Testament]]"' in out


def test_ot_index_up_link(renderer):
    out = renderer.render_book_index("Isaiah")
    assert 'up: "[[01 - Old Testament]]"' in out


def test_all_books_render_without_error(renderer):
    for book in BOOK_CHAPTER_COUNT:
        out = renderer.render_book_index(book)
        assert f"# {book}" in out
        assert "[[" in out
