"""
Contract tests: OSB inline hub note marker generation (_footnote_marker_html).

Guards the symbol/CSS-class mapping for all note types and ensures the
correct note type is resolved from each known EPUB source file name.

Contracts:
  1. study*.html hrefs → footnote type → † / nt-fn
  2. crossReference.html → cross_reference type → § / nt-cross
  3. background.html → background_notes type → ◦ / nt-bg (not † — disambiguated)
  4. variant.html → variants → ‡ / nt-tc
  5. x-liturgical.html → liturgical → ☩ / nt-lit
  6. citation.html → citations → ¶ / nt-cit
  7. alternative.html → alternatives → ⁺ / nt-alt
  8. translation.html → translator_notes → * / nt-tn
  9. Unknown file → empty string (no marker)
 10. Fragment ID is preserved in the wikilink anchor
"""

import pytest

from vault_builder.adapters.sources.osb_epub import _footnote_marker_html


# ── Study endnotes (footnotes) ────────────────────────────────────────────────

def test_study_html_produces_footnote_marker():
    result = _footnote_marker_html("study3.html#f1234", "John", 1, 5)
    assert "†" in result
    assert 'class="nt-fn"' in result


def test_study_html_any_number_matches():
    for n in (1, 5, 11):
        result = _footnote_marker_html(f"study{n}.html#f999", "Genesis", 1, 1)
        assert "†" in result, f"study{n}.html should produce footnote marker"


# ── Cross references ──────────────────────────────────────────────────────────

def test_cross_reference_html_produces_section_marker():
    result = _footnote_marker_html("crossReference.html#cr42", "John", 1, 3)
    assert "§" in result, f"Expected § symbol, got: {result!r}"
    assert 'class="nt-cross"' in result


def test_cross_reference_wikilink_targets_osb_notes():
    result = _footnote_marker_html("crossReference.html#cr42", "John", 1, 3)
    assert "[[John 1 — OSB Notes#" in result


# ── Background notes ─────────────────────────────────────────────────────────

def test_background_html_produces_open_circle_marker():
    result = _footnote_marker_html("background.html#bg7", "Genesis", 1, 2)
    assert "◦" in result, f"Expected ◦ symbol (not †), got: {result!r}"
    assert 'class="nt-bg"' in result


def test_background_symbol_differs_from_footnote_symbol():
    fn_result = _footnote_marker_html("study1.html#f1", "John", 1, 1)
    bg_result = _footnote_marker_html("background.html#bg1", "John", 1, 1)
    fn_sym = fn_result.split("|")[1].split("]")[0] if "|" in fn_result else ""
    bg_sym = bg_result.split("|")[1].split("]")[0] if "|" in bg_result else ""
    assert fn_sym != bg_sym, "footnote and background_note must have distinct symbols"


# ── Other note types ──────────────────────────────────────────────────────────

def test_variant_html_produces_double_dagger():
    result = _footnote_marker_html("variant.html#v5", "Matthew", 5, 3)
    assert "‡" in result
    assert 'class="nt-tc"' in result


def test_liturgical_html_produces_cross_symbol():
    result = _footnote_marker_html("x-liturgical.html#lit9", "Psalms", 50, 1)
    assert "☩" in result
    assert 'class="nt-lit"' in result


def test_citation_html_produces_pilcrow():
    result = _footnote_marker_html("citation.html#c3", "John", 1, 14)
    assert "¶" in result
    assert 'class="nt-cit"' in result


def test_alternative_html_produces_plus():
    result = _footnote_marker_html("alternative.html#a2", "Romans", 8, 1)
    assert "⁺" in result
    assert 'class="nt-alt"' in result


def test_translation_html_produces_asterisk():
    result = _footnote_marker_html("translation.html#t11", "John", 1, 1)
    assert "*" in result
    assert 'class="nt-tn"' in result


# ── Unknown / missing ─────────────────────────────────────────────────────────

def test_unknown_file_returns_empty_string():
    assert _footnote_marker_html("unknown.html#x1", "John", 1, 1) == ""


def test_no_fragment_falls_back_to_verse_anchor():
    result = _footnote_marker_html("study1.html", "John", 1, 7)
    assert "#^v7" in result


# ── Fragment ID preserved in anchor ──────────────────────────────────────────

def test_fragment_id_used_as_block_anchor():
    result = _footnote_marker_html("study3.html#f4706", "John", 1, 1)
    assert "#^f4706" in result
