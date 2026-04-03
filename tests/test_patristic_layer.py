"""
PER-45: Unit tests for the Patristic layer.

Covers:
  1. Domain: PatristicExcerpt immutability, PatristicType routing,
     ChapterFathers.add_excerpt(), sorted_excerpts()
  2. Renderer: render_fathers() output shape — frontmatter, nav, section
     headings, [!cite] callouts with attribution, pericope range refs
  3. Writer: write_fathers() path convention
  4. Service: ExtractionService writes fathers when patristic_source set
  5. Nav: show_fathers=True adds Fathers slot; False omits it
  6. Regression: existing StudyNote / ChapterNotes tests unaffected
"""

from pathlib import Path

import pytest

from tests.fakes import FakePatristicSource, FakeScriptureSource, FakeVaultWriter
from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.domain.models import (
    ChapterFathers,
    ChapterNotes,
    NoteType,
    PatristicExcerpt,
    PatristicType,
    StudyNote,
)
from vault_builder.service_layer.extraction import ExtractionService

renderer = ObsidianRenderer()


# ── 1. Domain ─────────────────────────────────────────────────────────────────

def test_patristic_excerpt_is_frozen():
    exc = PatristicExcerpt(father="Ignatius", work="To the Ephesians", content="text", verse_start=1)
    with pytest.raises(Exception):
        exc.father = "other"  # type: ignore[misc]


def test_patristic_excerpt_optional_fields_default():
    exc = PatristicExcerpt(father="Clement", work="1 Clement", content="body", verse_start=3)
    assert exc.verse_end is None
    assert exc.section is None


def test_patristic_type_routing():
    assert PatristicType.HOMILY.value == "homily"
    assert PatristicType.COMMENTARY.value == "commentary"


def test_chapter_fathers_add_and_sorted():
    cf = ChapterFathers(book="John", chapter=1, source="Test")
    cf.add_excerpt(PatristicType.HOMILY, PatristicExcerpt(
        father="Chrysostom", work="Homilies on John", content="v14 text", verse_start=14
    ))
    cf.add_excerpt(PatristicType.COMMENTARY, PatristicExcerpt(
        father="Origen", work="Commentary on John", content="v1 text", verse_start=1
    ))
    result = cf.sorted_excerpts()
    assert result[0][1].verse_start == 1
    assert result[1][1].verse_start == 14


def test_chapter_fathers_sorted_by_verse_start():
    cf = ChapterFathers(book="Romans", chapter=8, source="Test")
    for v in [10, 1, 5]:
        cf.add_excerpt(PatristicType.EPISTLE, PatristicExcerpt(
            father="Paul", work="N/A", content="x", verse_start=v
        ))
    verse_starts = [e.verse_start for _, e in cf.sorted_excerpts()]
    assert verse_starts == [1, 5, 10]


# ── 2. Renderer ───────────────────────────────────────────────────────────────

def _make_fathers(book="John", chapter=1, source="Apostolic Fathers") -> ChapterFathers:
    cf = ChapterFathers(book=book, chapter=chapter, source=source)
    cf.add_excerpt(PatristicType.HOMILY, PatristicExcerpt(
        father="Ignatius of Antioch",
        work="To the Ephesians",
        section="§7",
        content="He is both flesh and spirit.",
        verse_start=14,
    ))
    cf.add_excerpt(PatristicType.COMMENTARY, PatristicExcerpt(
        father="Clement of Rome",
        work="1 Clement",
        content="In the beginning was the Word.",
        verse_start=1,
    ))
    return cf


def test_render_fathers_frontmatter():
    out = renderer.render_fathers(_make_fathers())
    assert 'hub: "[[John 1]]"' in out
    assert 'source: "Apostolic Fathers"' in out


def test_render_fathers_nav():
    out = renderer.render_fathers(_make_fathers())
    assert "[[John 1|Hub]]" in out
    assert "[[John 1 \u2014 Fathers|Fathers]]" not in out


def test_render_fathers_section_heading_links_to_hub():
    out = renderer.render_fathers(_make_fathers())
    assert "[[John 1#v1|Jn 1:1]]" in out
    assert "[[John 1#v14|Jn 1:14]]" in out


def test_render_fathers_block_id():
    out = renderer.render_fathers(_make_fathers())
    assert "^v1" in out
    assert "^v14" in out


def test_render_fathers_callout_attribution():
    out = renderer.render_fathers(_make_fathers())
    assert "> [!cite] Ignatius of Antioch — To the Ephesians, §7" in out
    assert "> [!cite] Clement of Rome — 1 Clement" in out


def test_render_fathers_callout_content():
    out = renderer.render_fathers(_make_fathers())
    assert "> He is both flesh and spirit." in out
    assert "> In the beginning was the Word." in out


def test_render_fathers_sorted_verse_order():
    out = renderer.render_fathers(_make_fathers())
    pos_v1 = out.index("Jn 1:1")
    pos_v14 = out.index("Jn 1:14")
    assert pos_v1 < pos_v14


def test_render_fathers_no_section_omits_comma():
    cf = ChapterFathers(book="John", chapter=1, source="Test")
    cf.add_excerpt(PatristicType.HOMILY, PatristicExcerpt(
        father="Polycarp", work="To the Philippians", content="body", verse_start=1
    ))
    out = renderer.render_fathers(cf)
    assert "> [!cite] Polycarp — To the Philippians\n" in out


# ── 3. Writer path convention ─────────────────────────────────────────────────

def test_fake_writer_write_fathers_stores_content():
    writer = FakeVaultWriter()
    writer.write_fathers("John", 1, "content")
    assert ("John", 1) in writer.written_fathers
    assert writer.written_fathers[("John", 1)] == "content"


# ── 4. ExtractionService wires fathers ───────────────────────────────────────

def test_extraction_service_writes_fathers_when_source_set():
    cf = _make_fathers()
    patristic = FakePatristicSource(fathers=[cf])
    writer = FakeVaultWriter()
    svc = ExtractionService(
        source=FakeScriptureSource(),
        renderer=renderer,
        writer=writer,
        patristic_source=patristic,
    )
    result = svc.extract()
    assert result.fathers_written == 1
    assert ("John", 1) in writer.written_fathers


def test_extraction_service_skips_fathers_when_no_source():
    writer = FakeVaultWriter()
    svc = ExtractionService(
        source=FakeScriptureSource(),
        renderer=renderer,
        writer=writer,
    )
    result = svc.extract()
    assert result.fathers_written == 0
    assert writer.written_fathers == {}


def test_extraction_result_summary_includes_fathers():
    cf = _make_fathers()
    patristic = FakePatristicSource(fathers=[cf])
    writer = FakeVaultWriter()
    svc = ExtractionService(
        source=FakeScriptureSource(),
        renderer=renderer,
        writer=writer,
        patristic_source=patristic,
    )
    result = svc.extract()
    assert "1 fathers" in result.summary()


def test_extraction_service_marks_hub_with_fathers_link_when_present():
    from vault_builder.domain.models import Book, Chapter

    book = Book(name="John")
    chapter = Chapter(book="John", number=1)
    chapter.add_verse(1, "In the beginning was the Word.")
    book.add_chapter(chapter)

    patristic = FakePatristicSource(fathers=[_make_fathers()])
    writer = FakeVaultWriter()
    svc = ExtractionService(
        source=FakeScriptureSource(books=[book]),
        renderer=renderer,
        writer=writer,
        patristic_source=patristic,
    )
    svc.extract()

    assert "[[John 1 \u2014 Fathers|Fathers]]" in writer.written_hubs[("John", 1)]


# ── 5. Nav slot ───────────────────────────────────────────────────────────────

def test_nav_callout_fathers_slot_when_has_fathers():
    from vault_builder.domain.models import Chapter
    ch = Chapter(book="John", number=1)
    hub = renderer.render_hub(ch, max_chapter=21, has_fathers=True)
    assert "Fathers" in hub
    assert "— Fathers|Fathers" in hub


def test_nav_callout_no_fathers_slot_by_default():
    from vault_builder.domain.models import Chapter
    ch = Chapter(book="John", number=1)
    hub = renderer.render_hub(ch, max_chapter=21)
    assert "— Fathers|Fathers" not in hub


# ── 6. Regression: ChapterNotes / StudyNote unaffected ───────────────────────

def test_chapter_notes_unaffected_by_patristic_additions():
    notes = ChapterNotes(book="John", chapter=1, source="OSB")
    notes.add_note(NoteType.FOOTNOTE, StudyNote(verse_number=1, ref_str="1:1", content="x"))
    assert len(notes.footnotes) == 1
    assert notes.sorted_notes(NoteType.FOOTNOTE)[0].verse_number == 1
