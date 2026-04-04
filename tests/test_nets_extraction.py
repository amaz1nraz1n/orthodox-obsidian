"""
Tests for NetsEpubSource — NETS LXX EPUB adapter.

Covers: verse parsing (three marker patterns), book boundary detection,
intro/text delimiter, footnote resolution from page files, note type routing,
Psalm LXX-primary numbering, sample filtering, and output naming.

All NETS footnotes route to NoteType.TRANSLATOR (user decision 3-A).
"""
import re
import warnings

import pytest
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

EPUB_PATH = "./source_files/Old Testament /A new English translation of the Septuagint.epub"

_SAMPLE: set[tuple[str, int]] = {
    ("Genesis", 1),
    ("Psalms", 50),
    ("Isaiah", 7),
}


# ── Fixtures (real EPUB) ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def source():
    from vault_builder.adapters.sources.nets_epub import NetsEpubSource
    return NetsEpubSource(EPUB_PATH, sample_only=True, sample_chapters=_SAMPLE)


@pytest.fixture(scope="module")
def books(source):
    return {b.name: b for b in source.read_text()}


@pytest.fixture(scope="module")
def notes_list(source):
    return list(source.read_notes())


@pytest.fixture(scope="module")
def intros_list(source):
    return list(source.read_intros())


# ── Verse counts ──────────────────────────────────────────────────────────────

def test_genesis_1_verse_count(books):
    """Genesis 1 has 31 verses."""
    ch = books["Genesis"].chapters[1]
    assert len(ch.verses) == 31


def test_psalm_50_verse_count(books):
    """Psalm 50 (LXX) = Psalm 51 (MT) has 21 verses (2 superscription + 19 content)."""
    ch = books["Psalms"].chapters[50]
    assert len(ch.verses) == 21


# ── Known verse text ──────────────────────────────────────────────────────────

def test_genesis_1_1(books):
    text = books["Genesis"].chapters[1].verses[1].text
    assert "beginning" in text.lower()
    assert "God" in text


def test_genesis_1_2(books):
    """Verse 2 follows immediately — confirms plain-text paragraph-start pattern."""
    text = books["Genesis"].chapters[1].verses[2].text
    assert text.strip()


def test_psalm_50_3(books):
    """Psalm 50 (LXX) verse 3 ≈ 'Have mercy on me, O God'."""
    ch = books["Psalms"].chapters[50]
    text = ch.verses[3].text
    assert "mercy" in text.lower()
    assert "God" in text


def test_isaiah_7_14(books):
    """Isaiah 7:14 — LXX uses 'the virgin'."""
    text = books["Isaiah"].chapters[7].verses[14].text
    assert "virgin" in text.lower() or "sign" in text.lower()


# ── No verse merge ────────────────────────────────────────────────────────────

def test_no_double_verse_number_in_text(books):
    """No verse text body should contain a leading bare digit (leaked verse number)."""
    digit_re = re.compile(r"^\d+\s")
    for book in books.values():
        for ch in book.chapters.values():
            for verse in ch.verses.values():
                assert not digit_re.match(verse.text), (
                    f"{book.name} {ch.number}:{verse.number} text starts with digit: {verse.text[:40]!r}"
                )


# ── Note slot routing ─────────────────────────────────────────────────────────

def test_notes_exist_for_isaiah_7(notes_list):
    """Isaiah 7 has translator notes (Genesis 1 has none in NETS)."""
    isaiah_notes = [n for n in notes_list if n.book == "Isaiah" and n.chapter == 7]
    assert isaiah_notes, "Expected at least one ChapterNotes for Isaiah 7"


def test_all_notes_are_translator(notes_list):
    """All NETS notes must route to NoteType.TRANSLATOR (user decision 3-A)."""
    assert notes_list, "Expected some notes"
    for n in notes_list:
        assert n.translator_notes, f"Expected translator_notes in {n.book} {n.chapter}"
        assert not n.variants, f"No VARIANT slot expected in {n.book} {n.chapter}"
        assert not n.alternatives, f"No ALTERNATIVE slot expected in {n.book} {n.chapter}"


# ── Intros ────────────────────────────────────────────────────────────────────

def test_intros_produced(intros_list):
    """Intros should be extracted for sampled books."""
    assert intros_list, "Expected at least one BookIntro"


def test_genesis_intro_present(intros_list):
    books_with_intros = {i.book for i in intros_list}
    assert "Genesis" in books_with_intros


# ── Sample filtering ──────────────────────────────────────────────────────────

def test_sample_only_excludes_other_books(books):
    """In sample mode only sampled books appear."""
    for name in books:
        assert name in {"Genesis", "Psalms", "Isaiah"}, f"Unexpected book: {name}"


# ── Unit: verse marker parsing ────────────────────────────────────────────────

def _make_source():
    from vault_builder.adapters.sources.nets_epub import NetsEpubSource
    return NetsEpubSource(epub_path="dummy.epub", sample_only=False)


_CHAPTER_OPEN = """
<p class="noindent"><strong>1</strong> In the beginning God made the sky and the earth.
<sup>2</sup>Yet the earth was invisible and unformed, and darkness was over the abyss,
and a divine wind was being carried along over the water.
</p>
"""

_MID_PARA = """
<p class="indent"><sup>7</sup>And God made the firmament, and God separated
<sup>8</sup>And God called the firmament Sky.</p>
"""

_NEW_PARA_VERSE = """
<p class="indent">6 And God said, "Let a firmament come into being
<sup>7</sup>And God made the firmament.</p>
"""


def test_parse_strong_verse_marker():
    """Pattern 1: <strong>1</strong> at chapter open yields verse 1."""
    src = _make_source()
    events = list(src._walk_para(BeautifulSoup(_CHAPTER_OPEN, "lxml").find("p")))
    starts = [v for k, v in events if k == "verse_start"]
    assert 1 in starts
    assert 2 in starts


def test_parse_sup_verse_marker():
    """Pattern 2: <sup>N</sup> mid-paragraph yields verse boundaries."""
    src = _make_source()
    events = list(src._walk_para(BeautifulSoup(_MID_PARA, "lxml").find("p")))
    starts = [v for k, v in events if k == "verse_start"]
    assert 7 in starts
    assert 8 in starts


def test_parse_plain_text_verse_marker():
    """Pattern 3: bare '6 ' at paragraph start yields verse 6."""
    src = _make_source()
    events = list(src._walk_para(BeautifulSoup(_NEW_PARA_VERSE, "lxml").find("p")))
    starts = [v for k, v in events if k == "verse_start"]
    assert 6 in starts


# ── Unit: GBS anchor stripping ────────────────────────────────────────────────

_GBS_PARA = """
<p class="noindent"><a id="GBS.0001.01"/><strong>1</strong> In the beginning God made the sky.</p>
"""


def test_gbs_anchor_stripped_from_text():
    """GBS anchors must not bleed into verse text."""
    src = _make_source()
    events = list(src._walk_para(BeautifulSoup(_GBS_PARA, "lxml").find("p")))
    texts = [v for k, v in events if k == "text"]
    combined = " ".join(texts)
    assert "GBS" not in combined
    assert "0001" not in combined


# ── Unit: Psalm LXX-primary numbering ────────────────────────────────────────

def test_psalm_lxx_number_extracted():
    """Verse marker <sup>3(1)</sup> → yield verse 3 (LXX primary, not 1)."""
    src = _make_source()
    html = '<p class="indenthanging1a"><sup>3(1)</sup>Have mercy on me, O God.</p>'
    events = list(src._walk_para(BeautifulSoup(html, "lxml").find("p")))
    starts = [v for k, v in events if k == "verse_start"]
    assert starts == [3], f"Expected [3], got {starts}"


# ── Unit: intro/text boundary ─────────────────────────────────────────────────

_INTRO_WITH_ATTR = """
<html><body>
<h2 class="h2">Genesis</h2>
<p>Some intro text here.</p>
<p>More intro text.</p>
<p class="attribute">ROBERT J. V. HIEBERT</p>
<p class="noindent"><strong>1</strong> In the beginning God made the sky.</p>
</body></html>
"""


def test_attribute_para_is_intro_text_boundary():
    """Everything before <p class='attribute'> is intro; after is Bible text."""
    src = _make_source()
    intro_text, bible_paras = src._split_intro_and_text(
        BeautifulSoup(_INTRO_WITH_ATTR, "lxml")
    )
    assert "Some intro text" in intro_text
    assert len(bible_paras) >= 1
    # Bible text paragraph should not contain "intro text"
    bible_combined = " ".join(p.get_text() for p in bible_paras)
    assert "intro text" not in bible_combined
    assert "beginning" in bible_combined


# ── Unit: footnote resolution ─────────────────────────────────────────────────

_INLINE_MARKER = """
<p class="noindent"><strong>1</strong> In the beginning
<sup><a id="pg001en_e"/><a class="nounder" href="page_001.html#pg001ene">e</a></sup>
God made the sky.</p>
"""

_PAGE_HTML = """
<html><body>
<p class="endnote"><a id="pg001ene"/>
  <sup><a class="nounder" href="chapter01.html#pg001en_e">e</a></sup>
  Or <em>created</em>
</p>
</body></html>
"""


def test_footnote_marker_yields_anchor_id():
    """Inline footnote marker yields a footnote_ref event with the anchor ID."""
    src = _make_source()
    events = list(src._walk_para(BeautifulSoup(_INLINE_MARKER, "lxml").find("p")))
    # footnote_ref events are 3-tuples: (kind, anchor_id, page_file)
    refs = [ev[1] for ev in events if ev[0] == "footnote_ref"]
    assert "pg001ene" in refs


def test_resolve_footnote_from_page_html():
    """_resolve_footnote finds note text in a page_N.html endnote paragraph."""
    src = _make_source()
    text = src._resolve_footnote_from_html("pg001ene", _PAGE_HTML)
    assert text is not None
    assert "Or" in text or "created" in text
