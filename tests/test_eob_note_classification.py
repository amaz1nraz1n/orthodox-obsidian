"""
Unit tests for _classify_eob_note — EOB endnote type classification.
"""
import pytest

from vault_builder.adapters.sources.eob_epub import _classify_eob_note
from vault_builder.domain.models import NoteType


# ── variants ──────────────────────────────────────────────────────────────────

def test_variants_ct_omits():
    assert _classify_eob_note('[750] CT omits "and you ask, who touched me?"') == NoteType.VARIANT

def test_variants_other_manuscripts_read():
    assert _classify_eob_note('[732] Other manuscripts read "them" instead of "him"') == NoteType.VARIANT

def test_variants_pt_adds():
    assert _classify_eob_note('[731] PT adds in smaller text, "their diseases"') == NoteType.VARIANT

def test_variants_nt_agrees():
    assert _classify_eob_note("[1023] NT agrees with LXX against MT.") == NoteType.VARIANT


# ── alternatives ──────────────────────────────────────────────────────────────

def test_alternatives_or():
    assert _classify_eob_note('[727] Or "vindicated"') == NoteType.ALTERNATIVE

def test_alternatives_literally():
    assert _classify_eob_note('[742] Literally "What do I have to do with you"') == NoteType.ALTERNATIVE

def test_alternatives_other_translations():
    assert _classify_eob_note('[755] Other translations "And he took them..."') == NoteType.ALTERNATIVE


# ── translator_notes ──────────────────────────────────────────────────────────

def test_translator_notes_greek_bare():
    assert _classify_eob_note('[729] Greek "he"') == NoteType.TRANSLATOR

def test_translator_notes_the_greek_word():
    assert _classify_eob_note(
        "[1003] The Greek word Logos (lo,goj) is traditionally..."
    ) == NoteType.TRANSLATOR


# ── cross_references ──────────────────────────────────────────────────────────

def test_cross_ref_see():
    assert _classify_eob_note("[728] See Wisdom of Sirach 4:11") == NoteType.CROSS_REF

def test_cross_ref_bare_book():
    assert _classify_eob_note("[733] Isaias (Isaiah) 6:9") == NoteType.CROSS_REF

def test_cross_ref_compare():
    assert _classify_eob_note("[1100] Compare Colossians 1:19") == NoteType.CROSS_REF


# ── citations ─────────────────────────────────────────────────────────────────

def test_citations_st_with_period():
    assert _classify_eob_note("[850] St. John Chrysostom says that the logos was...") == NoteType.CITATION

def test_citations_according_to_st():
    assert _classify_eob_note("[851] According to St. Basil, this passage...") == NoteType.CITATION

def test_citations_saint_full():
    assert _classify_eob_note("[852] Saint Athanasius interprets this as...") == NoteType.CITATION


# ── background_notes ──────────────────────────────────────────────────────────

def test_background_ancient_near_east():
    assert _classify_eob_note("[900] In the ancient Near East, the concept of...") == NoteType.BACKGROUND

def test_background_city_location():
    assert _classify_eob_note("[901] Caesarea Philippi was a city located at the...") == NoteType.BACKGROUND

def test_background_river_boundary():
    assert _classify_eob_note("[902] The Jordan River was the boundary between...") == NoteType.BACKGROUND


# ── footnotes (default) ───────────────────────────────────────────────────────

def test_footnotes_see_appendix_not_cross_ref():
    assert _classify_eob_note("[736] See Appendix E") == NoteType.FOOTNOTE

def test_footnotes_general_commentary():
    assert _classify_eob_note("[741] Some translations connect the clause...") == NoteType.FOOTNOTE

def test_footnotes_note_id_with_letter():
    assert _classify_eob_note("[1003b] The Word is not God in the sense...") == NoteType.FOOTNOTE
