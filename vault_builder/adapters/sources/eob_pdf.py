"""
Adapter: EobPdfSource

Reads the Eastern/Greek Orthodox Bible (EOB) NT PDF and yields domain Book
objects containing per-verse text for all 27 NT books.

PDF structure:
  - NT text on pages 48–626 (1-indexed); appendices begin page 627
  - Book titles: "BOOKNAME  \\n(GREEK)" box at y≈676
  - Chapter headings come in three shapes:
      Pattern 1  standalone integer                  "3"
      Pattern 2  pericope + \\n + bare integer        "The Birth of Jesus\\n18"
                 (integer on its own last line)
      Pattern 3  pericope + \\n + int + \\n + text    "The visit of the magi\\n2\\nWhen…"
                 (integer on its own line, verse 1 text follows)
  - Mid-chapter pericope headings (not chapter starts): "Title Case\\n18Now the…"
    — heading line is skipped; verse text is extracted from the remainder
  - Verse text: verse numbers are inline digits immediately preceding a capital
    letter — "2Abraham", "18Now", "3Blessed" — verse 1 is always implicit
  - Footnote markers: [N] or [N][M] in separate small text boxes — stripped
  - Section intro headers between books: ALL-ASCII-uppercase text (no Greek) —
    resets chapter state to prevent bleed into previous book's last chapter

Known gap (full-run only):
  Intro prose pages between books (e.g. the Pauline intro before Romans) may
  emit a few words into the previous book's last chapter when running in
  full (non-sample) mode.  This is benign for sample-only Phase 1 acceptance
  testing and is documented for future full-run hardening.
"""

import logging
import re
from typing import Iterator, Optional

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextBox

from vault_builder.domain.models import Book, Chapter, Verse

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# EOB book title text → canonical vault book name
# --------------------------------------------------------------------------- #
_EOB_TITLE_TO_BOOK: dict[str, str] = {
    "MATTHEW":              "Matthew",
    "MARK":                 "Mark",
    "LUKE":                 "Luke",
    "JOHN":                 "John",
    "ACTS OF THE APOSTLES": "Acts",
    "ROMANS":               "Romans",
    "1 CORINTHIANS":        "I Corinthians",
    "2 CORINTHIANS":        "II Corinthians",
    "GALATIANS":            "Galatians",
    "EPHESIANS":            "Ephesians",
    "PHILIPPIANS":          "Philippians",
    "COLOSSIANS":           "Colossians",
    "1 THESSALONIANS":      "I Thessalonians",
    "2 THESSALONIANS":      "II Thessalonians",
    "1 TIMOTHY":            "I Timothy",
    "2 TIMOTHY":            "II Timothy",
    "TITUS":                "Titus",
    "PHILEMON":             "Philemon",
    "HEBREWS":              "Hebrews",
    "JAMES":                "James",
    "1 PETER":              "I Peter",
    "2 PETER":              "II Peter",
    "1 JOHN":               "I John",
    "2 JOHN":               "II John",
    "3 JOHN":               "III John",
    "JUDE":                 "Jude",
    "REVELATION":           "Revelation",
}

# NT content: pages 48–626 (1-indexed) → 47–625 (0-indexed)
_NT_FIRST_PAGE = 47      # inclusive, 0-indexed
_APPENDIX_FIRST_PAGE = 626  # exclusive, 0-indexed (page 627 in 1-indexed)

# Footnote markers: [N] or [N][M][K]…
_FOOTNOTE_RE = re.compile(r'^(\[\d+\])+$')

# Book title box: "BOOKNAME  \n(GREEK TEXT)"
_BOOK_TITLE_RE = re.compile(r'^(.+?)\s*\n\s*\([\u0370-\u03FF\w\s]+\)', re.DOTALL)

# Chapter heading patterns
_STANDALONE_INT_RE = re.compile(r'^\d+$')
_PERICOPE_CHAPTER_VERSE_RE = re.compile(r'^(.+)\n(\d+)\n(.+)', re.DOTALL)
_PERICOPE_CHAPTER_RE = re.compile(r'^(.+)\n(\d+)$', re.DOTALL)
_CHAPTER_INT_THEN_TEXT_RE = re.compile(r'^(\d+)\n(.+)', re.DOTALL)

# Mid-chapter pericope heading prefix: one or more Title-Case lines ending
# before a digit that starts verse text — "The Birth of Jesus\n18Now…"
_PERICOPE_PREFIX_RE = re.compile(
    r'^([A-Z][^0-9\n]+(?:\n[A-Z][^0-9\n]+)*)\n(?=\d)',
)

# Section intro header: entirely ASCII-uppercase (no Greek), length > 4
_SECTION_HEADER_RE = re.compile(r'^[A-Z0-9\s\-:,/()\[\].!?"\'—]+$')

# Inline verse number: digits immediately followed by any letter (upper or lower).
# EOB uses no space between verse number and text — "2Abraham", "3knowing", "18Now".
_INLINE_VERSE_RE = re.compile(r'(?<!\d)(\d+)(?=[A-Za-z])')


class EobPdfSource:
    """
    Reads the Eastern/Greek Orthodox Bible NT PDF and yields Book domain objects.

    In sample_only mode only chapters listed in sample_chapters are extracted.
    In full mode (sample_only=False) all 27 NT books are extracted.
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

    def read_text(self) -> Iterator[Book]:
        """Parse the PDF and yield one Book per NT book."""
        # book_name -> chapter_num -> verse_num -> text
        raw: dict[str, dict[int, dict[int, str]]] = {}
        self._parse_pdf(raw)

        for book_name, chapters in sorted(raw.items()):
            book = Book(name=book_name)
            for ch_num in sorted(chapters):
                chapter = Chapter(book=book_name, number=ch_num)
                for v_num in sorted(chapters[ch_num]):
                    text = chapters[ch_num][v_num].strip()
                    if text:
                        chapter.add_verse(v_num, text)
                if chapter.verses:
                    book.add_chapter(chapter)
            if book.chapters:
                yield book

    # ── PDF parser ────────────────────────────────────────────────────────────

    def _parse_pdf(self, raw: dict[str, dict[int, dict[int, str]]]) -> None:
        current_book: Optional[str] = None
        current_chapter: Optional[int] = None
        current_verse: Optional[int] = None

        for page_num, page in enumerate(extract_pages(self.pdf_path)):
            if page_num < _NT_FIRST_PAGE:
                continue
            if page_num >= _APPENDIX_FIRST_PAGE:
                break

            # Collect text boxes; sort top-to-bottom, left-to-right
            boxes = []
            for el in page:
                if isinstance(el, LTTextBox):
                    t = el.get_text().strip()
                    if t:
                        boxes.append((el.bbox, t))
            boxes.sort(key=lambda b: (-b[0][1], b[0][0]))

            for _, text in boxes:

                # 1. Footnote marker → skip
                if _FOOTNOTE_RE.match(text):
                    continue

                # 2. Book title
                book_name = self._detect_book_title(text)
                if book_name is not None:
                    current_book = book_name
                    current_chapter = None
                    current_verse = None
                    continue

                # 3. Section intro header (between-book intro pages)
                if self._is_section_header(text):
                    current_chapter = None
                    current_verse = None
                    continue

                # 4. Chapter heading
                ch_result = self._detect_chapter(text)
                if ch_result is not None:
                    chapter_num, verse1_text = ch_result
                    if current_book is None:
                        continue
                    current_chapter = chapter_num
                    current_verse = 1
                    if verse1_text and self._in_scope(current_book, current_chapter):
                        self._add_text(raw, current_book, current_chapter, 1, verse1_text)
                    continue

                # 5. Verse text
                if current_book is None or current_chapter is None:
                    continue
                if not self._in_scope(current_book, current_chapter):
                    continue

                for verse_num, fragment in self._parse_verse_text(text, current_verse):
                    if verse_num is not None:
                        current_verse = verse_num
                    if current_verse is not None and fragment:
                        self._add_text(raw, current_book, current_chapter, current_verse, fragment)

    def _in_scope(self, book: str, chapter: int) -> bool:
        if not self.sample_only:
            return True
        return (book, chapter) in self.sample_chapters

    # ── Classification helpers ────────────────────────────────────────────────

    @staticmethod
    def _detect_book_title(text: str) -> Optional[str]:
        """Return canonical book name if text is a book title box, else None."""
        if not _BOOK_TITLE_RE.match(text):
            return None
        first_line = text.split('\n')[0].strip()
        first_line = re.sub(r'\s+', ' ', first_line)
        # Strip "(ACCORDING TO) " prefix for Gospel titles
        first_line = re.sub(r'^\(ACCORDING TO\)\s+', '', first_line)
        return _EOB_TITLE_TO_BOOK.get(first_line)

    @staticmethod
    def _is_section_header(text: str) -> bool:
        """Detect ALL-ASCII-uppercase section intro headers between books."""
        stripped = text.strip()
        if len(stripped) <= 4:
            return False
        if _STANDALONE_INT_RE.match(stripped):
            return False  # standalone integer = chapter number
        return bool(_SECTION_HEADER_RE.match(stripped))

    @staticmethod
    def _detect_chapter(text: str) -> Optional[tuple[int, str]]:
        """
        Return (chapter_num, verse1_text) if text is a chapter heading, else None.
        verse1_text is the implicit verse 1 content when present in the same box.
        """
        stripped = text.strip()

        # Pattern 1: standalone integer
        if _STANDALONE_INT_RE.match(stripped):
            return int(stripped), ""

        # Pattern 3 first (more specific): pericope + bare int line + verse 1 text
        m = _PERICOPE_CHAPTER_VERSE_RE.match(stripped)
        if m:
            verse1 = re.sub(r'\[\d+\]', '', m.group(3))
            verse1 = ' '.join(verse1.split()).strip()
            return int(m.group(2)), verse1

        # Pattern 2: pericope ending with bare integer on last line
        m = _PERICOPE_CHAPTER_RE.match(stripped)
        if m:
            return int(m.group(2)), ""

        # Pattern 4: chapter integer on first line, verse 1 text on rest
        # e.g. "1\nJames, a bondservant of God…"
        m = _CHAPTER_INT_THEN_TEXT_RE.match(stripped)
        if m:
            verse1 = re.sub(r'\[\d+\]', '', m.group(2))
            verse1 = ' '.join(verse1.split()).strip()
            return int(m.group(1)), verse1

        return None

    # ── Verse text parser ─────────────────────────────────────────────────────

    @staticmethod
    def _parse_verse_text(text: str, current_verse: Optional[int]):
        """
        Yield (verse_num_or_None, fragment) tuples from a verse-bearing text box.

        verse_num_or_None = None  → continuation of current verse
        verse_num_or_None = N     → new verse N begins

        Steps:
          1. Strip footnote markers [N]
          2. Skip a leading pericope heading line if present
          3. Split on inline verse numbers (digit immediately before capital)
          4. Yield prefix as current-verse continuation, then each verse segment
        """
        # Strip footnote markers
        text = re.sub(r'\[\d+\]', '', text)

        # Skip leading pericope heading line(s):
        # "The Birth of Jesus\n18Now…" → skip "The Birth of Jesus\n"
        m = _PERICOPE_PREFIX_RE.match(text)
        if m:
            text = text[m.end():]

        # Normalize whitespace
        text = ' '.join(text.split()).strip()
        if not text:
            return

        matches = list(_INLINE_VERSE_RE.finditer(text))

        if not matches:
            yield None, text
            return

        # Text before first verse number → current verse continuation
        first_start = matches[0].start()
        if first_start > 0:
            prefix = text[:first_start].strip()
            if prefix:
                yield None, prefix

        for i, m in enumerate(matches):
            verse_num = int(m.group(1))
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            fragment = text[start:end].strip()
            if fragment:
                yield verse_num, fragment

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _add_text(raw: dict[str, dict[int, dict[int, str]]], book: str, chapter: int, verse: int, text: str) -> None:
        raw.setdefault(book, {}).setdefault(chapter, {})
        existing = raw[book][chapter].get(verse, "")
        raw[book][chapter][verse] = (existing + " " + text) if existing else text
