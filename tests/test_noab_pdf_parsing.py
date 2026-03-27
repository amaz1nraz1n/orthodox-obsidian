"""
TDD tests: NoabPdfSource PDF parsing contracts.

Contracts guarded:
  Unit (no PDF required):
    1. _classify_box: verse/pericope/header/footnote/page_num/superscript
    2. _sort_reading_order: left column top-to-bottom, then right column top-to-bottom
    3. _parse_verse_stream: verse numbers parsed, verse 1 is pre-number text, text cleaned
    4. OCR junk does not create impossible verse jumps or silent chapter resets

  Integration (requires NOAB PDF):
    4. read_chapter returns Chapter with correct book/number
    5. Genesis 1:3 contains "light"
    6. Genesis 1:14 contains "firmament" or "lights"
    7. Genesis 1 has at least 20 verses
    8. Verse text does not begin with its verse number
    9. Verse text does not contain double-spaces after cleaning
"""

import os
import pytest

from vault_builder.adapters.sources.noab_pdf import NoabPdfSource, PageBox
from vault_builder.domain.models import Chapter

# ── PDF availability ──────────────────────────────────────────────────────────

_NOAB_PDF = os.path.join(
    os.path.dirname(__file__),
    "..",
    "source_files",
    "Full Bible",
    "New Oxford Annotated Bible with Apocrypha RSV.pdf",
)
_PDF_AVAILABLE = os.path.exists(_NOAB_PDF)
needs_pdf = pytest.mark.skipif(not _PDF_AVAILABLE, reason="NOAB PDF not present")


# ── Helpers ───────────────────────────────────────────────────────────────────


def box(x, y_top, y_bot, sz, text):
    return PageBox(x=x, y_top=y_top, y_bot=y_bot, sz=sz, text=text)


# ── Contract 1: _classify_box ─────────────────────────────────────────────────


def test_classify_verse_box():
    b = box(x=13, y_top=420, y_bot=238, sz=9.4, text="14  And  God  said")
    assert NoabPdfSource.classify_box(b, page_width=367) == "verse"


def test_classify_pericope_box():
    # Short, sz < 8.7, not at very top of page
    b = box(x=272, y_top=579, y_bot=571, sz=8.4, text="The  creation  of  man")
    assert NoabPdfSource.classify_box(b, page_width=367) == "pericope"


def test_classify_chapter_header_box():
    # Pattern "GENESIS 1", at very top of page, sz ~8.9
    b = box(x=12, y_top=585, y_bot=576, sz=8.9, text="GENESIS  1")
    assert NoabPdfSource.classify_box(b, page_width=367) == "header"


def test_classify_arabic_numeral_header_box():
    # NOAB uses "1 CORINTHIANS 13" not Roman "I CORINTHIANS 13"
    b = box(x=250, y_top=579, y_bot=571, sz=8.6, text="1  CORINTHIANS  13")
    assert NoabPdfSource.classify_box(b, page_width=367) == "header"


def test_classify_psalm_singular_header_box():
    # NOAB uses "PSALM 8" (singular) for lone-psalm pages
    b = box(x=12, y_top=582, y_bot=574, sz=8.8, text="PSALM  8")
    assert NoabPdfSource.classify_box(b, page_width=367) == "header"


def test_classify_footnote_box():
    b = box(x=15, y_top=41, y_bot=17, sz=7.6, text="9-10: The seas, a portion of the watery chaos")
    assert NoabPdfSource.classify_box(b, page_width=367) == "footnote"


def test_classify_page_num_box():
    b = box(x=180, y_top=33, y_bot=21, sz=11.1, text="[2]")
    assert NoabPdfSource.classify_box(b, page_width=367) == "page_num"


def test_classify_superscript_box():
    b = box(x=294, y_top=137, y_bot=130, sz=5.8, text="b  Or  wind")
    assert NoabPdfSource.classify_box(b, page_width=367) == "superscript"


def test_classify_numbered_body_line_at_font_threshold_as_verse():
    b = box(x=197.2, y_top=358.4, y_bot=348.0, sz=8.8, text="26 Then God said, “Let us make")
    assert NoabPdfSource.classify_box(b, page_width=367) == "verse"


# ── Contract 2: _sort_reading_order ───────────────────────────────────────────


def test_left_column_before_right():
    """Left column (x < pw/2) should come before right column at same y."""
    left = box(x=13, y_top=300, y_bot=200, sz=9.3, text="left")
    right = box(x=200, y_top=300, y_bot=200, sz=9.3, text="right")
    result = NoabPdfSource.sort_reading_order([right, left], page_width=367)
    assert result[0].text == "left"
    assert result[1].text == "right"


def test_within_column_top_to_bottom():
    """Within a column higher y_top (higher on page) comes first."""
    upper = box(x=13, y_top=500, y_bot=400, sz=9.3, text="upper")
    lower = box(x=13, y_top=300, y_bot=200, sz=9.3, text="lower")
    result = NoabPdfSource.sort_reading_order([lower, upper], page_width=367)
    assert result[0].text == "upper"
    assert result[1].text == "lower"


def test_right_column_top_to_bottom():
    """Right column boxes also sorted top-to-bottom."""
    upper_right = box(x=200, y_top=500, y_bot=400, sz=9.3, text="upper_right")
    lower_right = box(x=200, y_top=300, y_bot=200, sz=9.3, text="lower_right")
    lower_left = box(x=13, y_top=250, y_bot=100, sz=9.3, text="lower_left")
    result = NoabPdfSource.sort_reading_order(
        [lower_right, lower_left, upper_right], page_width=367
    )
    assert result[0].text == "lower_left"
    assert result[1].text == "upper_right"
    assert result[2].text == "lower_right"


# ── Contract 3: _parse_verse_stream ───────────────────────────────────────────


def test_verse_numbers_parsed():
    text = "In the beginning God created. 2 The earth was without form. 3 And God said."
    result = NoabPdfSource.parse_verse_stream(text)
    assert 1 in result
    assert 2 in result
    assert 3 in result


def test_verse_1_is_pre_number_text():
    text = "In the beginning God created the heavens. 2 The earth was without form."
    result = NoabPdfSource.parse_verse_stream(text)
    assert "beginning" in result[1]
    assert "heavens" in result[1]


def test_verse_2_text_correct():
    text = "In the beginning God created. 2 The earth was without form and void. 3 And God said."
    result = NoabPdfSource.parse_verse_stream(text)
    assert "without form" in result[2]


def test_verse_numbers_stripped_from_text():
    text = "In the beginning. 14 And God said let there be lights. 15 And it was so."
    result = NoabPdfSource.parse_verse_stream(text)
    assert not result[14].startswith("14")
    assert not result[15].startswith("15")


def test_double_spaces_normalized():
    text = "In  the  beginning  God  created. 2  The  earth  was  without  form."
    result = NoabPdfSource.parse_verse_stream(text)
    assert "  " not in result[1]
    assert "  " not in result[2]


def test_hyphenated_line_breaks_joined():
    """Hyphen at end of line followed by newline should be joined."""
    text = "In the begin-\nning God created the heavens. 2 The earth was void."
    result = NoabPdfSource.parse_verse_stream(text)
    assert "beginning" in result[1]
    assert "-" not in result[1] or "beginning" in result[1]


def test_arabic_numeral_book_header_classifies_as_header():
    """'1 CORINTHIANS 13' standalone box should be header, not verse/pericope."""
    b = box(x=20, y_top=578, y_bot=570, sz=8.6, text="1  CORINTHIANS  13")
    assert NoabPdfSource.classify_box(b, page_width=367) == "header"


def test_empty_pre_number_text_skipped():
    """If there is no text before verse 2, no verse 1 entry."""
    text = "2 The earth was without form. 3 And God said."
    result = NoabPdfSource.parse_verse_stream(text)
    assert 1 not in result
    assert 2 in result


def test_implausible_large_jump_not_promoted_to_new_verse():
    text = (
        "In the beginning God created the heavens and the earth. "
        "3 And God said, Let there be light. "
        "73 And there was evening and there was morning."
    )
    result = NoabPdfSource.parse_verse_stream(text)
    assert 73 not in result
    assert "73" in result[3]


def test_stateful_parser_stops_on_chapter_reset():
    text = "47 Mary saw where he was laid. 8 1 but Jesus went to the Mount of Olives."
    result, current_verse, hit_reset = NoabPdfSource._parse_verse_stream_stateful(
        text,
        starting_verse=47,
    )
    assert hit_reset is True
    assert current_verse == 47
    assert 47 in result


def test_stateful_parser_ignores_high_marker_on_nonopening_page():
    text = "11 And God said, Let the earth put forth vegetation."
    result, current_verse, hit_reset = NoabPdfSource._parse_verse_stream_stateful(
        text,
        starting_verse=None,
        allow_preamble_as_verse1=False,
    )
    assert result == {}
    assert current_verse is None
    assert hit_reset is False


def test_stateful_parser_stops_on_low_marker_after_high_verse():
    text = "30 And God said ... 4 These are the generations of the heavens and the earth."
    result, current_verse, hit_reset = NoabPdfSource._parse_verse_stream_stateful(
        text,
        starting_verse=18,
    )
    assert 30 in result
    assert hit_reset is True
    assert current_verse == 30


def test_stateful_parser_recovers_implicit_verse_1_before_low_marker():
    text = (
        "Thus the heavens and the earth were finished, and all the host of them. "
        "2 And on the seventh day God finished his work which he had done."
    )
    result, current_verse, hit_reset = NoabPdfSource._parse_verse_stream_stateful(
        text,
        starting_verse=None,
        allow_preamble_as_verse1=False,
    )
    assert hit_reset is False
    assert current_verse == 2
    assert "Thus the heavens and the earth were finished" in result[1]
    assert "seventh day" in result[2]


def test_parse_ordered_boxes_repairs_corrupted_leading_and_inline_markers():
    boxes = [
        box(x=22.6, y_top=218.1, y_bot=208.0, sz=8.9, text="364 And God said, “Let there be"),
        box(x=11.2, y_top=208.6, y_bot=198.0, sz=9.7, text="light”; and there was light. * And God"),
        box(x=11.8, y_top=198.2, y_bot=188.0, sz=9.5, text="saw that the light was good; and God"),
        box(x=11.4, y_top=188.1, y_bot=178.0, sz=9.5, text="separated the light from the darkness."),
    ]
    result, current_verse, hit_reset = NoabPdfSource._parse_ordered_boxes_stateful(
        boxes,
        starting_verse=2,
    )
    assert hit_reset is False
    assert current_verse == 4
    assert result[3].startswith("And God said")
    assert result[4].startswith("And God saw")


def test_parse_ordered_boxes_repairs_sequence_confusion_for_expected_next_verse():
    boxes = [
        box(x=21.8, y_top=136.7, y_bot=126.0, sz=8.9, text="6 And God said, “Let there be a"),
        box(x=187.8, y_top=259.0, y_bot=249.0, sz=9.3, text="waters.” * And God made the firma-"),
        box(x=187.8, y_top=249.2, y_bot=239.0, sz=9.5, text="ment and separated the waters which"),
        box(x=187.6, y_top=238.7, y_bot=228.0, sz=9.1, text="were under the firmament from the"),
        box(x=187.6, y_top=228.9, y_bot=218.0, sz=9.3, text="waters which were above the firma-"),
        box(x=187.8, y_top=218.8, y_bot=208.0, sz=9.3, text="ment. And it was so. 3 And God called"),
        box(x=187.8, y_top=208.5, y_bot=198.0, sz=9.1, text="the firmament Heaven. And there was"),
    ]
    result, current_verse, hit_reset = NoabPdfSource._parse_ordered_boxes_stateful(
        boxes,
        starting_verse=5,
    )
    assert hit_reset is False
    assert current_verse == 8
    assert result[6].startswith("And God said")
    assert result[7].startswith("And God made")
    assert result[8].startswith("And God called")


def test_fill_chapter_gaps_infers_multpage_chapter_1_from_book_start():
    src = NoabPdfSource.__new__(NoabPdfSource)
    src._chapter_pages = {
        ("Genesis", 2): [12, 13],
        ("Genesis", 3): [14, 15],
    }
    src._book_start_pages = {"Genesis": 10}
    src._fill_chapter_gaps()
    assert src._chapter_pages[("Genesis", 1)] == [10, 11]


def test_fill_chapter_gaps_shares_boundary_page_on_missing_internal_chapter():
    src = NoabPdfSource.__new__(NoabPdfSource)
    src._chapter_pages = {
        ("Genesis", 1): [48, 49],
        ("Genesis", 3): [50, 51],
    }
    src._book_start_pages = {"Genesis": 48}
    src._fill_chapter_gaps()
    assert src._chapter_pages[("Genesis", 1)] == [48, 49, 50]
    assert src._chapter_pages[("Genesis", 2)] == [50, 51]


def test_overflow_pages_borrows_one_shared_boundary_page():
    src = NoabPdfSource.__new__(NoabPdfSource)
    src._chapter_pages = {
        ("Genesis", 1): [48, 49],
        ("Genesis", 2): [49, 50],
    }
    assert src._overflow_pages("Genesis", 1, [48, 49]) == [50]


def test_find_chapter_start_idx_backs_up_to_preceding_opener_line():
    lines = [
        box(x=12, y_top=520, y_bot=510, sz=9.3, text="30 And to every beast of the earth,"),
        box(x=12, y_top=500, y_bot=490, sz=9.3, text="31 And God saw everything that he had made,"),
        box(x=31, y_top=160, y_bot=150, sz=9.5, text="Thus the heavens and the earth"),
        box(x=12, y_top=150, y_bot=140, sz=8.9, text="Z were finished, and all the host of them."),
        box(x=22, y_top=140, y_bot=130, sz=9.3, text="2 And on the seventh day God finished his work"),
    ]
    assert NoabPdfSource._find_chapter_start_idx(lines, chapter=2) == 2


def test_strip_decorative_opener_tokens_for_chapter_start():
    lines = [
        box(x=31, y_top=160, y_bot=150, sz=9.5, text="Thus the heavens and the earth"),
        box(x=12, y_top=150, y_bot=140, sz=8.9, text="Z were finished, and all the host of them."),
        box(x=22, y_top=140, y_bot=130, sz=9.3, text="2 And on the seventh day God finished his work"),
    ]
    cleaned = NoabPdfSource._clean_chapter_start_boxes(lines, chapter=2)
    assert cleaned[0].text == "Thus the heavens and the earth"
    assert cleaned[1].text == "were finished, and all the host of them."
    assert cleaned[2].text == "2 And on the seventh day God finished his work"


def test_find_implicit_verse_1_idx_from_following_explicit_verse_2():
    lines = [
        box(x=20.4, y_top=310.4, y_bot=300.0, sz=9.5, text="N THE BEGINNING WAS THE WorD,"),
        box(x=24.2, y_top=299.8, y_bot=289.0, sz=8.8, text="was and the Word was with God, and the"),
        box(x=13.6, y_top=289.8, y_bot=279.0, sz=9.1, text="Word was God. 2 He was in the begin-"),
    ]
    assert NoabPdfSource._find_implicit_verse_1_idx(lines) == 0


# ── Contract 4-9: Integration (real PDF) ─────────────────────────────────────


@pytest.fixture(scope="module")
def noab_source():
    if not _PDF_AVAILABLE:
        pytest.skip("NOAB PDF not present")
    return NoabPdfSource(_NOAB_PDF)


@needs_pdf
def test_read_chapter_type(noab_source):
    ch = noab_source.read_chapter("Genesis", 1)
    assert isinstance(ch, Chapter)


@needs_pdf
def test_read_chapter_book_number(noab_source):
    ch = noab_source.read_chapter("Genesis", 1)
    assert ch.book == "Genesis"
    assert ch.number == 1


@needs_pdf
def test_genesis_1_verse_3_light(noab_source):
    ch = noab_source.read_chapter("Genesis", 1)
    assert 3 in ch.verses
    assert "light" in ch.verses[3].text.lower()


@needs_pdf
def test_genesis_1_verse_14(noab_source):
    ch = noab_source.read_chapter("Genesis", 1)
    assert 14 in ch.verses
    v14 = ch.verses[14].text
    assert "light" in v14.lower() or "firmament" in v14.lower()


@needs_pdf
def test_genesis_1_at_least_10_verses(noab_source):
    # GlyphLessFont encoding in this PDF maps some verse-number glyphs to
    # non-digit Unicode characters (e.g. verse 10 → "1°", verse 22 → "7?"),
    # so not all 31 verse boundaries are detected.  We assert a meaningful
    # subset (>= 10) rather than the canonical total.
    ch = noab_source.read_chapter("Genesis", 1)
    assert len(ch.verses) >= 10


@needs_pdf
def test_genesis_1_no_implausible_large_jump(noab_source):
    ch = noab_source.read_chapter("Genesis", 1)
    assert 73 not in ch.verses
    assert max(ch.verses) < 40


@needs_pdf
def test_genesis_1_exact_verse_count(noab_source):
    ch = noab_source.read_chapter("Genesis", 1)
    assert len(ch.verses) == 31
    assert sorted(ch.verses) == list(range(1, 32))


@needs_pdf
def test_verse_text_does_not_start_with_number(noab_source):
    ch = noab_source.read_chapter("Genesis", 1)
    for v_num, verse in ch.verses.items():
        assert not verse.text.lstrip().startswith(
            str(v_num)
        ), f"Verse {v_num} text starts with its own number: {verse.text[:40]!r}"


@needs_pdf
def test_verse_text_no_double_spaces(noab_source):
    ch = noab_source.read_chapter("Genesis", 1)
    for v_num, verse in ch.verses.items():
        assert "  " not in verse.text, f"Verse {v_num} has double-spaces: {verse.text[:60]!r}"


@needs_pdf
def test_genesis_2_distinct_from_genesis_1(noab_source):
    ch2 = noab_source.read_chapter("Genesis", 2)
    assert ch2.number == 2
    assert len(ch2.verses) >= 10
    # Gen 2:7 "breath of life"
    if 7 in ch2.verses:
        assert "breath" in ch2.verses[7].text.lower() or "life" in ch2.verses[7].text.lower()


@needs_pdf
def test_genesis_2_recovers_opening_verse(noab_source):
    ch2 = noab_source.read_chapter("Genesis", 2)
    assert 1 in ch2.verses
    verse1 = ch2.verses[1].text.lower()
    assert "thus the heavens and the earth" in verse1
    assert "were finished" in verse1
