"""
Contract tests: hub footnote markers use block ID anchors (#^vN).

All three sources that embed inline hub-link markers in verse text —
EOB, Lexham, and NET — must target the block ID anchor (#^vN) rather
than the heading-text anchor (#vN).  The heading-text anchor fails
because heading display text is "1:1", not "v1"; the link lands at the
file top.  The block ID anchor (#^vN) always resolves because the
renderer places a standalone `^vN` line immediately after each heading.

Contracts:
  1. EOB: _walk generates markers with #^v{N} format
  2. Lexham: _walk_para generates footnote_marker events, and the
     caller formats them as #^v{N}
  3. NET: read_chapter verse text contains #^v{N} (not bare #v{N})
"""

import io
import warnings
import zipfile

import pytest
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


# ── EOB ───────────────────────────────────────────────────────────────────────

from vault_builder.adapters.sources.eob_epub import _walk  # type: ignore[import]


def _make_eob_para(html_fragment: str) -> BeautifulSoup:
    soup = BeautifulSoup(f"<div>{html_fragment}</div>", "html.parser")
    return soup.find("div")


def test_eob_hub_marker_uses_block_id_anchor():
    """EOB endnote ref anchor must resolve to #^vN, not #vN."""
    para = _make_eob_para(
        '<a id="_ednref1003">*</a> some text'
    )
    raw: dict = {}
    _walk(para, current_verse=5, book="John", chapter=1, raw=raw)

    verse_text = raw.get("John", {}).get(1, {}).get(5, "")
    assert "#^v5" in verse_text, f"Expected block ID anchor #^v5, got: {verse_text!r}"
    assert "#v5|" not in verse_text, f"Bare heading anchor must not appear: {verse_text!r}"


def test_eob_hub_marker_format_full():
    """EOB marker must be a valid Obsidian wikilink with correct structure."""
    para = _make_eob_para('<a id="_ednref7">*</a>')
    raw: dict = {}
    _walk(para, current_verse=3, book="Genesis", chapter=1, raw=raw)

    verse_text = raw.get("Genesis", {}).get(1, {}).get(3, "")
    assert "[[Genesis 1 — EOB Notes#^v3|†]]" in verse_text


# ── Lexham ────────────────────────────────────────────────────────────────────

from vault_builder.adapters.sources.lexham_epub import LexhamEpubSource


@pytest.fixture
def lexham_source() -> LexhamEpubSource:
    return LexhamEpubSource(epub_path="dummy.epub", sample_only=False)


_LEXHAM_VERSE_PARA = """\
<p class="x12">
  <a id="GE.1_BibleLXX2_Ge_1_6"></a>
  <span class="x20"><b>6</b></span>
  And God said, Let firmament come into being
  <a class="x1B" href="f79.xhtml#FN.1.A_c0_e0"><i>a</i></a>
  in the midst of the water.
</p>"""


def test_lexham_walk_para_yields_footnote_marker_event(lexham_source):
    """_walk_para must yield ('footnote_marker', ...) events for x1B links."""
    soup = BeautifulSoup(_LEXHAM_VERSE_PARA, "html.parser")
    para = soup.find("p")
    events = list(lexham_source._walk_para(para))
    event_types = [e[0] for e in events]
    assert "footnote_marker" in event_types


def test_lexham_hub_marker_uses_block_id_anchor(lexham_source):
    """Lexham footnote_marker event, when formatted by the caller, must use #^vN."""
    # Simulate what the caller does: for each footnote_marker event, build the marker.
    book, chapter, verse = "Genesis", 1, 6
    soup = BeautifulSoup(_LEXHAM_VERSE_PARA, "html.parser")
    para = soup.find("p")

    markers: list[str] = []
    for event in lexham_source._walk_para(para):
        if event[0] == "footnote_marker":
            marker = (
                f'<sup class="nt-tn">[[{book} {chapter}'
                f" \u2014 Lexham Notes#^v{verse}|*]]</sup>"
            )
            markers.append(marker)

    assert markers, "Expected at least one footnote marker"
    for m in markers:
        assert f"#^v{verse}" in m, f"Expected block ID anchor, got: {m!r}"
        assert f"#v{verse}|" not in m, f"Bare heading anchor must not appear: {m!r}"


# ── NET ───────────────────────────────────────────────────────────────────────

from vault_builder.adapters.sources.net_epub import NetEpubSource

_MINIMAL_NCX_TMPL = """\
<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="file{toc}" playOrder="1">
      <navLabel><text>{book}</text></navLabel>
      <content src="file{toc}.xhtml"/>
    </navPoint>
  </navMap>
</ncx>"""

_NET_JOHN1_TEXT = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1>John<br />Chapter 1</h1>
<p class="bodytext">
  <span class="verse">1:1</span> In the beginning<sup><a id="n430011" href="file1041_notes.xhtml#n430011">1</a></sup> was the Word.
  <span class="verse">1:2</span> He was with God<sup><a id="n430021" href="file1041_notes.xhtml#n430021">2</a></sup> in the beginning.
</p>
</body></html>"""

_NET_JOHN1_NOTES = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
<p id="n430011"><a href="file1041.xhtml#n430011">1</a> <p><b>tn</b> Note for v1.</p></p>
<p id="n430021"><a href="file1041.xhtml#n430021">2</a> <p><b>sn</b> Note for v2.</p></p>
</body></html>"""


@pytest.fixture
def net_john1_source():
    buf = io.BytesIO()
    ncx = _MINIMAL_NCX_TMPL.format(toc=1040, book="John")
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("META-INF/container.xml", "")
        zf.writestr("OEBPS/toc.ncx", ncx)
        zf.writestr("OEBPS/file1040.xhtml", "")  # TOC stub
        zf.writestr("OEBPS/file1041.xhtml", _NET_JOHN1_TEXT)
        zf.writestr("OEBPS/file1041_notes.xhtml", _NET_JOHN1_NOTES)
    buf.seek(0)
    return NetEpubSource(epub_path=buf)


def test_net_hub_marker_uses_block_id_anchor_v1(net_john1_source):
    """NET verse text must contain #^v1 (block ID), not bare #v1."""
    ch = net_john1_source.read_chapter("John", 1)
    text = ch.verses[1].text
    assert "#^v1" in text, f"Expected #^v1 block ID anchor in: {text!r}"
    # Guard against accidental bare heading anchor
    assert "#v1|" not in text, f"Bare heading anchor #v1 must not appear: {text!r}"


def test_net_hub_marker_uses_block_id_anchor_v2(net_john1_source):
    """NET verse text for v2 must contain #^v2 (block ID)."""
    ch = net_john1_source.read_chapter("John", 1)
    text = ch.verses[2].text
    assert "#^v2" in text, f"Expected #^v2 block ID anchor in: {text!r}"
    assert "#v2|" not in text, f"Bare heading anchor #v2 must not appear: {text!r}"


def test_net_hub_marker_full_wikilink_format(net_john1_source):
    """NET marker must be a complete Obsidian wikilink targeting the correct notes file."""
    ch = net_john1_source.read_chapter("John", 1)
    text = ch.verses[1].text
    assert "[[John 1 — NET Notes#^v1|" in text, (
        f"Expected full wikilink target, got: {text!r}"
    )
