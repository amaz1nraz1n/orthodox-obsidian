"""
PER-39: Regression suite for per-note anchor_ids across NET, EOB, and OSB.

Contracts:
  1. NET _parse_notes sets anchor_id on the first StudyNote of each EPUB para;
     all notes in that para share the same sort_key (para_index).
  2. EOB read_notes sets anchor_id='ednN', sort_key=N on each StudyNote.
  3. render_notes emits ^anchor_id block IDs on the callout line.
  4. render_net_notes emits ^anchor_id block IDs on the callout line.
  5. NET text companion links to #^nNNNNN (not #^vN).
  6. OSB anchor_id/sort_key behaviour is unchanged (defaults: None/0).
"""

import io
import warnings
import zipfile

import pytest
from bs4 import XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.sources.net_epub import NetEpubSource
from vault_builder.domain.models import ChapterNotes, NoteType, StudyNote

renderer = ObsidianRenderer()


# ── NET fixtures ──────────────────────────────────────────────────────────────

_MINIMAL_NCX = """\
<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <navMap>
    <navPoint id="file1040" playOrder="1">
      <navLabel><text>John</text></navLabel>
      <content src="file1040.xhtml"/>
    </navPoint>
  </navMap>
</ncx>"""

# Two note paragraphs: n0001 (tn + sn sub-paras) and n0002 (tn only)
_NET_TEXT = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
<h1>John<br />Chapter 1</h1>
<p class="bodytext">
  <span class="verse">1:1</span> Word<sup><a id="n0001" href="#">1</a></sup>.
  <span class="verse">1:2</span> God<sup><a id="n0002" href="#">2</a></sup>.
</p>
</body></html>"""

_NET_NOTES = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body>
<p id="n0001">
  <p><b>tn</b> Translator note for v1.</p>
  <p><b>sn</b> Study note for v1.</p>
</p>
<p id="n0002">
  <p><b>tn</b> Translator note for v2.</p>
</p>
</body></html>"""


@pytest.fixture
def net_source():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("META-INF/container.xml", "")
        zf.writestr("OEBPS/toc.ncx", _MINIMAL_NCX)
        zf.writestr("OEBPS/file1040.xhtml", "")
        zf.writestr("OEBPS/file1041.xhtml", _NET_TEXT)
        zf.writestr("OEBPS/file1041_notes.xhtml", _NET_NOTES)
    buf.seek(0)
    return NetEpubSource(epub_path=buf)


# ── 1. NET _parse_notes: anchor_id + sort_key ─────────────────────────────────

def test_net_parse_notes_anchor_id_on_first_note(net_source):
    """First StudyNote in each EPUB paragraph gets anchor_id = note_id."""
    notes = net_source.read_notes("John", 1)
    all_notes = notes.translator_notes + notes.footnotes
    n0001_notes = [n for n in all_notes if n.verse_number == 1]
    assert n0001_notes, "Expected notes for verse 1"
    first = n0001_notes[0]
    assert first.anchor_id == "n0001", f"Expected anchor_id='n0001', got {first.anchor_id!r}"


def test_net_parse_notes_second_note_no_anchor_id(net_source):
    """Second StudyNote in the same paragraph has anchor_id=None."""
    notes = net_source.read_notes("John", 1)
    all_notes = notes.translator_notes + notes.footnotes
    v1_notes = [n for n in all_notes if n.verse_number == 1]
    assert len(v1_notes) == 2, f"Expected 2 notes for v1, got {len(v1_notes)}"
    second = v1_notes[1]
    assert second.anchor_id is None, f"Second note in para should have anchor_id=None, got {second.anchor_id!r}"


def test_net_parse_notes_sort_key_same_within_para(net_source):
    """All notes within one EPUB paragraph share the same sort_key."""
    notes = net_source.read_notes("John", 1)
    all_notes = notes.translator_notes + notes.footnotes
    v1_notes = [n for n in all_notes if n.verse_number == 1]
    assert len(v1_notes) == 2
    assert v1_notes[0].sort_key == v1_notes[1].sort_key


def test_net_parse_notes_sort_key_ordering(net_source):
    """Notes from later paragraphs have higher sort_key."""
    notes = net_source.read_notes("John", 1)
    all_notes = notes.translator_notes + notes.footnotes
    v1_note = next(n for n in all_notes if n.verse_number == 1)
    v2_note = next(n for n in all_notes if n.verse_number == 2)
    assert v2_note.sort_key > v1_note.sort_key


# ── 2. EOB read_notes: anchor_id + sort_key ──────────────────────────────────

def test_eob_study_note_anchor_id_field():
    """StudyNote.anchor_id defaults to None (OSB path unchanged)."""
    note = StudyNote(verse_number=1, ref_str="1:1", content="text")
    assert note.anchor_id is None


def test_eob_study_note_sort_key_default():
    """StudyNote.sort_key defaults to 0."""
    note = StudyNote(verse_number=1, ref_str="1:1", content="text")
    assert note.sort_key == 0


def test_eob_study_note_anchor_id_and_sort_key_set():
    """StudyNote accepts explicit anchor_id and sort_key."""
    note = StudyNote(verse_number=3, ref_str="1:3", content="text", anchor_id="edn42", sort_key=42)
    assert note.anchor_id == "edn42"
    assert note.sort_key == 42


# ── 3. render_notes: ^anchor_id block ID on callout line ─────────────────────

def test_render_notes_emits_anchor_id_block_id():
    """render_notes puts ^anchor_id on the callout line when anchor_id is set."""
    notes = ChapterNotes(book="John", chapter=1, source="EOB")
    notes.add_note(NoteType.FOOTNOTE, StudyNote(
        verse_number=1, ref_str="1:1", content="A note.", anchor_id="edn5", sort_key=5
    ))
    output = renderer.render_notes(notes)
    assert "> [!note] 1:1 ^edn5" in output, f"Expected callout with block ID, got:\n{output}"


def test_render_notes_no_block_id_when_anchor_id_none():
    """render_notes omits block ID when anchor_id is None."""
    notes = ChapterNotes(book="John", chapter=1, source="OSB")
    notes.add_note(NoteType.FOOTNOTE, StudyNote(
        verse_number=1, ref_str="1:1", content="A note."
    ))
    output = renderer.render_notes(notes)
    assert "> [!note] 1:1\n" in output, f"Expected callout without block ID, got:\n{output}"


# ── 4. render_net_notes: ^anchor_id block ID on callout line ─────────────────

def test_render_net_notes_emits_anchor_id_block_id():
    """render_net_notes puts ^anchor_id on the callout line when anchor_id is set."""
    notes = ChapterNotes(book="John", chapter=1, source="NET")
    notes.add_note(NoteType.TRANSLATOR, StudyNote(
        verse_number=1, ref_str="1:1", content="TN content.", anchor_id="n0001", sort_key=0
    ))
    output = renderer.render_net_notes(notes)
    assert "> [!tn] 1:1 ^n0001" in output, f"Expected callout with block ID, got:\n{output}"


def test_render_net_notes_no_block_id_when_anchor_id_none():
    """render_net_notes omits block ID when anchor_id is None."""
    notes = ChapterNotes(book="John", chapter=1, source="NET")
    notes.add_note(NoteType.TRANSLATOR, StudyNote(
        verse_number=1, ref_str="1:1", content="TN content."
    ))
    output = renderer.render_net_notes(notes)
    assert "> [!tn] 1:1\n" in output, f"Expected callout without block ID, got:\n{output}"


# ── 5. NET text companion links to per-note anchor ───────────────────────────

def test_net_text_companion_links_to_per_note_anchor(net_source):
    """NET text companion verse text links to #^nNNNNN, not #^vN."""
    ch = net_source.read_chapter("John", 1)
    v1 = ch.verses[1].text
    assert "#^n0001" in v1, f"Expected #^n0001 in v1 text, got: {v1!r}"
    assert "#^v1" not in v1, f"Verse-section anchor #^v1 must not appear: {v1!r}"


# ── 6. OSB: sort_key and anchor_id unchanged (defaults) ──────────────────────

def test_osb_notes_sort_key_defaults_stable():
    """ChapterNotes.sorted_notes stable-sorts by (verse_number, sort_key=0)."""
    notes = ChapterNotes(book="Genesis", chapter=1, source="OSB")
    notes.add_note(NoteType.FOOTNOTE, StudyNote(verse_number=3, ref_str="1:3", content="c"))
    notes.add_note(NoteType.FOOTNOTE, StudyNote(verse_number=1, ref_str="1:1", content="a"))
    notes.add_note(NoteType.FOOTNOTE, StudyNote(verse_number=2, ref_str="1:2", content="b"))
    result = notes.sorted_notes(NoteType.FOOTNOTE)
    assert [n.verse_number for n in result] == [1, 2, 3]
