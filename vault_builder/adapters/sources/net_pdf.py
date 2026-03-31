"""
Adapter: NetPdfSource

Reads the NET Bible First Edition PDF and yields domain ChapterNotes objects
containing per-verse translator's notes (tn), text-critical notes (tc), study
notes (sn), and map notes (map) for requested chapters.

PDF structure:
  - Two-column layout; each column ~183pt wide (left x≈29, right x≈219)
  - Page headers at y > 620: "BookName Chapter:Verse" / content-page-number
  - Book title: text box matching a known book name, appears atop its first page
  - Section headings: Title-Case prose without inline verse references — skipped
  - Verse text: inline chapter:verse references — "1:3  All things were created…"
    Chapter and verse are always in the format "D:D  " (two spaces after the ref)
  - Note boxes: contain \xa0tn\xa0 / \xa0sn\xa0 / \xa0tc\xa0 / \xa0map\xa0 markers
    Multiple notes per box separated by chr(4) (\x04)
  - Font encoding: the digit "2" is encoded as chr(24) (\x18) throughout

Note families → ChapterNotes slot mapping:
  tn  (Translator's Note)   → translator_notes
  tc  (Text-critical Note)  → variants
  sn  (Study Note)          → footnotes
  map (Map Note)            → cross_references

Known Phase 1 limitation:
  Note content that spans more than one text box may be truncated; the first
  box always carries the substantive note text.  Continuations are silently
  dropped.  This is benign for sample-mode acceptance testing.
"""

import logging
import re
from typing import Iterator, Optional

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextBox

from vault_builder.domain.models import ChapterNotes, NoteType, StudyNote

logger = logging.getLogger(__name__)

_PDF_CODE_TO_NOTE_TYPE: dict[str, NoteType] = {
    "tn": NoteType.TRANSLATOR,
    "tc": NoteType.VARIANT,
    "sn": NoteType.FOOTNOTE,
    "map": NoteType.CROSS_REF,
}

# --------------------------------------------------------------------------- #
# NET Bible book title text → canonical vault book name
# --------------------------------------------------------------------------- #
_NET_TITLE_TO_BOOK: dict[str, str] = {
    # Old Testament (Protestant/NET naming → Orthodox vault naming)
    "Genesis":            "Genesis",
    "Exodus":             "Exodus",
    "Leviticus":          "Leviticus",
    "Numbers":            "Numbers",
    "Deuteronomy":        "Deuteronomy",
    "Joshua":             "Joshua",
    "Judges":             "Judges",
    "Ruth":               "Ruth",
    "1 Samuel":           "I Kingdoms",
    "2 Samuel":           "II Kingdoms",
    "1 Kings":            "III Kingdoms",
    "2 Kings":            "IV Kingdoms",
    "1 Chronicles":       "I Chronicles",
    "2 Chronicles":       "II Chronicles",
    "Ezra":               "Ezra",
    "Nehemiah":           "Nehemiah",
    "Esther":             "Esther",
    "Job":                "Job",
    "Psalms":             "Psalms",
    "Proverbs":           "Proverbs",
    "Ecclesiastes":       "Ecclesiastes",
    "Song of Songs":      "Song of Solomon",
    "The Song of Songs":  "Song of Solomon",
    "Isaiah":             "Isaiah",
    "Jeremiah":           "Jeremiah",
    "Lamentations":       "Lamentations",
    "Ezekiel":            "Ezekiel",
    "Daniel":             "Daniel",
    "Hosea":              "Hosea",
    "Joel":               "Joel",
    "Amos":               "Amos",
    "Obadiah":            "Obadiah",
    "Jonah":              "Jonah",
    "Micah":              "Micah",
    "Nahum":              "Nahum",
    "Habakkuk":           "Habakkuk",
    "Zephaniah":          "Zephaniah",
    "Haggai":             "Haggai",
    "Zechariah":          "Zechariah",
    "Malachi":            "Malachi",
    # New Testament (standard names)
    "Matthew":            "Matthew",
    "Mark":               "Mark",
    "Luke":               "Luke",
    "John":               "John",
    "Acts":               "Acts",
    "Romans":             "Romans",
    "1 Corinthians":      "I Corinthians",
    "2 Corinthians":      "II Corinthians",
    "Galatians":          "Galatians",
    "Ephesians":          "Ephesians",
    "Philippians":        "Philippians",
    "Colossians":         "Colossians",
    "1 Thessalonians":    "I Thessalonians",
    "2 Thessalonians":    "II Thessalonians",
    "1 Timothy":          "I Timothy",
    "2 Timothy":          "II Timothy",
    "Titus":              "Titus",
    "Philemon":           "Philemon",
    "Hebrews":            "Hebrews",
    "James":              "James",
    "1 Peter":            "I Peter",
    "2 Peter":            "II Peter",
    "1 John":             "I John",
    "2 John":             "II John",
    "3 John":             "III John",
    "Jude":               "Jude",
    "Revelation":         "Revelation",
}

# Page header y-threshold — boxes above this are running headers, skip them
_HEADER_Y = 620

# Two-column layout boundary: left col x < 215, right col x >= 215
_RIGHT_COL_X = 215

# Inline verse reference: chapter:verse followed by whitespace.
# Prose pages use double-space ("1:3  All things…"), poetry pages (Psalms) use
# single-space ("1:1 How blessed…").  Accept one or more spaces.
# Works after \x18 → 2 normalization.
_VERSE_REF_RE = re.compile(r'(\d{1,3}):(\d{1,3})\s+')

# Is-note-box: text contains a note-type marker surrounded by \xa0 or at start
_IS_NOTE_RE = re.compile(r'\x04\s*\xa0?(tn|tc|sn|map)\xa0|^(tn|tc|sn|map)\xa0')

# Split note box into individual note segments on \x04 separator
_NOTE_SEGMENT_SPLIT_RE = re.compile(r'\x04')

# Each segment starts with optional whitespace + type + \xa0 or space
_NOTE_SEGMENT_RE = re.compile(r'^\s*\xa0?(tn|tc|sn|map)[\xa0\s]+(.*)', re.DOTALL)


class NetPdfSource:
    """
    Reads the NET Bible First Edition PDF and yields ChapterNotes objects.

    In sample_only mode only chapters listed in sample_chapters are extracted.
    In full mode (sample_only=False) all books with title matches are extracted.
    """

    def __init__(
        self,
        pdf_path: str,
        sample_only: bool = True,
        sample_chapters: Optional[set[tuple[str, int]]] = None,
    ) -> None:
        self.pdf_path = pdf_path
        self.sample_only = sample_only
        self.sample_chapters = sample_chapters or set()

    def read_notes(self) -> Iterator[ChapterNotes]:
        """Parse the PDF and yield one ChapterNotes per (book, chapter)."""
        # raw: book -> chapter -> verse -> [(family, content)]
        raw: dict[str, dict[int, dict[int, list[tuple[str, str]]]]] = {}
        self._parse_pdf(raw)

        for book_name, chapters in sorted(raw.items()):
            for ch_num in sorted(chapters):
                chapter_raw = chapters[ch_num]
                notes_obj = ChapterNotes(book=book_name, chapter=ch_num, source="NET")
                for verse_num in sorted(chapter_raw):
                    if verse_num > 176:  # no Bible chapter exceeds 176 verses (Ps 119)
                        logger.debug("Dropping notes at verse %d (out of range)", verse_num)
                        continue
                    for family, content in chapter_raw[verse_num]:
                        ref = f"{ch_num}:{verse_num}"
                        note = StudyNote(
                            verse_number=verse_num,
                            ref_str=ref,
                            content=content,
                        )
                        if nt := _PDF_CODE_TO_NOTE_TYPE.get(family):
                            notes_obj.add_note(nt, note)
                if (notes_obj.translator_notes or notes_obj.variants
                        or notes_obj.footnotes or notes_obj.cross_references):
                    yield notes_obj

    # ── PDF parser ────────────────────────────────────────────────────────────

    def _parse_pdf(self, raw: dict[str, dict[int, dict[int, list[tuple[str, str]]]]]) -> None:
        """
        Parse the PDF with per-column verse tracking.

        The NET Bible uses a two-column layout.  Sorting all boxes by (-y, x)
        causes right-column verse text (which may reference later verses) to
        update the shared verse state before the note boxes for earlier
        left-column verses are reached.  To fix this, maintain separate
        chapter/verse cursors for the left column (x < _RIGHT_COL_X) and the
        right column (x >= _RIGHT_COL_X), and use the cursor matching the note
        box's own column.

        In sample_only mode, parsing stops as soon as all requested chapters
        have been finalized (a column cursor has advanced past each one).
        """
        current_book: Optional[str] = None
        # Per-column cursors: index 0 = left, index 1 = right
        col_chapter: list[Optional[int]] = [None, None]
        col_verse:   list[Optional[int]] = [None, None]
        # sample_only early-exit: track which requested chapters are done
        finalized: set[tuple[str, int]] = set()

        for _page_num, page in enumerate(extract_pages(self.pdf_path)):
            boxes = []
            for el in page:
                if isinstance(el, LTTextBox):
                    t = el.get_text().strip()
                    if t:
                        boxes.append((el.bbox, t))
            # Sort top-to-bottom, left-to-right
            boxes.sort(key=lambda b: (-b[0][1], b[0][0]))

            for bbox, raw_text in boxes:
                y = bbox[1]
                x = bbox[0]
                col = 0 if x < _RIGHT_COL_X else 1

                # Skip running page headers
                if y > _HEADER_Y:
                    continue

                text = self._normalize(raw_text)

                # Book title detection
                book = _NET_TITLE_TO_BOOK.get(text)
                if book is not None:
                    # Finalize any in-scope chapters still held in column cursors
                    if self.sample_only and current_book is not None:
                        for c in (col_chapter[0], col_chapter[1]):
                            if c is not None:
                                finalized.add((current_book, c))
                        if finalized >= self.sample_chapters:
                            return
                    current_book = book
                    col_chapter = [None, None]
                    col_verse   = [None, None]
                    continue

                if current_book is None:
                    continue

                # Note box — assign to the verse tracked in this box's column
                if _IS_NOTE_RE.search(raw_text):
                    ch = col_chapter[col]
                    v  = col_verse[col]
                    if ch is not None and v is not None:
                        if self._in_scope(current_book, ch):
                            for family, content in self._parse_note_segments(raw_text):
                                _add_note(raw, current_book, ch, v, family, content)
                    continue

                # Verse text box — update this column's chapter/verse cursor.
                # Use the first verse ref found anywhere in the text box (not just
                # at the start), with a monotonic-advance guard so back-references
                # like "cf. Ps 1:7" never corrupt a cursor that's already past
                # that verse.  This handles flowing prose (e.g. Genesis) where
                # text boxes start with continuation text then embed a verse number
                # mid-sentence ("surface of the water. 1:3 God said…").
                ch, v = self._extract_first_verse_ref(text)
                if ch is not None:
                    old_ch = col_chapter[col]
                    old_v  = col_verse[col]
                    forward = (
                        old_ch is None
                        or ch > old_ch
                        or (ch == old_ch and v >= (old_v or 0))
                    )
                    if forward:
                        # Track chapter advancement for sample_only early exit
                        if (self.sample_only and old_ch is not None
                                and old_ch != ch
                                and (current_book, old_ch) in self.sample_chapters):
                            finalized.add((current_book, old_ch))
                            if finalized >= self.sample_chapters:
                                return
                        col_chapter[col] = ch
                        col_verse[col]   = v
                        # In sample mode, once a column advances to an out-of-scope
                        # chapter, clear the cursor so downstream note boxes don't
                        # bleed into in-scope chapters via a stale cursor.
                        if self.sample_only and not self._in_scope(current_book, ch):
                            col_chapter[col] = None
                            col_verse[col]   = None

    def _in_scope(self, book: str, chapter: int) -> bool:
        if not self.sample_only:
            return True
        return (book, chapter) in self.sample_chapters

    # ── Classification helpers ────────────────────────────────────────────────

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize font-encoding artifacts: chr(24) → '2'."""
        return text.replace('\x18', '2')

    @staticmethod
    def _extract_first_verse_ref(text: str) -> tuple[Optional[int], Optional[int]]:
        """
        Return the first (chapter, verse) inline reference found anywhere in
        text, or (None, None) if none present.  Using the first (not last)
        ref prevents a text box that spans verses 3–5 from advancing the cursor
        all the way to verse 5, which would incorrectly attribute note boxes
        about verse 3 to verse 5.
        """
        m = _VERSE_REF_RE.search(text)
        if m:
            return int(m.group(1)), int(m.group(2))
        return None, None

    @staticmethod
    def _parse_note_segments(text: str) -> list[tuple[str, str]]:
        """
        Parse a note text box into (note_type, content) tuples.

        Note boxes may contain multiple notes separated by chr(4).  Each
        segment starts with an optional leading space / non-breaking-space,
        then the note type (tn/tc/sn/map), then a space/\xa0, then the content.

        Non-breaking spaces (\xa0) in content are converted to regular spaces.
        """
        results: list[tuple[str, str]] = []

        # Split on \x04 separator; each resulting segment may be one note
        segments = _NOTE_SEGMENT_SPLIT_RE.split(text)

        for seg in segments:
            seg_clean = seg.replace('\xa0', ' ').strip()
            m = _NOTE_SEGMENT_RE.match(seg_clean)
            if m:
                ntype = m.group(1)
                content = re.sub(r'\s+', ' ', m.group(2)).strip()
                if content:
                    results.append((ntype, content))

        # Also handle a box that starts with type\xa0 directly (no \x04 prefix)
        if not results:
            first_clean = text.replace('\xa0', ' ').strip()
            m = _NOTE_SEGMENT_RE.match(first_clean)
            if m:
                ntype = m.group(1)
                content = re.sub(r'\s+', ' ', m.group(2)).strip()
                if content:
                    results.append((ntype, content))

        return results


# ── Internal helpers ──────────────────────────────────────────────────────────

def _add_note(
    raw: dict[str, dict[int, dict[int, list[tuple[str, str]]]]],
    book: str,
    chapter: int,
    verse: int,
    family: str,
    content: str,
) -> None:
    raw.setdefault(book, {}).setdefault(chapter, {}).setdefault(verse, [])
    raw[book][chapter][verse].append((family, content))
