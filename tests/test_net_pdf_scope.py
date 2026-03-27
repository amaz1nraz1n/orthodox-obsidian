"""
Regression tests: NET PDF sample-mode scope contracts.

Contracts guarded:
  1. Psalms 1 sample extraction yields NO notes attributed to verse numbers
     beyond Psalm 1's actual verse count (6 verses in LXX).
     — THIS TEST IS EXPECTED TO FAIL until the adapter is fixed.
  2. In-scope chapters produce notes; out-of-scope chapters are absent.

Marked as integration: skipped when the PDF is not present.
"""
import os
import re

import pytest

from vault_builder.adapters.sources.net_pdf import NetPdfSource

PDF_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "source_files",
    "Full Bible",
    "The NET Bible, First Edition.pdf",
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def psalms1_notes():
    if not os.path.exists(PDF_PATH):
        pytest.skip("NET Bible PDF not present")
    source = NetPdfSource(
        pdf_path=PDF_PATH,
        sample_only=True,
        sample_chapters={("Psalms", 1)},
    )
    chapters = list(source.read_notes())
    matches = [c for c in chapters if c.book == "Psalms" and c.chapter == 1]
    assert matches, "Expected at least one ChapterNotes for Psalms 1"
    return matches[0]


@pytest.fixture(scope="module")
def john1_net_chapters():
    if not os.path.exists(PDF_PATH):
        pytest.skip("NET Bible PDF not present")
    source = NetPdfSource(
        pdf_path=PDF_PATH,
        sample_only=True,
        sample_chapters={("John", 1)},
    )
    return list(source.read_notes())


# ── Contract 1: no cross-chapter bleed (currently FAILS) ──────────────────────

def test_psalms1_net_notes_no_verse_beyond_chapter_max(psalms1_notes):
    """Psalm 1 has 6 verses (LXX). No note should be attributed to verse > 6."""
    PSALM_1_MAX_VERSE = 6
    all_notes = (
        psalms1_notes.footnotes
        + psalms1_notes.variants
        + psalms1_notes.citations
        + psalms1_notes.cross_references
    )
    out_of_range = [n for n in all_notes if n.verse_number > PSALM_1_MAX_VERSE]
    assert not out_of_range, (
        f"Sample-mode bleed: {len(out_of_range)} note(s) attributed to verses "
        f"beyond Psalm 1:{PSALM_1_MAX_VERSE} — "
        f"verse numbers found: {sorted({n.verse_number for n in out_of_range})}"
    )


# ── Contract 2: only the requested chapter is returned ───────────────────────

def test_net_sample_only_returns_requested_chapters(john1_net_chapters):
    for ch in john1_net_chapters:
        assert (ch.book, ch.chapter) == ("John", 1), (
            f"Out-of-scope chapter returned: {ch.book} {ch.chapter}"
        )


# ── Contract 3: in-scope chapter has notes ───────────────────────────────────

def test_net_sample_john1_has_footnotes(john1_net_chapters):
    john1 = next((c for c in john1_net_chapters if c.book == "John" and c.chapter == 1), None)
    assert john1 is not None
    assert john1.footnotes, "John 1 NET Notes must contain at least one translator's note"
