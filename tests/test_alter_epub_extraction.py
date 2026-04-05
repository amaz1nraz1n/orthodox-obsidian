"""
Tests for AlterEpubSource — Robert Alter Hebrew Bible EPUB adapter.

Covers: verse parsing, multi-verse paragraphs, footnote extraction,
note type routing (all TRANSLATOR), divine name rendering (LORD),
and sample-scope filtering. Psalms are GATED and not tested here.
"""
import re
import pytest

EPUB_PATH = "./source_files/Old Testament /The Hebrew Bible -- Robert Alter.epub"

_SAMPLE: set[tuple[str, int]] = {
    ("Genesis",     1),
    ("Genesis",     2),
    ("Exodus",     20),
    ("Isaiah",      7),
    ("Isaiah",     53),
    ("Ruth",        1),
    ("Job",         3),
}


@pytest.fixture(scope="module")
def source():
    from vault_builder.adapters.sources.alter_epub import AlterEpubSource
    return AlterEpubSource(EPUB_PATH, sample_only=True, sample_chapters=_SAMPLE)


@pytest.fixture(scope="module")
def books(source):
    return {b.name: b for b in source.read_text()}


@pytest.fixture(scope="module")
def notes_list(source):
    return list(source.read_notes())


# ── Verse count ───────────────────────────────────────────────────────────────

def test_genesis_1_verse_count(books):
    """Genesis 1 has 31 verses."""
    ch = books["Genesis"].chapters[1]
    assert len(ch.verses) == 31


def test_genesis_2_verse_count(books):
    """Genesis 2 has 25 verses."""
    ch = books["Genesis"].chapters[2]
    assert len(ch.verses) == 25


def test_exodus_20_verse_count(books):
    """Exodus 20 has 26 verses."""
    ch = books["Exodus"].chapters[20]
    assert len(ch.verses) == 26


# ── Known verse text ──────────────────────────────────────────────────────────

def test_genesis_1_1(books):
    """Alter's Gen 1:1 opens with 'When God began to create'."""
    text = books["Genesis"].chapters[1].verses[1].text
    assert "When God began to create" in text


def test_genesis_1_3(books):
    """Gen 1:3 — 'God said, Let there be light.'"""
    text = books["Genesis"].chapters[1].verses[3].text
    assert "light" in text.lower()


def test_isaiah_7_14(books):
    """Alter's Isa 7:14 uses 'young woman', not 'virgin'."""
    text = books["Isaiah"].chapters[7].verses[14].text
    assert "young woman" in text


def test_no_verse_number_leak_in_text(books):
    """Verse text must not start with a digit (verse number leaking into body)."""
    for book in books.values():
        for ch in book.chapters.values():
            for v in ch.verses.values():
                assert not v.text.lstrip().startswith(str(v.number)), (
                    f"{book.name} {ch.number}:{v.number} text starts with its own number"
                )


# ── Divine name ───────────────────────────────────────────────────────────────

def test_divine_name_lord_rendered_plain(books):
    """L<small>ORD</small> must be extracted as plain LORD, not with HTML."""
    for book in books.values():
        for ch in book.chapters.values():
            for v in ch.verses.values():
                assert "<small>" not in v.text
                assert "</small>" not in v.text


# ── Multi-verse paragraph: no merge ──────────────────────────────────────────

def test_no_verse_merge(books):
    """No single verse block should contain two inline verse numbers.

    Catches the bug where multiple verses in one paragraph collapse into one.
    """
    digit_re = re.compile(r"\b(\d{1,3})\b")
    for book in books.values():
        for ch in book.chapters.values():
            for v in ch.verses.values():
                # A verse text that contains a lone digit equal to another
                # verse number in the same chapter is a merge signal
                nums = [int(m) for m in digit_re.findall(v.text)]
                other_verse_nums = set(ch.verses.keys()) - {v.number}
                leaked = [n for n in nums if n in other_verse_nums and n != v.number]
                # Only flag if the leaked number is not part of a longer token
                # (e.g. a year "586" is fine); we check for bare small integers
                small_leaked = [n for n in leaked if n < 200]
                assert not small_leaked, (
                    f"{book.name} {ch.number}:{v.number} text may contain "
                    f"leaked verse num(s) {small_leaked}: {v.text[:80]!r}"
                )


# ── Strip artifacts ───────────────────────────────────────────────────────────

def test_no_html_tags_in_verse_text(books):
    """Verse text must contain no raw HTML tags."""
    for book in books.values():
        for ch in book.chapters.values():
            for v in ch.verses.values():
                assert "<" not in v.text or "[[" in v.text, (
                    f"{book.name} {ch.number}:{v.number} contains HTML: {v.text[:80]!r}"
                )


def test_no_hide_span_text(books):
    """The hide-span indentation text must not appear in verse output."""
    for book in books.values():
        for ch in book.chapters.values():
            for v in ch.verses.values():
                assert "    " not in v.text  # 4-space hide-span artifact


# ── Notes ─────────────────────────────────────────────────────────────────────

def test_genesis_1_has_notes(notes_list):
    gen1 = [n for n in notes_list if n.book == "Genesis" and n.chapter == 1]
    assert gen1, "Genesis 1 should have at least one Alter translator note"


def test_notes_are_translator_type(notes_list):
    """All Alter notes route to NoteType.TRANSLATOR."""
    from vault_builder.domain.models import NoteType
    for cn in notes_list:
        for note in cn.translator_notes:
            assert note  # non-empty
        # No other slots should be populated
        assert not cn.footnotes
        assert not cn.variants
        assert not cn.alternatives
        assert not cn.cross_references


def test_notes_source_label(notes_list):
    for cn in notes_list:
        assert cn.source == "Alter"


def test_notes_have_content(notes_list):
    for cn in notes_list:
        for note in cn.translator_notes:
            assert note.content.strip(), f"Empty note body in {cn.book} {cn.chapter}"


# ── Book name canonicalization ─────────────────────────────────────────────────

def test_no_mt_book_names(books):
    """Adapter must canonicalize MT names to vault names."""
    assert "1 Samuel" not in books
    assert "2 Samuel" not in books
    assert "Song of Songs" not in books
    assert "Qohelet" not in books
