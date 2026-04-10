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

from vault_builder.adapters.sources.manley_archive import (
    ManleyArchiveSource,
    _clean_body_text,
    _is_plausible_author,
    _normalize_ocr_text,
)


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


def test_scofield_excerpts_are_filtered(fixture_source):
    fathers = list(fixture_source.read_fathers())
    all_authors = [
        excerpt.father
        for item in fathers
        for _, excerpt in item.sorted_excerpts()
    ]
    assert not any("scofield" in a.lower() for a in all_authors)
    assert not any(a in ("C", "Rev") for a in all_authors)


def test_liturgical_headers_stripped_from_body(fixture_source):
    fathers = list(fixture_source.read_fathers())
    matthew_18 = next(item for item in fathers if (item.book, item.chapter) == ("Matthew", 18))
    ambrose = next(
        excerpt
        for _, excerpt in matthew_18.sorted_excerpts()
        if excerpt.father == "Ambrose of Milan"
    )
    assert "19th WEEK" not in ambrose.content
    assert "APe" not in ambrose.content
    assert "PENTECOST" not in ambrose.content
    assert "The child is our model" in ambrose.content
    assert "little ones mentioned here" in ambrose.content


def test_strip_context_headers_unit():
    from vault_builder.adapters.sources.manley_archive import _strip_context_headers
    block = "The child is our model.\n19th WEEK AFTER PENTECOST (19 APe)\nThe little ones are meek."
    assert _strip_context_headers(block) == "The child is our model.\nThe little ones are meek."

    assert _strip_context_headers("CHEESE FARE WEEK (CFW)") == ""
    assert _strip_context_headers("FIRST WEEK OF GREAT LENT (1 OGL)") == ""
    assert _strip_context_headers("SECOND SUNDAY OF PASCHA (2 OPA)") == ""
    assert _strip_context_headers("APPENDIX I") == ""
    assert _strip_context_headers("Pure commentary text") == "Pure commentary text"


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


def test_clean_body_text_strips_pipe_artifacts():
    text = (
        "heritage that is priestly and filled with holiness, |\n"
        "while from the tribe of Juda - to which David and }\n"
        "Solomon and the rest of the kings belonged -\n"
        "there shines forth the splendor of a royal descent. |\n"
        "through its | own fault, into sin, it gives IQ} N i\n"
        "Whosoever wants to enter must of |@am"
    )
    result = _clean_body_text(text)
    assert "|" not in result
    assert "}" not in result
    assert "heritage that is priestly" in result
    assert "splendor of a royal descent." in result
    assert "through its own fault" in result

    noisy = "| Q&S \nIQ} N i \n|@am"
    assert _clean_body_text(noisy).strip() == ""

    leading = "| He said to him, 'Follow Me', and\n| you see that the most wise Paul"
    result2 = _clean_body_text(leading)
    assert result2.startswith("He said")
    assert "you see that" in result2
    assert not any(line.lstrip().startswith("|") for line in result2.splitlines())


def test_clean_body_text_joins_hyphenated_line_breaks():
    text = "the de-\nscent of the Spirit\ndrink- f ing\nim-\nmortality is given\nun-\nknown to the world"
    result = _clean_body_text(text)
    assert "descent" in result
    assert "drinking" in result
    assert "immortality" in result
    assert "unknown" in result
    assert "de-\n" not in result


def test_clean_body_text_normalizes_german_quotes():
    text = '\u201eHe who believes in Me\u201c said the Lord'
    result = _clean_body_text(text)
    assert "\u201e" not in result
    assert "\u201c" in result
    assert result.startswith("\u201cHe who believes")


def test_normalize_ocr_text_cleans_wrapped_work_titles():
    text = (
        "St. John Chrysostom. Homily XXII on I Corin- thians 9. "
        "St. John Chrysostom. Homily LXXV on Hea ABA! Matthew XXIV, 3. "
        "St. Cyril of Jerusalem. Lectures on the Sacraments. k} Myst. Cat.II, "
        "On the Rites of Baptism, 4, 5; Myst. Cat.IV, £| On the Eucharistic Food, 3, 6."
    )
    result = _normalize_ocr_text(text)
    assert "I Corinthians 9" in result
    assert "Homily LXXV on Matthew XXIV, 3" in result
    assert "Myst. Cat.II, On the Rites of Baptism, 4, 5;" in result
    assert "Myst. Cat.IV, On the Eucharistic Food, 3, 6" in result
    assert "Hea ABA!" not in result
    assert "k}" not in result
    assert "£|" not in result


def test_clean_body_text_normalizes_common_ocr_substitutions():
    text = (
        "Do you sce how the begotton child was DOVETING?\n"
        "St. Jobn Chrysostom said that Bp. Nikolai Velimirović was right."
    )
    result = _clean_body_text(text)
    assert "sce" not in result
    assert "begotton" not in result
    assert "DOVETING" not in result
    assert "Jobn" not in result
    assert "Velimirović" not in result
    assert "see" in result
    assert "begotten" in result
    assert "DOUBTING" in result
    assert "John Chrysostom" in result
    assert "Velimirovic" in result


def test_is_plausible_author_rejects_broken_citations():
    assert _is_plausible_author("John Chrysostom")
    assert _is_plausible_author("The Martyrdom of Saint Polycarp of Smyrna")
    assert not _is_plausible_author(
        'The Scriptures were fulfilled, the mission completed, at the very moment when He "breathed His last."'
    )
    assert not _is_plausible_author("The Martyrdom of St")
    assert not _is_plausible_author("tyr")
    assert not _is_plausible_author("A10")


def test_bibliography_marker_variant_is_parsed(tmp_path):
    source_path = tmp_path / "manley_b_marker.txt"
    source_path.write_text(
        "JOHN 1\n\n"
        "1 In the beginning was the Word.\n\n"
        "THE INCARNATE WORD\n\n"
        "The Word is God.\n\n"
        "St. John Chrysostom. Homily I on John 1, 1. B¥54, p. 367.\n",
        encoding="utf-8",
    )

    source = ManleyArchiveSource(str(source_path), sample_only=False)
    fathers = list(source.read_fathers())
    assert len(fathers) == 1

    excerpts = fathers[0].sorted_excerpts()
    assert len(excerpts) == 1
    assert excerpts[0][1].father == "John Chrysostom"
    assert excerpts[0][1].work == "Homily I on John 1"
    assert excerpts[0][1].verse_start == 1


def test_bibliography_section_is_skipped(tmp_path):
    source_path = tmp_path / "manley_bibliography.txt"
    source_path.write_text(
        "JOHN 5\n\n"
        "1 Then there was a feast of the Jews.\n\n"
        "THE HEALING OF THE PARALYTIC\n\n"
        "The Lord speaks to the sick man.\n"
        "St. John Chrysostom. Homily XXXVII on John 5, 1. B#1, p. 1.\n\n"
        "A1. Rev. John Matusiak, Orthodox Clip An, Light and Life Publishing\n"
        "A2. Another reference entry\n",
        encoding="utf-8",
    )

    source = ManleyArchiveSource(str(source_path), sample_only=False)
    fathers = list(source.read_fathers())
    assert len(fathers) == 1

    excerpts = fathers[0].sorted_excerpts()
    assert len(excerpts) == 1
    assert excerpts[0][1].father == "John Chrysostom"
