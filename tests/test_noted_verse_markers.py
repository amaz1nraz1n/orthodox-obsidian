"""
TDD: inline noted-verse markers and notes-companion verse links.

Covers:
  A. Each NoteType → correct symbol (or no symbol) in text companion
  B. Multi-type combinations on the same verse
  C. Unnoted verses produce no marker
  D. Marker link format [[Notes#vN|symbol]]
  E. Nav notes_suffix suppressed when chapter has no notes
  F. Notes companion verse headings → text companion (non-OSB) or hub (OSB)
  G. Per-source scenarios: EOB, Lexham, Alter, NETS
"""
import pytest

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer, _INLINE_MARKER
from vault_builder.domain.models import Book, Chapter, ChapterNotes, NoteType, StudyNote
from vault_builder.service_layer.extraction import ExtractionMode, ExtractionService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chapter(book: str, ch: int, verses: list[tuple[int, str]]) -> Chapter:
    chapter = Chapter(book=book, number=ch)
    for vnum, text in verses:
        chapter.add_verse(vnum, text)
    return chapter


def _note(verse: int, ch: int, content: str) -> StudyNote:
    return StudyNote(verse_number=verse, ref_str=f"{ch}:{verse}", content=content)


def _noted(notes: ChapterNotes) -> dict[int, set[NoteType]]:
    """Build the noted_verses dict the service would pass to render_text_companion."""
    index: dict[int, set[NoteType]] = {}
    for nt in NoteType:
        for note in notes.sorted_notes(nt):
            if note.verse_number > 0:
                index.setdefault(note.verse_number, set()).add(nt)
    return index


@pytest.fixture
def renderer() -> ObsidianRenderer:
    return ObsidianRenderer()


@pytest.fixture
def simple_chapter() -> Chapter:
    return _chapter("Genesis", 1, [
        (1, "In the beginning God created heaven and earth."),
        (2, "The earth was formless and empty."),
        (3, "God said, Let there be light."),
    ])


# ── A. Single NoteType → correct symbol ──────────────────────────────────────

@pytest.mark.parametrize("note_type, expected_symbol", [
    (NoteType.FOOTNOTE,    "\u2020"),   # †
    (NoteType.TRANSLATOR,  "\u2021"),   # ‡
    (NoteType.CITATION,    "\u203b"),   # ※
    (NoteType.BACKGROUND,  "\u00b6"),   # ¶
    (NoteType.LITURGICAL,  "\u2629"),   # ☩
    (NoteType.VARIANT,     "*"),
    (NoteType.ALTERNATIVE, "\u25ca"),   # ◊
])
def test_single_note_type_produces_correct_symbol(renderer, simple_chapter, note_type, expected_symbol):
    notes = ChapterNotes(book="Genesis", chapter=1, source="TestSource")
    notes.add_note(note_type, _note(2, 1, "A note on verse 2."))
    noted = _noted(notes)

    out = renderer.render_text_companion(simple_chapter, "TestSource", noted_verses=noted)
    # Symbol must appear as a link on v2
    assert f"Genesis 1 \u2014 TestSource Notes#v2|{expected_symbol}]]" in out


@pytest.mark.parametrize("note_type", [NoteType.CROSS_REF, NoteType.PARALLEL])
def test_structural_note_types_produce_no_marker(renderer, simple_chapter, note_type):
    notes = ChapterNotes(book="Genesis", chapter=1, source="TestSource")
    notes.add_note(note_type, _note(2, 1, "A structural note."))
    noted = _noted(notes)

    out = renderer.render_text_companion(simple_chapter, "TestSource", noted_verses=noted)
    v2_line = next(l for l in out.splitlines() if f'class="vn">2</span>' in l)
    assert "TestSource Notes#v2" not in v2_line


# ── B. Multi-type combinations on the same verse ─────────────────────────────

def test_footnote_plus_liturgical_on_same_verse(renderer, simple_chapter):
    notes = ChapterNotes(book="Genesis", chapter=1, source="OSB")
    notes.add_note(NoteType.FOOTNOTE,   _note(2, 1, "Study note."))
    notes.add_note(NoteType.LITURGICAL, _note(2, 1, "Liturgical rubric."))
    notes.add_note(NoteType.LITURGICAL, _note(2, 1, "Second liturgical note."))
    noted = _noted(notes)

    out = renderer.render_text_companion(simple_chapter, "OSB", noted_verses=noted)
    v2_line = next(l for l in out.splitlines() if 'class="vn">2</span>' in l)
    # Both symbols must appear in the single combined link
    assert "\u2020" in v2_line   # †
    assert "\u2629" in v2_line   # ☩
    # Only one link, not two separate markers
    assert v2_line.count("OSB Notes#v2") == 1


def test_footnote_plus_variant_on_same_verse(renderer, simple_chapter):
    notes = ChapterNotes(book="Genesis", chapter=1, source="EOB")
    notes.add_note(NoteType.FOOTNOTE, _note(1, 1, "Commentary note."))
    notes.add_note(NoteType.VARIANT,  _note(1, 1, "Textual variant."))
    noted = _noted(notes)

    out = renderer.render_text_companion(simple_chapter, "EOB", noted_verses=noted)
    v1_line = next(l for l in out.splitlines() if 'class="vn">1</span>' in l)
    assert "\u2020" in v1_line   # †
    assert "*" in v1_line        # *
    assert v1_line.count("EOB Notes#v1") == 1


def test_translator_plus_alternative_on_same_verse(renderer, simple_chapter):
    notes = ChapterNotes(book="Genesis", chapter=1, source="Lexham")
    notes.add_note(NoteType.TRANSLATOR,  _note(3, 1, "Translation note."))
    notes.add_note(NoteType.ALTERNATIVE, _note(3, 1, "Or: another reading."))
    noted = _noted(notes)

    out = renderer.render_text_companion(simple_chapter, "Lexham", noted_verses=noted)
    v3_line = next(l for l in out.splitlines() if 'class="vn">3</span>' in l)
    assert "\u2021" in v3_line   # ‡
    assert "\u25ca" in v3_line   # ◊
    assert v3_line.count("Lexham Notes#v3") == 1


def test_all_structural_types_plus_content_type(renderer, simple_chapter):
    """CROSS_REF and PARALLEL don't produce symbols; content type still appears."""
    notes = ChapterNotes(book="Genesis", chapter=1, source="TestSource")
    notes.add_note(NoteType.CROSS_REF, _note(1, 1, "See John 1:1."))
    notes.add_note(NoteType.PARALLEL,  _note(1, 1, "Mt 5:1–3."))
    notes.add_note(NoteType.FOOTNOTE,  _note(1, 1, "Study note."))
    noted = _noted(notes)

    out = renderer.render_text_companion(simple_chapter, "TestSource", noted_verses=noted)
    v1_line = next(l for l in out.splitlines() if 'class="vn">1</span>' in l)
    assert "\u2020" in v1_line                     # † from FOOTNOTE
    assert v1_line.count("TestSource Notes#v1") == 1


# ── C. Unnoted verses produce no marker ──────────────────────────────────────

def test_unnoted_verse_has_no_marker(renderer, simple_chapter):
    notes = ChapterNotes(book="Genesis", chapter=1, source="Alter")
    notes.add_note(NoteType.TRANSLATOR, _note(2, 1, "Only v2 has a note."))
    noted = _noted(notes)

    out = renderer.render_text_companion(simple_chapter, "Alter", noted_verses=noted)
    v1_line = next(l for l in out.splitlines() if 'class="vn">1</span>' in l)
    v3_line = next(l for l in out.splitlines() if 'class="vn">3</span>' in l)
    assert "Alter Notes#v1" not in v1_line
    assert "Alter Notes#v3" not in v3_line


def test_no_noted_verses_means_no_any_marker(renderer, simple_chapter):
    out = renderer.render_text_companion(simple_chapter, "LXX", notes_suffix=None, noted_verses=None)
    assert "LXX Notes" not in out


# ── D. Marker link format ─────────────────────────────────────────────────────

def test_marker_link_targets_notes_file_not_hub(renderer, simple_chapter):
    notes = ChapterNotes(book="Genesis", chapter=1, source="Alter")
    notes.add_note(NoteType.TRANSLATOR, _note(1, 1, "Translation note."))
    noted = _noted(notes)

    out = renderer.render_text_companion(simple_chapter, "Alter", noted_verses=noted)
    # Must link to "Genesis 1 — Alter Notes#v1", not "Genesis 1#v1"
    assert "Genesis 1 \u2014 Alter Notes#v1" in out
    # The bare hub anchor must not appear as a marker (the hub link [[Genesis 1]] is OK,
    # but a marker of the form [[Genesis 1#v1|...]] must not appear)
    import re
    marker_to_hub = re.search(r'\[\[Genesis 1#v1\|', out)
    assert not marker_to_hub, "Marker must not link to hub — should target Notes companion"


def test_marker_link_uses_v_prefix_anchor(renderer, simple_chapter):
    notes = ChapterNotes(book="Genesis", chapter=1, source="Lexham")
    notes.add_note(NoteType.TRANSLATOR, _note(2, 1, "Note on v2."))
    noted = _noted(notes)

    out = renderer.render_text_companion(simple_chapter, "Lexham", noted_verses=noted)
    assert "#v2|" in out, "Anchor must use #vN format"


# ── E. Nav notes_suffix suppressed when no noted verses ──────────────────────

def test_notes_suffix_absent_when_no_noted_verses(renderer, simple_chapter):
    out = renderer.render_text_companion(
        simple_chapter, "NETS", notes_suffix=None, noted_verses=None
    )
    assert "NETS Notes" not in out


def test_notes_suffix_present_when_noted_verses_exist(renderer, simple_chapter):
    notes = ChapterNotes(book="Genesis", chapter=1, source="NETS")
    notes.add_note(NoteType.TRANSLATOR, _note(1, 1, "A translator note."))
    noted = _noted(notes)

    out = renderer.render_text_companion(
        simple_chapter, "NETS",
        notes_suffix="NETS Notes",
        noted_verses=noted,
    )
    assert "[[Genesis 1 \u2014 NETS Notes|NETS Notes]]" in out


# ── F. Notes companion verse headings ────────────────────────────────────────

def test_non_osb_notes_verse_heading_links_to_text_companion(renderer):
    notes = ChapterNotes(book="Genesis", chapter=1, source="Alter")
    notes.add_note(NoteType.TRANSLATOR, _note(2, 1, "welter and waste."))
    out = renderer.render_notes(notes)
    assert "[[Genesis 1 \u2014 Alter#v2|" in out
    assert "[[Genesis 1#v2|" not in out


def test_osb_notes_verse_heading_links_to_hub(renderer):
    notes = ChapterNotes(book="Genesis", chapter=1, source="OSB")
    notes.add_note(NoteType.FOOTNOTE, _note(1, 1, "Creation note."))
    out = renderer.render_notes(notes)
    assert "[[Genesis 1#v1|" in out
    assert "[[Genesis 1 \u2014 OSB#v1|" not in out


def test_eob_notes_verse_heading_links_to_eob_text(renderer):
    notes = ChapterNotes(book="John", chapter=1, source="EOB")
    notes.add_note(NoteType.FOOTNOTE, _note(1, 1, "Logos commentary."))
    out = renderer.render_notes(notes)
    assert "[[John 1 \u2014 EOB#v1|" in out


def test_lexham_notes_verse_heading_links_to_lexham_text(renderer):
    notes = ChapterNotes(book="Genesis", chapter=1, source="Lexham")
    notes.add_note(NoteType.TRANSLATOR, _note(6, 1, "Lit. 'of the water'."))
    out = renderer.render_notes(notes)
    assert "[[Genesis 1 \u2014 Lexham#v6|" in out


# ── G. Per-source scenarios ───────────────────────────────────────────────────

# EOB: FOOTNOTE(†), VARIANT(*), ALTERNATIVE(◊)

def test_eob_footnote_marker(renderer):
    ch = _chapter("John", 1, [(1, "In the beginning was the Word."),
                               (5, "The light shines in the darkness."),
                               (14, "And the Word became flesh.")])
    notes = ChapterNotes(book="John", chapter=1, source="EOB")
    notes.add_note(NoteType.FOOTNOTE, _note(1,  1, "Logos commentary."))
    notes.add_note(NoteType.FOOTNOTE, _note(5,  1, "Light vs darkness."))
    notes.add_note(NoteType.FOOTNOTE, _note(14, 1, "Incarnation note."))
    noted = _noted(notes)
    out = renderer.render_text_companion(ch, "EOB", noted_verses=noted)
    for vn in (1, 5, 14):
        assert f"EOB Notes#v{vn}|\u2020]]" in out   # †


def test_eob_variant_marker(renderer):
    ch = _chapter("John", 1, [(1, "Word."), (10, "He was in the world."), (18, "No one has seen God.")])
    notes = ChapterNotes(book="John", chapter=1, source="EOB")
    notes.add_note(NoteType.VARIANT, _note(1,  1, "Some MSS omit article."))
    notes.add_note(NoteType.VARIANT, _note(10, 1, "Var: 'knew'."))
    notes.add_note(NoteType.VARIANT, _note(18, 1, "Some MSS: 'only-begotten God'."))
    noted = _noted(notes)
    out = renderer.render_text_companion(ch, "EOB", noted_verses=noted)
    for vn in (1, 10, 18):
        assert f"EOB Notes#v{vn}|*]]" in out


def test_eob_alternative_marker(renderer):
    ch = _chapter("John", 1, [(1, "Word."), (3, "Through him."), (12, "Power.")])
    notes = ChapterNotes(book="John", chapter=1, source="EOB")
    notes.add_note(NoteType.ALTERNATIVE, _note(1,  1, "Or: 'a god'."))
    notes.add_note(NoteType.ALTERNATIVE, _note(3,  1, "Or: 'without him nothing was made'."))
    notes.add_note(NoteType.ALTERNATIVE, _note(12, 1, "Or: 'right'."))
    noted = _noted(notes)
    out = renderer.render_text_companion(ch, "EOB", noted_verses=noted)
    for vn in (1, 3, 12):
        assert f"EOB Notes#v{vn}|\u25ca]]" in out   # ◊


# Lexham: TRANSLATOR(‡), VARIANT(*), ALTERNATIVE(◊)

def test_lexham_translator_marker(renderer):
    ch = _chapter("Genesis", 1, [(1, "Created."), (6, "Expanse."), (20, "Living creatures.")])
    notes = ChapterNotes(book="Genesis", chapter=1, source="Lexham")
    notes.add_note(NoteType.TRANSLATOR, _note(1,  1, 'Or "sky".'))
    notes.add_note(NoteType.TRANSLATOR, _note(6,  1, 'Lit. "of the water and of the water".'))
    notes.add_note(NoteType.TRANSLATOR, _note(20, 1, 'Lit. "creeping things of living souls".'))
    noted = _noted(notes)
    out = renderer.render_text_companion(ch, "Lexham", noted_verses=noted)
    for vn in (1, 6, 20):
        assert f"Lexham Notes#v{vn}|\u2021]]" in out  # ‡


def test_lexham_variant_marker(renderer):
    ch = _chapter("Genesis", 1, [(1, "Created."), (2, "Formless."), (26, "Image.")])
    notes = ChapterNotes(book="Genesis", chapter=1, source="Lexham")
    notes.add_note(NoteType.VARIANT, _note(1,  1, "Some MSS add 'the'."))
    notes.add_note(NoteType.VARIANT, _note(2,  1, "LXX differs."))
    notes.add_note(NoteType.VARIANT, _note(26, 1, "Heb: 'our image'."))
    noted = _noted(notes)
    out = renderer.render_text_companion(ch, "Lexham", noted_verses=noted)
    for vn in (1, 2, 26):
        assert f"Lexham Notes#v{vn}|*]]" in out


def test_lexham_alternative_marker(renderer):
    ch = _chapter("Genesis", 1, [(3, "Light."), (9, "Dry land."), (14, "Lights.")])
    notes = ChapterNotes(book="Genesis", chapter=1, source="Lexham")
    notes.add_note(NoteType.ALTERNATIVE, _note(3,  1, "Or: 'Let light come to be'."))
    notes.add_note(NoteType.ALTERNATIVE, _note(9,  1, "Or: 'Let the waters under the sky'."))
    notes.add_note(NoteType.ALTERNATIVE, _note(14, 1, "Or: 'luminaries'."))
    noted = _noted(notes)
    out = renderer.render_text_companion(ch, "Lexham", noted_verses=noted)
    for vn in (3, 9, 14):
        assert f"Lexham Notes#v{vn}|\u25ca]]" in out  # ◊


# Alter: TRANSLATOR(‡) only

def test_alter_translator_markers_three_verses(renderer):
    ch = _chapter("Genesis", 1, [(2, "Welter."), (5, "Day."), (6, "Vault."),
                                  (24, "Wild beasts."), (26, "Human."), (27, "Male and female.")])
    notes = ChapterNotes(book="Genesis", chapter=1, source="Alter")
    notes.add_note(NoteType.TRANSLATOR, _note(2,  1, "tohu wabohu."))
    notes.add_note(NoteType.TRANSLATOR, _note(5,  1, "cardinal not ordinal."))
    notes.add_note(NoteType.TRANSLATOR, _note(6,  1, "rakiʿa."))
    noted = _noted(notes)
    out = renderer.render_text_companion(ch, "Alter", noted_verses=noted)
    for vn in (2, 5, 6):
        assert f"Alter Notes#v{vn}|\u2021]]" in out   # ‡
    # Unnoted verses must not have markers
    for vn in (24, 26, 27):
        assert f"Alter Notes#v{vn}" not in out


def test_alter_only_translator_no_other_symbols(renderer):
    """Alter only emits TRANSLATOR notes — no other symbols should appear."""
    ch = _chapter("Genesis", 1, [(1, "Creation."), (2, "Welter."), (3, "Light.")])
    notes = ChapterNotes(book="Genesis", chapter=1, source="Alter")
    notes.add_note(NoteType.TRANSLATOR, _note(2, 1, "A note."))
    noted = _noted(notes)
    out = renderer.render_text_companion(ch, "Alter", noted_verses=noted)
    # No † ◊ ※ ¶ ☩ marker links should appear (only ‡); * in "**Nav:**" is fine
    for sym in ("\u2020", "\u25ca", "\u203b", "\u00b6", "\u2629"):
        assert sym not in out, f"Unexpected symbol {sym!r} in Alter companion"
    # * must not appear as a marker link (but may appear in bold markdown)
    assert "Alter Notes#v2|*" not in out


# NETS: TRANSLATOR(‡) only (by design)

def test_nets_translator_markers_three_verses(renderer):
    ch = _chapter("Isaiah", 7, [(2, "Aram."), (8, "Damascus."), (14, "Virgin.")])
    notes = ChapterNotes(book="Isaiah", chapter=7, source="NETS")
    notes.add_note(NoteType.TRANSLATOR, _note(2,  7, "I.e. Achaz's."))
    notes.add_note(NoteType.TRANSLATOR, _note(8,  7, "Or 'the reign of Ephraim'."))
    notes.add_note(NoteType.TRANSLATOR, _note(14, 7, "Gk parthenos."))
    noted = _noted(notes)
    out = renderer.render_text_companion(ch, "NETS", noted_verses=noted)
    for vn in (2, 8, 14):
        assert f"NETS Notes#v{vn}|\u2021]]" in out  # ‡


# ── H. _INLINE_MARKER coverage: every NoteType is explicitly mapped ───────────

def test_inline_marker_covers_all_note_types():
    for nt in NoteType:
        assert nt in _INLINE_MARKER, f"NoteType.{nt.name} missing from _INLINE_MARKER"


# ── I. Service-layer noted_verse_markers flag ────────────────────────────────

def _make_service(source_label: str, noted_verse_markers: bool, notes: ChapterNotes, chapter: Chapter):
    """Build a minimal ExtractionService with fakes for testing the markers flag."""
    from tests.fakes import FakeScriptureSource, FakeVaultWriter

    book = Book(name=chapter.book)
    book.add_chapter(chapter)
    source = FakeScriptureSource(books=[book], notes=[notes])
    writer = FakeVaultWriter()
    renderer = ObsidianRenderer()
    return ExtractionService(
        source=source,
        renderer=renderer,
        writer=writer,
        mode=ExtractionMode.COMPANION,
        source_label=source_label,
        noted_verse_markers=noted_verse_markers,
    ), writer


@pytest.mark.parametrize("source_label", ["EOB", "Lexham", "DBH"])
def test_native_marker_sources_produce_no_combined_link(source_label):
    """EOB/Lexham/DBH set noted_verse_markers=False — no combined end-of-verse link."""
    ch = _chapter("John", 1, [(1, "In the beginning was the Word."), (2, "He was with God.")])
    notes = ChapterNotes(book="John", chapter=1, source=source_label)
    notes.add_note(NoteType.FOOTNOTE, _note(1, 1, "Commentary on the Logos."))
    notes.add_note(NoteType.TRANSLATOR, _note(1, 1, "Or: divine reason."))

    service, writer = _make_service(source_label, noted_verse_markers=False, notes=notes, chapter=ch)
    service.extract()

    companion = writer.written_companions[("John", 1, source_label)]
    # No combined end-of-verse wikilink to the notes file should appear
    assert f"{source_label} Notes#v1" not in companion


@pytest.mark.parametrize("source_label", ["EOB", "Lexham", "DBH"])
def test_native_marker_sources_still_show_notes_nav_link(source_label):
    """Even with noted_verse_markers=False, the nav link to Notes must appear."""
    ch = _chapter("John", 1, [(1, "In the beginning was the Word.")])
    notes = ChapterNotes(book="John", chapter=1, source=source_label)
    notes.add_note(NoteType.FOOTNOTE, _note(1, 1, "A note."))

    service, writer = _make_service(source_label, noted_verse_markers=False, notes=notes, chapter=ch)
    service.extract()

    companion = writer.written_companions[("John", 1, source_label)]
    assert f"{source_label} Notes" in companion


@pytest.mark.parametrize("source_label", ["Alter", "NETS"])
def test_no_native_marker_sources_produce_combined_link(source_label):
    """Alter/NETS set noted_verse_markers=True — combined link appears."""
    ch = _chapter("Genesis", 1, [(2, "Welter and waste."), (5, "First day.")])
    notes = ChapterNotes(book="Genesis", chapter=1, source=source_label)
    notes.add_note(NoteType.TRANSLATOR, _note(2, 1, "tohu wabohu."))

    service, writer = _make_service(source_label, noted_verse_markers=True, notes=notes, chapter=ch)
    service.extract()

    companion = writer.written_companions[("Genesis", 1, source_label)]
    assert f"{source_label} Notes#v2" in companion
