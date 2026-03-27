"""
Regression tests: Lexham notes extraction — pure-function unit tests.

Contracts guarded:
  1. _load_footnote_definitions parses anchor IDs and note text from synthetic HTML.
  2. _load_footnote_definitions strips the leading letter sigil from note text.
  3. _load_footnote_definitions ignores non-FN anchors.
  4. _walk_node_for_notes yields verse_start events from verse anchors.
  5. _walk_node_for_notes yields footnote_ref events from x1B links.
  6. footnote_ref is attributed to the verse anchor that precedes it in DOM order.
"""
import warnings

import pytest
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from vault_builder.adapters.sources.lexham_epub import LexhamEpubSource

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


@pytest.fixture
def source() -> LexhamEpubSource:
    return LexhamEpubSource(epub_path="dummy.epub", sample_only=False)


# ── _load_footnote_definitions ────────────────────────────────────────────────

_F79_SNIPPET = """
<html><body>
<p class="BM1">Genesis</p>
<p class="List1"><a id="FN.1.A_c0_e0"></a>aLit. "of the water and of the water"</p>
<p class="List1"><a id="FN.1.B_c0_e0"></a>bOr "sky"</p>
<p class="List1"><a id="FN.3.A_c0_e0"></a>aLit. "you will die the death"</p>
<p class="List1"><a id="OTHER_ANCHOR_c0_e0"></a>should be ignored</p>
<p class="BM1">Exodus</p>
<p class="List1"><a id="FN.63.A_c0_e0"></a>aLit. "not when"</p>
</body></html>
"""


def test_load_footnote_definitions_parses_known_anchors():
    result = LexhamEpubSource._load_footnote_definitions(_F79_SNIPPET)
    assert "FN.1.A_c0_e0" in result
    assert "FN.1.B_c0_e0" in result
    assert "FN.3.A_c0_e0" in result
    assert "FN.63.A_c0_e0" in result


def test_load_footnote_definitions_strips_letter_sigil():
    result = LexhamEpubSource._load_footnote_definitions(_F79_SNIPPET)
    assert result["FN.1.A_c0_e0"] == 'Lit. "of the water and of the water"'
    assert result["FN.1.B_c0_e0"] == 'Or "sky"'
    assert result["FN.63.A_c0_e0"] == 'Lit. "not when"'


def test_load_footnote_definitions_ignores_non_fn_anchors():
    result = LexhamEpubSource._load_footnote_definitions(_F79_SNIPPET)
    assert "OTHER_ANCHOR_c0_e0" not in result


def test_load_footnote_definitions_count(source):
    result = LexhamEpubSource._load_footnote_definitions(_F79_SNIPPET)
    assert len(result) == 4


# ── _walk_node_for_notes ──────────────────────────────────────────────────────

_VERSE_PARA = """
<p class="x12">
  <a id="GE.1_BibleLXX2_Ge_1_6"></a>
  <span class="x20"><b>6</b></span>
  And God said, "Let a firmament come into being
  <a class="x1B" href="f79.xhtml#FN.1.A_c0_e0"><i>a</i></a>
  in the midst of the water.
  <a class="x1B" href="f79.xhtml#FN.1.B_c0_e0"><i>b</i></a>
  <a id="GE.1_BibleLXX2_Ge_1_7"></a>
  And God made the firmament.
  <a class="x1B" href="f79.xhtml#FN.1.C_c0_e0"><i>c</i></a>
</p>
"""


def _events(source, html):
    soup = BeautifulSoup(html, "lxml")
    para = soup.find("p")
    return list(source._walk_node_for_notes(para))


def test_walk_node_yields_verse_start_events(source):
    events = _events(source, _VERSE_PARA)
    verse_starts = [e for e in events if e[0] == "verse_start"]
    assert len(verse_starts) == 2
    assert ("verse_start", 6) in verse_starts
    assert ("verse_start", 7) in verse_starts


def test_walk_node_yields_footnote_ref_events(source):
    events = _events(source, _VERSE_PARA)
    fn_refs = [e for e in events if e[0] == "footnote_ref"]
    assert len(fn_refs) == 3
    assert ("footnote_ref", "FN.1.A_c0_e0") in fn_refs
    assert ("footnote_ref", "FN.1.B_c0_e0") in fn_refs
    assert ("footnote_ref", "FN.1.C_c0_e0") in fn_refs


def test_walk_node_footnote_attributed_to_preceding_verse(source):
    """FN.1.A and FN.1.B follow verse 6; FN.1.C follows verse 7."""
    events = _events(source, _VERSE_PARA)
    current_verse = None
    verse_to_fns: dict[int, list[str]] = {}
    for kind, val in events:
        if kind == "verse_start":
            current_verse = val
        elif kind == "footnote_ref" and current_verse is not None:
            verse_to_fns.setdefault(current_verse, []).append(val)
    assert verse_to_fns[6] == ["FN.1.A_c0_e0", "FN.1.B_c0_e0"]
    assert verse_to_fns[7] == ["FN.1.C_c0_e0"]
