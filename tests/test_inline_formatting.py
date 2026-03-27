"""Unit tests for inline Markdown formatting in verse text extraction."""
from bs4 import BeautifulSoup
from vault_builder.adapters.sources.eob_epub import _walk, _add_text


def _extract(html: str) -> str:
    """Parse an HTML paragraph snippet and return accumulated verse text."""
    soup = BeautifulSoup(f"<p class='msonormal1'>{html}</p>", "lxml")
    p = soup.find("p")
    raw: dict = {}
    _walk(p, 1, "TestBook", 1, raw)
    return raw.get("TestBook", {}).get(1, {}).get(1, "")


def test_eob_italic_preserved():
    result = _extract("The <i>logos</i> was with God")
    assert "*logos*" in result


def test_eob_bold_preserved():
    result = _extract("This is <b>important</b> text")
    assert "**important**" in result


def test_eob_italic_skips_ednref():
    """Endnote anchor inside <i> must not appear in the italic text."""
    result = _extract('<i>word<a id="_ednref5" href="#edn5">[5]</a></i>')
    assert "*word*" in result
    assert "[5]" not in result


def test_eob_plain_text_unchanged():
    result = _extract("In the beginning was the Word")
    assert "In the beginning was the Word" in result
    assert "*" not in result


# ── ES2 (Esdras B) chapter-offset split ──────────────────────────────────────

from vault_builder.adapters.sources.lexham_epub import _CHAPTER_ANCHOR_RE, LEXHAM_CODE_TO_BOOK


def test_es2_chapter_anchor_regex_matches():
    """ES2.11 should match the chapter anchor regex and give chapter 11."""
    m = _CHAPTER_ANCHOR_RE.match("ES2.11")
    assert m is not None
    assert m.group(1) == "ES2"
    assert int(m.group(2)) == 11


def test_es2_not_in_book_map():
    """ES2 must NOT appear in LEXHAM_CODE_TO_BOOK (handled separately)."""
    assert "ES2" not in LEXHAM_CODE_TO_BOOK


def test_ezra_nehemiah_in_book_map_indirectly():
    """Ezra and Nehemiah target names are valid vault books."""
    from vault_builder.domain.canon import BOOK_CHAPTER_COUNT
    assert "Ezra" in BOOK_CHAPTER_COUNT
    assert "Nehemiah" in BOOK_CHAPTER_COUNT
