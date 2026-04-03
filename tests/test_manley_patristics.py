"""
TDD tests for ManleyArchiveSource.

Contracts:
  1. Local OCR text fixtures can be parsed without network access.
  2. read_fathers() groups excerpts into chapter companions for the sampled
     fixture chapters that back the shared sample envelope.
  3. Explicit biblical references in the commentary body / attribution line
     can refine the anchor verse for a companion entry.
  4. The source is patristic-only: read_text/read_notes/read_intros are empty.
  5. bootstrap("manley") auto-wires the PatristicSource into the existing
     Fathers pipeline and writes Fathers companions via the renderer/writer.
"""

from pathlib import Path

import pytest

from tests.fakes import FakeVaultWriter
from vault_builder.bootstrap import FATHERS_SAMPLE_CHAPTERS, bootstrap
from vault_builder.domain.models import PatristicType

from vault_builder.adapters.sources.manley_archive import ManleyArchiveSource


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "manley_ocr_sample.txt"


@pytest.fixture
def fixture_source() -> ManleyArchiveSource:
    return ManleyArchiveSource(str(FIXTURE_PATH), sample_only=False)


def test_fixture_file_exists():
    assert FIXTURE_PATH.exists()


def test_read_fathers_groups_expected_chapters(fixture_source):
    fathers = list(fixture_source.read_fathers())
    keys = {(item.book, item.chapter) for item in fathers}
    assert keys == {
        ("Matthew", 18),
        ("Luke", 9),
        ("Luke", 18),
        ("John", 14),
    }
    assert all(item.source == "Manley" for item in fathers)


def test_mathew_18_chrysostom_anchor_uses_explicit_reference(fixture_source):
    fathers = list(fixture_source.read_fathers())
    matthew_18 = next(item for item in fathers if (item.book, item.chapter) == ("Matthew", 18))
    excerpts = matthew_18.sorted_excerpts()
    assert excerpts[0][0] in {PatristicType.HOMILY, PatristicType.COMMENTARY}
    assert excerpts[0][1].father == "John Chrysostom"
    assert excerpts[0][1].verse_start == 4
    assert excerpts[0][1].verse_end == 5
    assert "He calls the little ones" in excerpts[0][1].content


def test_john_14_wrapped_attribution_is_preserved(fixture_source):
    fathers = list(fixture_source.read_fathers())
    john_14 = next(item for item in fathers if (item.book, item.chapter) == ("John", 14))
    excerpts = john_14.sorted_excerpts()
    anchors = [excerpt.verse_start for _, excerpt in excerpts]
    assert any(excerpt.father == "Archimandrite Justin Popovic" for _, excerpt in excerpts)
    assert any(excerpt.father == "Gregory of Nazianzus" for _, excerpt in excerpts)
    assert 10 in anchors
    assert 19 in anchors


def test_sample_only_filters_requested_chapters():
    source = ManleyArchiveSource(
        str(FIXTURE_PATH),
        sample_only=True,
        sample_chapters={("Matthew", 18), ("John", 14)},
    )
    fathers = list(source.read_fathers())
    keys = {(item.book, item.chapter) for item in fathers}
    assert keys == {("Matthew", 18), ("John", 14)}


def test_patristic_only_interfaces_are_empty(fixture_source):
    assert list(fixture_source.read_text()) == []
    assert list(fixture_source.read_notes()) == []
    assert list(fixture_source.read_intros()) == []


def test_bootstrap_manley_wires_fathers_pipeline(fixture_source):
    writer = FakeVaultWriter()
    service = bootstrap("manley", source=fixture_source, writer=writer)
    result = service.extract()

    assert result.fathers_written == 4
    assert result.hubs_written == 0
    assert result.notes_written == 0
    assert set(writer.written_fathers) == {
        ("Matthew", 18),
        ("Luke", 9),
        ("Luke", 18),
        ("John", 14),
    }


def test_shared_sample_envelope_includes_other_source_chapters():
    expected = {
        ("Genesis", 1),
        ("Genesis", 2),
        ("Exodus", 20),
        ("Leviticus", 1),
        ("Numbers", 6),
        ("Deuteronomy", 6),
        ("Joshua", 1),
        ("I Kingdoms", 1),
        ("Psalms", 1),
        ("Psalms", 50),
        ("Psalms", 151),
        ("Job", 3),
        ("Proverbs", 8),
        ("Song of Solomon", 1),
        ("Sirach", 1),
        ("Tobit", 1),
        ("Wisdom of Solomon", 1),
        ("I Maccabees", 1),
        ("Isaiah", 7),
        ("Isaiah", 53),
        ("Jeremiah", 1),
        ("Ezekiel", 1),
        ("Ezra", 1),
        ("Nehemiah", 1),
        ("Daniel", 3),
        ("Matthew", 1),
        ("Matthew", 5),
        ("Matthew", 18),
        ("John", 1),
        ("John", 14),
        ("Acts", 15),
        ("Romans", 8),
        ("I Corinthians", 13),
        ("Luke", 9),
        ("Luke", 18),
        ("James", 1),
        ("Revelation", 1),
    }
    assert expected <= FATHERS_SAMPLE_CHAPTERS
