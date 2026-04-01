"""
PER-21/22: Unit tests for the parallel passages layer.

Covers:
  1. Adapter: ParallelPassageSource yields correct ChapterNotes with
     bidirectional NoteType.PARALLEL notes and wikilink content
  2. Adapter: single-passage groups (< 2 passages) are skipped
  3. Adapter: verse_end=None when single verse
  4. Writer: write_parallels stores content in FakeVaultWriter
  5. Service: ExtractionService writes parallels when parallel_source set
  6. Service: skips parallels when no source
  7. Service: parallels_written in summary()
  8. Regression: existing Patristic / ChapterNotes tests unaffected
"""

from pathlib import Path

import pytest
import yaml

from tests.fakes import FakeParallelSource, FakeScriptureSource, FakeVaultWriter
from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.sources.parallel_passages import (
    ParallelPassageSource,
    _ref_link,
)
from vault_builder.domain.models import ChapterNotes, NoteType
from vault_builder.service_layer.extraction import ExtractionService

renderer = ObsidianRenderer()

# ── Minimal YAML fixture ───────────────────────────────────────────────────────

_MINIMAL_YAML = """
parallels:
  - title: "Baptism of Jesus"
    passages:
      - {book: Matthew, chapter: 3, verse_start: 13, verse_end: 17}
      - {book: Mark,    chapter: 1, verse_start: 9,  verse_end: 11}
      - {book: Luke,    chapter: 3, verse_start: 21, verse_end: 22}
  - title: "Single passage — should be skipped"
    passages:
      - {book: John, chapter: 1, verse_start: 1, verse_end: 18}
  - title: "Single verse no range"
    passages:
      - {book: Matthew, chapter: 7, verse_start: 12}
      - {book: Luke,    chapter: 6, verse_start: 31}
"""


def _source_from_yaml(text: str) -> ParallelPassageSource:
    """Write minimal YAML to a tmp file and return a source pointing at it."""
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    tmp.write(text)
    tmp.close()
    return ParallelPassageSource(data_path=Path(tmp.name))


# ── 1. Adapter yields correct ChapterNotes ────────────────────────────────────

def test_adapter_yields_chapter_notes_for_each_book_chapter():
    src = _source_from_yaml(_MINIMAL_YAML)
    results = list(src.read_parallels())
    books_chapters = {(cn.book, cn.chapter) for cn in results}
    # Baptism: Matthew 3, Mark 1, Luke 3
    # Single verse: Matthew 7, Luke 6
    assert ("Matthew", 3) in books_chapters
    assert ("Mark", 1) in books_chapters
    assert ("Luke", 3) in books_chapters
    assert ("Matthew", 7) in books_chapters
    assert ("Luke", 6) in books_chapters


def test_adapter_source_is_parallels():
    src = _source_from_yaml(_MINIMAL_YAML)
    for cn in src.read_parallels():
        assert cn.source == "Parallels"


def test_adapter_notes_are_parallel_type():
    src = _source_from_yaml(_MINIMAL_YAML)
    for cn in src.read_parallels():
        for note in cn.sorted_notes(NoteType.PARALLEL):
            assert note is not None  # type must route correctly
    # Confirm PARALLEL notes exist
    results = list(src.read_parallels())
    all_notes = [n for cn in results for n in cn.sorted_notes(NoteType.PARALLEL)]
    assert len(all_notes) > 0


def test_adapter_bidirectional_matthew_has_mark_and_luke():
    src = _source_from_yaml(_MINIMAL_YAML)
    mt3 = next(cn for cn in src.read_parallels() if cn.book == "Matthew" and cn.chapter == 3)
    notes = mt3.sorted_notes(NoteType.PARALLEL)
    assert len(notes) == 1
    content = notes[0].content
    assert "Mark 1" in content
    assert "Luke 3" in content


def test_adapter_bidirectional_mark_has_matthew_and_luke():
    src = _source_from_yaml(_MINIMAL_YAML)
    mk1 = next(cn for cn in src.read_parallels() if cn.book == "Mark" and cn.chapter == 1)
    notes = mk1.sorted_notes(NoteType.PARALLEL)
    content = notes[0].content
    assert "Matthew 3" in content
    assert "Luke 3" in content


def test_adapter_note_verse_start_correct():
    src = _source_from_yaml(_MINIMAL_YAML)
    mt3 = next(cn for cn in src.read_parallels() if cn.book == "Matthew" and cn.chapter == 3)
    note = mt3.sorted_notes(NoteType.PARALLEL)[0]
    assert note.verse_number == 13


def test_adapter_note_verse_end_correct():
    src = _source_from_yaml(_MINIMAL_YAML)
    mt3 = next(cn for cn in src.read_parallels() if cn.book == "Matthew" and cn.chapter == 3)
    note = mt3.sorted_notes(NoteType.PARALLEL)[0]
    assert note.verse_end == 17


# ── 2. Single-passage groups skipped ─────────────────────────────────────────

def test_adapter_skips_single_passage_groups():
    src = _source_from_yaml(_MINIMAL_YAML)
    results = list(src.read_parallels())
    # John 1 is the only passage in its group — should produce no note
    john_chapters = [cn for cn in results if cn.book == "John"]
    assert john_chapters == []


# ── 3. Single-verse note (no verse_end) ──────────────────────────────────────

def test_adapter_single_verse_no_verse_end():
    src = _source_from_yaml(_MINIMAL_YAML)
    mt7 = next(cn for cn in src.read_parallels() if cn.book == "Matthew" and cn.chapter == 7)
    note = mt7.sorted_notes(NoteType.PARALLEL)[0]
    assert note.verse_end is None


# ── 4. ref_link helper ────────────────────────────────────────────────────────

def test_ref_link_with_range():
    link = _ref_link("Matthew", 3, 13, 17)
    assert "[[Matthew 3#v13|Matthew 3:13-17]]" == link


def test_ref_link_single_verse():
    link = _ref_link("Luke", 6, 31, None)
    assert "[[Luke 6#v31|Luke 6:31]]" == link


def test_ref_link_uses_file_prefix():
    # book_file_prefix("I Corinthians") returns "I Corinthians" (full name)
    link = _ref_link("I Corinthians", 13, 1, 13)
    assert "[[I Corinthians 13#v1|I Corinthians 13:1-13]]" == link


# ── 5. FakeVaultWriter.write_parallels ───────────────────────────────────────

def test_fake_writer_write_parallels_stores_content():
    writer = FakeVaultWriter()
    writer.write_parallels("Matthew", 3, "content")
    assert ("Matthew", 3) in writer.written_parallels
    assert writer.written_parallels[("Matthew", 3)] == "content"


# ── 6. ExtractionService wires parallels ─────────────────────────────────────

def _make_parallel_notes() -> ChapterNotes:
    src = _source_from_yaml(_MINIMAL_YAML)
    results = list(src.read_parallels())
    return next(cn for cn in results if cn.book == "Matthew" and cn.chapter == 3)


def test_extraction_service_writes_parallels_when_source_set():
    cn = _make_parallel_notes()
    parallel = FakeParallelSource(parallels=[cn])
    writer = FakeVaultWriter()
    svc = ExtractionService(
        source=FakeScriptureSource(),
        renderer=renderer,
        writer=writer,
        parallel_source=parallel,
    )
    result = svc.extract()
    assert result.parallels_written == 1
    assert ("Matthew", 3) in writer.written_parallels


def test_extraction_service_skips_parallels_when_no_source():
    writer = FakeVaultWriter()
    svc = ExtractionService(
        source=FakeScriptureSource(),
        renderer=renderer,
        writer=writer,
    )
    result = svc.extract()
    assert result.parallels_written == 0
    assert writer.written_parallels == {}


# ── 7. Summary includes parallels ────────────────────────────────────────────

def test_extraction_result_summary_includes_parallels():
    cn = _make_parallel_notes()
    parallel = FakeParallelSource(parallels=[cn])
    writer = FakeVaultWriter()
    svc = ExtractionService(
        source=FakeScriptureSource(),
        renderer=renderer,
        writer=writer,
        parallel_source=parallel,
    )
    result = svc.extract()
    assert "1 parallels" in result.summary()


# ── 8. Rendered output shape ──────────────────────────────────────────────────

def test_rendered_parallel_note_contains_callout():
    cn = _make_parallel_notes()
    out = renderer.render_notes(cn)
    assert "[!parallel]" in out


def test_rendered_parallel_note_links_to_mark():
    cn = _make_parallel_notes()
    out = renderer.render_notes(cn)
    assert "Mark 1" in out


def test_rendered_parallel_note_links_to_hub():
    cn = _make_parallel_notes()
    out = renderer.render_notes(cn)
    assert '[[Matthew 3]]' in out or 'hub:' in out


# ── 9. Real data file loads without error ─────────────────────────────────────

def test_real_data_file_loads():
    src = ParallelPassageSource()
    results = list(src.read_parallels())
    assert len(results) > 10  # we have 50+ groups → many chapters


def test_real_data_bidirectionality():
    """Every book/chapter that appears in the data should have at least one parallel note."""
    src = ParallelPassageSource()
    for cn in src.read_parallels():
        notes = cn.sorted_notes(NoteType.PARALLEL)
        assert len(notes) >= 1, f"{cn.book} {cn.chapter} has no parallel notes"
