"""
TDD tests: NetEpubSource EPUB parsing contracts.

Contracts guarded:
  1. read_chapter(book, chapter) → Chapter with correct verse text
  2. Verse text has superscript note refs stripped
  3. Poetry verses spanning multiple <p> elements are joined
  4. read_notes(book, chapter) → ChapterNotes with source="NET"
  5. Note type mapping: tn→translator_notes, tc→variants, sn→footnotes, map→background_notes
  6. Notes correctly attributed to verses via text-file anchor cross-reference
  7. Multi-typed note entries (tn + sn in one <p id="nXXX">) expand to separate notes
  8. Psalm LXX→MT chapter conversion for file lookup (LXX 50 = MT 51)
"""
import io
import zipfile

import pytest

from vault_builder.adapters.sources.net_epub import NetEpubSource
from vault_builder.domain.models import Chapter, ChapterNotes


# ── Minimal EPUB fixture builders ─────────────────────────────────────────────

_MINIMAL_NCX_TMPL = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="file{toc}" playOrder="1">
      <navLabel><text>{book}</text></navLabel>
      <content src="file{toc}.xhtml"/>
    </navPoint>
  </navMap>
</ncx>"""

_JOHN1_TEXT = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1>John<br />Chapter 1</h1>
<p class="paragraphtitle">The Prologue</p>
<p class="bodytext"><span class="verse">1:1</span> In the beginning<sup><a id="n430011" href="file2_notes.xhtml#n430011">1</a></sup> was the Word, and the Word was with God. <span class="verse">1:2</span> The Word<sup><a id="n430021" href="file2_notes.xhtml#n430021">2</a></sup> was with God in the beginning. <span class="verse">1:3</span> All things were created<sup><a id="n430031" href="file2_notes.xhtml#n430031">3</a></sup> by him.</p>
</body></html>"""

_JOHN1_NOTES = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h2>Notes for John 1</h2>
<p id="n430011"><a href="file2.xhtml#n430011">1</a> <p><b>tn</b> The Logos was the creative agent.</p><p><b>tc</b> Some MSS omit "in the beginning."</p></p>
<p id="n430021"><a href="file2.xhtml#n430021">2</a> <p><b>sn</b> Reference back to verse 1.</p></p>
<p id="n430031"><a href="file2.xhtml#n430031">3</a> <p><b>map</b> See map of creation accounts.</p></p>
</body></html>"""

_PSALM1_TEXT = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h2>Psalm 1</h2>
<p class="paragraphtitle">Psalm 1<sup><a id="n190011" href="file2_notes.xhtml#n190011">1</a></sup></p>
<p class="poetry"><span class="verse">1:1</span> How blessed<sup><a id="n190012" href="file2_notes.xhtml#n190012">2</a></sup> is the one</p>
<p class="poetry">who does not follow the wicked,</p>
<p class="poetry"><span class="verse">1:2</span> Instead he finds pleasure<sup><a id="n190021" href="file2_notes.xhtml#n190021">3</a></sup> in obeying the Lord.</p>
</body></html>"""

_PSALM1_NOTES = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h2>Notes for Psalms 1</h2>
<p id="n190011"><a href="file2.xhtml#n190011">1</a> <p><b>sn</b> Psalm-level overview note.</p></p>
<p id="n190012"><a href="file2.xhtml#n190012">2</a> <p><b>tn</b> Hebrew abstract plural for happiness.</p></p>
<p id="n190021"><a href="file2.xhtml#n190021">3</a> <p><b>tn</b> He meditates on the law.</p></p>
</body></html>"""


def _make_epub(toc_file: int, ch_file: int, book_ncx: str, text_html: str, notes_html: str) -> io.BytesIO:
    """Build a minimal in-memory EPUB with one book TOC and one chapter pair."""
    ncx = _MINIMAL_NCX_TMPL.format(toc=toc_file, book=book_ncx)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("META-INF/container.xml", "")
        zf.writestr("OEBPS/toc.ncx", ncx)
        zf.writestr(f"OEBPS/file{toc_file}.xhtml", "")  # TOC stub
        zf.writestr(f"OEBPS/file{ch_file}.xhtml", text_html)
        zf.writestr(f"OEBPS/file{ch_file}_notes.xhtml", notes_html)
    buf.seek(0)
    return buf


@pytest.fixture
def john1_epub():
    # John TOC = file1040, John 1 = file1041
    return _make_epub(1040, 1041, "John", _JOHN1_TEXT, _JOHN1_NOTES)


@pytest.fixture
def psalm1_epub():
    # Psalms TOC = file497, Psalm 1 (LXX=MT=1) = file498
    return _make_epub(497, 498, "Psalms", _PSALM1_TEXT, _PSALM1_NOTES)


@pytest.fixture
def john1_source(john1_epub):
    return NetEpubSource(epub_path=john1_epub)


@pytest.fixture
def psalm1_source(psalm1_epub):
    return NetEpubSource(epub_path=psalm1_epub)


# ── Contract 1: read_chapter returns Chapter ──────────────────────────────────


def test_read_chapter_type(john1_source):
    ch = john1_source.read_chapter("John", 1)
    assert isinstance(ch, Chapter)


def test_read_chapter_book_and_number(john1_source):
    ch = john1_source.read_chapter("John", 1)
    assert ch.book == "John"
    assert ch.number == 1


def test_read_chapter_verse_count(john1_source):
    ch = john1_source.read_chapter("John", 1)
    assert len(ch.sorted_verses()) == 3


def test_read_chapter_verse_text_v1(john1_source):
    ch = john1_source.read_chapter("John", 1)
    v1 = ch.verses[1]
    assert "In the beginning" in v1.text
    assert "was the Word" in v1.text


def test_read_chapter_verse_text_v2(john1_source):
    ch = john1_source.read_chapter("John", 1)
    v2 = ch.verses[2]
    assert "Word" in v2.text
    assert "beginning" in v2.text


def test_read_chapter_verse_text_v3(john1_source):
    ch = john1_source.read_chapter("John", 1)
    v3 = ch.verses[3]
    assert "All things" in v3.text


# ── Contract 2: superscript note refs stripped ────────────────────────────────


def test_read_chapter_no_sup_tags(john1_source):
    ch = john1_source.read_chapter("John", 1)
    for v in ch.sorted_verses():
        assert "<sup>" not in v.text


def test_read_chapter_no_raw_note_numbers(john1_source):
    ch = john1_source.read_chapter("John", 1)
    v1 = ch.verses[1]
    # "1" is the note superscript number — must not appear standalone in text
    assert v1.text.strip()[0] != "1"


# ── Contract 3: poetry verses joined across multiple <p> ─────────────────────


def test_poetry_verse_joined(psalm1_source):
    ch = psalm1_source.read_chapter("Psalms", 1)
    v1 = ch.verses[1]
    assert "How blessed" in v1.text
    assert "who does not follow" in v1.text


def test_poetry_verse_count(psalm1_source):
    ch = psalm1_source.read_chapter("Psalms", 1)
    assert len(ch.sorted_verses()) == 2


# ── Contract 4: read_notes returns ChapterNotes ───────────────────────────────


def test_read_notes_type(john1_source):
    notes = john1_source.read_notes("John", 1)
    assert isinstance(notes, ChapterNotes)


def test_read_notes_book_chapter_source(john1_source):
    notes = john1_source.read_notes("John", 1)
    assert notes.book == "John"
    assert notes.chapter == 1
    assert notes.source == "NET"


# ── Contract 5: note type mapping ────────────────────────────────────────────


def test_tn_goes_to_translator_notes(john1_source):
    notes = john1_source.read_notes("John", 1)
    assert len(notes.translator_notes) >= 1
    assert any("Logos" in n.content or "creative" in n.content for n in notes.translator_notes)


def test_tc_goes_to_variants(john1_source):
    notes = john1_source.read_notes("John", 1)
    assert len(notes.variants) >= 1
    assert any("MSS" in n.content for n in notes.variants)


def test_sn_goes_to_footnotes(john1_source):
    notes = john1_source.read_notes("John", 1)
    assert len(notes.footnotes) >= 1
    assert any("Reference" in n.content or "verse 1" in n.content for n in notes.footnotes)


def test_map_goes_to_background_notes(john1_source):
    notes = john1_source.read_notes("John", 1)
    assert len(notes.background_notes) >= 1
    assert any("map" in n.content.lower() or "creation" in n.content.lower() for n in notes.background_notes)


def test_map_does_not_go_to_cross_references(john1_source):
    notes = john1_source.read_notes("John", 1)
    assert len(notes.cross_references) == 0


# ── Contract 6: verse attribution ─────────────────────────────────────────────


def test_notes_attributed_to_correct_verse(john1_source):
    notes = john1_source.read_notes("John", 1)
    v1_tns = [n for n in notes.translator_notes if n.verse_number == 1]
    v2_fns = [n for n in notes.footnotes if n.verse_number == 2]
    v3_bg = [n for n in notes.background_notes if n.verse_number == 3]
    assert len(v1_tns) == 1
    assert len(v2_fns) == 1
    assert len(v3_bg) == 1


def test_notes_ref_str_format(john1_source):
    notes = john1_source.read_notes("John", 1)
    v1_tn = next(n for n in notes.translator_notes if n.verse_number == 1)
    assert v1_tn.ref_str == "1:1"


# ── Contract 7: multi-typed note entry expands to separate notes ──────────────


def test_multi_typed_entry_expands(john1_source):
    """n430011 has both <b>tn</b> and <b>tc</b> — must produce two separate notes."""
    notes = john1_source.read_notes("John", 1)
    v1_tns = [n for n in notes.translator_notes if n.verse_number == 1]
    v1_tc = [n for n in notes.variants if n.verse_number == 1]
    assert len(v1_tns) == 1, "Expected one tn note for v1"
    assert len(v1_tc) == 1, "Expected one tc note for v1"


# ── Contract 8: Psalm LXX chapter → MT file lookup ───────────────────────────


def test_psalm_lxx_chapter_used_in_result(psalm1_source):
    """ChapterNotes.chapter should carry the LXX chapter number (1), not MT."""
    notes = psalm1_source.read_notes("Psalms", 1)
    assert notes.chapter == 1


def test_psalm_verse_attr_correct(psalm1_source):
    notes = psalm1_source.read_notes("Psalms", 1)
    v1_tns = [n for n in notes.translator_notes if n.verse_number == 1]
    v2_tns = [n for n in notes.translator_notes if n.verse_number == 2]
    assert len(v1_tns) == 1
    assert len(v2_tns) == 1


def test_psalm_intro_note_at_verse_zero(psalm1_source):
    """n190011 is in a paragraphtitle → mapped to verse 0 with ref_str 'intro'."""
    notes = psalm1_source.read_notes("Psalms", 1)
    intro_notes = [
        n for n in notes.footnotes + notes.variants + notes.translator_notes
        if n.verse_number == 0
    ]
    assert len(intro_notes) >= 1
    assert all(n.ref_str == "intro" for n in intro_notes)
    # Verse-attributed notes still have verse_number >= 1
    verse_notes = [
        n for n in notes.footnotes + notes.variants + notes.translator_notes
        if n.verse_number != 0
    ]
    for n in verse_notes:
        assert n.verse_number >= 1
