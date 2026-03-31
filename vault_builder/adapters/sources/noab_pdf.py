"""
Adapter: NoabPdfSource

Reads the New Oxford Annotated Bible (NOAB) RSV PDF and yields Chapter objects
(verse text) per request.

PDF structure:
  - 2032 pages, two-column layout (~367x600 pt pages)
  - Column split at x ≈ page_width / 2
  - Running headers: "GENESIS 1", "JOHN 3" etc. at top of page (sz ~8.9, y > 560)
    appear when a chapter CONTINUES onto that page
  - Pericope headings: short boxes, sz < 8.7
  - Verse text: sz 9.0–9.7
  - Footnotes/annotations: sz < 8.0 at page bottom
  - Inline variant superscripts: sz < 6.0
  - Page numbers: sz > 10.0

Chapter-to-page mapping:
  Running header "GENESIS 2" on page P means Genesis 2 continues on page P.
  The chapter's FIRST page is identified as (first_header_page - 1), since
  the chapter starts mid-page on the page before its header first appears.

Verse parsing:
  Verse numbers appear inline as "N  text..." (bold in print, plain in extraction).
  Verse 1 = text before the first verse number in the chapter's text stream.
  Hyphenated line-breaks are rejoined.

See docs/noab-pdf-source-structure.md for full structural documentation.
"""

import re
from dataclasses import dataclass

import pdfplumber

try:
    import pytesseract

    _HAS_OCR = True
except ImportError:  # pragma: no cover
    _HAS_OCR = False

# Regex matching GlyphLessFont corruption artifacts:
# tokens containing weird glyphs from the non-Unicode mapping
_GLYPH_JUNK = re.compile(r".*[*°?®!\|©>@%^†].*")

from vault_builder.domain.models import Chapter, Verse

# ── Book name mapping: PDF header form → vault canonical name ─────────────────

_HEADER_TO_VAULT: dict[str, str] = {
    "GENESIS": "Genesis",
    "EXODUS": "Exodus",
    "LEVITICUS": "Leviticus",
    "NUMBERS": "Numbers",
    "DEUTERONOMY": "Deuteronomy",
    "JOSHUA": "Joshua",
    "JUDGES": "Judges",
    "RUTH": "Ruth",
    # NOAB uses Roman numerals in the mapping but Arabic digits in running headers
    "I SAMUEL": "I Kingdoms",
    "II SAMUEL": "II Kingdoms",
    "1 SAMUEL": "I Kingdoms",
    "2 SAMUEL": "II Kingdoms",
    "I KINGS": "III Kingdoms",
    "II KINGS": "IV Kingdoms",
    "1 KINGS": "III Kingdoms",
    "2 KINGS": "IV Kingdoms",
    "I CHRONICLES": "I Chronicles",
    "II CHRONICLES": "II Chronicles",
    "1 CHRONICLES": "I Chronicles",
    "2 CHRONICLES": "II Chronicles",
    "EZRA": "Ezra",
    "NEHEMIAH": "Nehemiah",
    "ESTHER": "Esther",
    "JOB": "Job",
    "PSALMS": "Psalms",
    "PSALM": "Psalms",
    "PROVERBS": "Proverbs",
    "ECCLESIASTES": "Ecclesiastes",
    "SONG OF SOLOMON": "Song of Solomon",
    "ISAIAH": "Isaiah",
    "JEREMIAH": "Jeremiah",
    "LAMENTATIONS": "Lamentations",
    "EZEKIEL": "Ezekiel",
    "DANIEL": "Daniel",
    "HOSEA": "Hosea",
    "JOEL": "Joel",
    "AMOS": "Amos",
    "OBADIAH": "Obadiah",
    "JONAH": "Jonah",
    "MICAH": "Micah",
    "NAHUM": "Nahum",
    "HABAKKUK": "Habakkuk",
    "ZEPHANIAH": "Zephaniah",
    "HAGGAI": "Haggai",
    "ZECHARIAH": "Zechariah",
    "MALACHI": "Malachi",
    # Deuterocanon
    "TOBIT": "Tobit",
    "JUDITH": "Judith",
    "I MACCABEES": "I Maccabees",
    "II MACCABEES": "II Maccabees",
    "1 MACCABEES": "I Maccabees",
    "2 MACCABEES": "II Maccabees",
    "III MACCABEES": "III Maccabees",
    "IV MACCABEES": "IV Maccabees",
    "3 MACCABEES": "III Maccabees",
    "4 MACCABEES": "IV Maccabees",
    "WISDOM OF SOLOMON": "Wisdom of Solomon",
    "SIRACH": "Sirach",
    "BARUCH": "Baruch",
    "I ESDRAS": "I Esdras",
    "1 ESDRAS": "I Esdras",
    "PSALM 151": "Psalm 151",
    # NT
    "MATTHEW": "Matthew",
    "MARK": "Mark",
    "LUKE": "Luke",
    "JOHN": "John",
    "ACTS": "Acts",
    "ROMANS": "Romans",
    "I CORINTHIANS": "I Corinthians",
    "II CORINTHIANS": "II Corinthians",
    "1 CORINTHIANS": "I Corinthians",
    "2 CORINTHIANS": "II Corinthians",
    "GALATIANS": "Galatians",
    "EPHESIANS": "Ephesians",
    "PHILIPPIANS": "Philippians",
    "COLOSSIANS": "Colossians",
    "I THESSALONIANS": "I Thessalonians",
    "II THESSALONIANS": "II Thessalonians",
    "1 THESSALONIANS": "I Thessalonians",
    "2 THESSALONIANS": "II Thessalonians",
    "I TIMOTHY": "I Timothy",
    "II TIMOTHY": "II Timothy",
    "1 TIMOTHY": "I Timothy",
    "2 TIMOTHY": "II Timothy",
    "TITUS": "Titus",
    "PHILEMON": "Philemon",
    "HEBREWS": "Hebrews",
    "JAMES": "James",
    "I PETER": "I Peter",
    "II PETER": "II Peter",
    "1 PETER": "I Peter",
    "2 PETER": "II Peter",
    "I JOHN": "I John",
    "II JOHN": "II John",
    "III JOHN": "III John",
    "1 JOHN": "I John",
    "2 JOHN": "II John",
    "3 JOHN": "III John",
    "JUDE": "Jude",
    "REVELATION": "Revelation",
}

# Inverse map for header lookup
_VAULT_TO_HEADER: dict[str, str] = {v: k for k, v in _HEADER_TO_VAULT.items()}

# Running header pattern: "GENESIS 1", "1 CORINTHIANS 13", "PSALMS 2, 3", etc.
_HEADER_PAT = re.compile(r"^([A-Z0-9][A-Z0-9\s]+?)\s+([\d]+(?:\s*,\s*[\d]+)*)$")
_HEADER_PREFIX_PAT = re.compile(r"^([A-Z0-9][A-Z0-9\s]+?)\s+([\d]+(?:\s*,\s*[\d]+)*)\s+")
# Detects "THE GOSPEL ACCORDING TO JOHN" or "THE FIRST BOOK OF MOSES"
_BOOK_TITLE_PAT = re.compile(r".*(?:GENESIS|EXODUS|MATTHEW|MARK|LUKE|JOHN|REVELATION|ISAIAH|CORINTHIANS).*")

# Verse number at start of text segment
_VERSE_NUM_PAT = re.compile(r"\b(\d{1,3})\s+")
_PAGE_NUM_PAT = re.compile(r"^\[\d+\]$")
_CHAPTER_RESET_PAT = re.compile(r"^\d{1,3}\s+1\b")
_DECORATIVE_BOOK_OPENER_PAT = re.compile(r"^\|x\b", re.IGNORECASE)
_SINGLE_LETTER_OPENER_PAT = re.compile(r"^[A-Z]\b")
_SINGLE_DIGIT_MARKER_CONFUSIONS: dict[int, set[int]] = {
    1: {1, 7},
    2: {2, 7},
    3: {3, 8},
    4: {4},
    5: {5},
    6: {6},
    7: {1, 7},
    8: {3, 8},
    9: {9},
}


@dataclass(frozen=True)
class PageBox:
    """A pdfminer text box with its position and average font size."""

    x: float
    y_top: float
    y_bot: float
    sz: float
    text: str


class NoabPdfSource:
    """
    Reads the NOAB RSV PDF and returns Chapter objects per request.

    Builds a chapter-to-pages index on first construction (slow, one full scan)
    and caches all page boxes so subsequent reads are fast.
    """

    def __init__(self, pdf_path: str) -> None:
        self._pdf_path = pdf_path
        self._chapter_pages: dict[tuple[str, int], list[int]] = {}
        self._page_widths: dict[int, float] = {}
        self._page_box_cache: dict[int, list[PageBox]] = {}
        self._book_start_pages: dict[str, int] = {}
        self._build_chapter_index()

    # ── Public interface ───────────────────────────────────────────────────────

    def read_chapter(self, book: str, chapter: int) -> Chapter:
        """Return a Chapter with verse text for the given book and chapter."""
        pages = self._chapter_pages.get((book, chapter), [])
        result = Chapter(book=book, number=chapter)
        current_verse: int | None = None

        for pg_idx in pages + self._overflow_pages(book, chapter, pages):
            pw = self._page_widths.get(pg_idx, 367.0)
            raw_boxes = self._extract_page_boxes(pg_idx)
            verse_boxes = self._select_body_boxes(raw_boxes, pw)
            ordered = self.sort_reading_order(verse_boxes, pw)
            boundary_chapter = chapter if current_verse is None else chapter + 1
            chapter_start_idx = self._find_chapter_start_idx(ordered, boundary_chapter)
            page_can_start = self._page_can_start_chapter(raw_boxes, book, boundary_chapter, pg_idx)
            if chapter_start_idx is None and current_verse is None and page_can_start:
                chapter_start_idx = self._find_implicit_verse_1_idx(ordered)
            hit_boundary = False
            if current_verse is None and chapter_start_idx is None and not page_can_start:
                continue
            if chapter_start_idx is not None:
                if current_verse is None:
                    ordered = ordered[chapter_start_idx:]
                else:
                    ordered = ordered[:chapter_start_idx]
                    hit_boundary = True
            if not ordered:
                if hit_boundary:
                    break
                continue

            allow_preamble_as_verse1 = current_verse is None and (
                chapter_start_idx is not None or self._page_has_chapter_opener(raw_boxes)
            )
            if allow_preamble_as_verse1:
                ordered = self._clean_chapter_start_boxes(ordered, chapter)

            verse_texts, current_verse, hit_reset = self._parse_ordered_boxes_stateful(
                ordered,
                starting_verse=current_verse,
                allow_preamble_as_verse1=allow_preamble_as_verse1,
            )
            for v_num, text in verse_texts.items():
                if v_num in result.verses:
                    merged = f"{result.verses[v_num].text} {text}".strip()
                    result.verses[v_num] = Verse(number=v_num, text=re.sub(r"\s+", " ", merged))
                else:
                    result.verses[v_num] = Verse(number=v_num, text=text)
            if hit_reset or hit_boundary:
                break

        return result

    def _overflow_pages(self, book: str, chapter: int, pages: list[int]) -> list[int]:
        """
        Borrow one extra page from the next chapter when the current chapter is
        clearly under-scoped and the next chapter already overlaps a boundary page.
        This is a pragmatic recovery path for NOAB shared-page chapter starts.
        """
        if not pages:
            return []
        next_pages = self._chapter_pages.get((book, chapter + 1), [])
        if not next_pages:
            return []
        if not (set(pages) & set(next_pages)):
            return []
        extra = [pg for pg in next_pages if pg not in pages]
        return extra[:1]

    # ── Static parsing helpers (unit-testable) ────────────────────────────────

    @classmethod
    def classify_box(cls, pb: PageBox, page_width: float) -> str:
        """Classify a PageBox using font size and spatial heuristics."""
        text = re.sub(r"\s+", " ", pb.text.strip())

        # Large decorative initials at chapter starts should stay with the text layer.
        if pb.sz >= 15.0:
            return "verse"

        if _PAGE_NUM_PAT.match(text):
            return "page_num"

        # Running headers and pericope titles both live at the top band.
        if pb.y_top > 560:
            m_header = _HEADER_PAT.match(text) or _HEADER_PREFIX_PAT.match(text)
            if m_header and _HEADER_TO_VAULT.get(m_header.group(1).strip()):
                return "header"
            if pb.sz < 8.8 and len(text) < 70:
                return "pericope"
            if pb.sz >= 10.0:
                return "page_num"
            return "header"

        # Tiny parenthesized letter markers / apparatus sigla.
        if pb.sz < 6.2:
            if re.match(r"^\(?[A-Za-z0-9]+\)?(?:\s|$)", text):
                return "superscript"
            if pb.y_top < 230:
                return "footnote"
            return "pericope"

        # Large centered/footer material near the page edge is furniture.
        if pb.sz >= 10.0 and pb.y_top < 40:
            return "page_num"

        # Bottom-of-page note blocks.
        if pb.sz < 8.0 and pb.y_top < 230:
            return "footnote"

        # Explicit numbered verse lines on shared pages can sit right on the
        # pericope/font threshold; keep them in the text layer.
        if cls._looks_like_explicit_verse_box(pb):
            return "verse"

        # Small prose elsewhere is usually pericope or intro prose, not verse text.
        if pb.sz < 8.8:
            if pb.y_top < 230:
                return "footnote"
            return "pericope"

        # Default fallback: anything >= 8.8 is likely verse text
        return "verse"

    @staticmethod
    def sort_reading_order(boxes: list[PageBox], page_width: float) -> list[PageBox]:
        """
        Sort boxes in reading order: left column (x < page_width/2) top-to-bottom,
        then right column top-to-bottom.
        """
        col_split = page_width / 2
        left = [b for b in boxes if b.x < col_split]
        right = [b for b in boxes if b.x >= col_split]
        left.sort(key=lambda b: -b.y_top)
        right.sort(key=lambda b: -b.y_top)
        return left + right

    @staticmethod
    def parse_verse_stream(text: str) -> dict[int, str]:
        """
        Parse a concatenated text stream into {verse_num: clean_text}.

        Verse 1 = text before the first verse number marker.
        Verse N = text between marker N and marker N+1.
        Double-spaces normalized; hyphenated line-breaks rejoined.
        """
        result, _current_verse, _hit_reset = NoabPdfSource._parse_verse_stream_stateful(
            text,
            starting_verse=None,
        )
        return result

    @staticmethod
    def _clean_box_text(text: str) -> str:
        text = re.sub(r"\[\d+\]", " ", text)
        text = re.sub(r"-\s*\n\s*", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _page_note_cutoff(boxes: list[PageBox]) -> float:
        note_band = [b.y_top for b in boxes if b.sz < 8.2 and b.y_top < 250]
        return max(note_band, default=0.0)

    @staticmethod
    def _looks_like_body_text(pb: PageBox, note_cutoff: float) -> bool:
        if note_cutoff and pb.y_top <= note_cutoff + 2.0 and pb.sz < 9.8:
            return False
        return True

    @classmethod
    def _select_body_boxes(cls, raw_boxes: list[PageBox], page_width: float) -> list[PageBox]:
        note_cutoff = cls._page_note_cutoff(raw_boxes)
        result: list[PageBox] = []
        for pb in raw_boxes:
            if cls.classify_box(pb, page_width) != "verse":
                continue
            if not cls._looks_like_body_text(pb, note_cutoff):
                continue
            clean = cls._clean_box_text(pb.text)
            if not clean:
                continue
            result.append(PageBox(x=pb.x, y_top=pb.y_top, y_bot=pb.y_bot, sz=pb.sz, text=clean))
        return result

    @staticmethod
    def _split_leading_marker(token: str) -> tuple[int | None, str]:
        token = token.strip()
        if not token or _PAGE_NUM_PAT.match(token):
            return None, token

        m = re.match(r"^(\d{1,3})(.*)$", token)
        if not m:
            return None, token

        number = int(m.group(1))
        rest = m.group(2).lstrip(".,;:)]}\"'`")
        return number, rest

    @staticmethod
    def _leading_token(text: str) -> str:
        parts = text.strip().split(maxsplit=1)
        return parts[0] if parts else ""

    @classmethod
    def _looks_like_explicit_verse_box(cls, pb: PageBox) -> bool:
        token = cls._leading_token(pb.text)
        if not token:
            return False
        candidate, _rest = cls._split_leading_marker(token)
        if candidate is not None and 1 <= candidate <= 176:
            return True
        if token.isdigit() and len(token) <= 3:
            return True
        if len(token) <= 4 and (_GLYPH_JUNK.match(token) or token == "Z"):
            return True
        return False

    @classmethod
    def _is_chapter_opener_box(cls, pb: PageBox, chapter: int) -> bool:
        token = cls._leading_token(pb.text)
        if not token or pb.x > 40:
            return False
        if chapter == 1 and _DECORATIVE_BOOK_OPENER_PAT.match(pb.text):
            return True
        if chapter > 1 and token == str(chapter):
            return True
        if chapter > 1 and token == "Z":
            return True
        return False

    @classmethod
    def _find_chapter_start_idx(cls, boxes: list[PageBox], chapter: int) -> int | None:
        for idx, pb in enumerate(boxes):
            if not cls._is_chapter_opener_box(pb, chapter):
                continue
            if idx > 0:
                prev = boxes[idx - 1]
                if (
                    prev.x < 60
                    and not cls._split_leading_marker(cls._leading_token(prev.text))[0]
                    and not prev.text.rstrip().endswith((".", "!", "?", ":", ";"))
                ):
                    return idx - 1
            return idx
        return None

    @classmethod
    def _box_has_explicit_marker(cls, pb: PageBox, marker: int) -> bool:
        for token in cls._clean_box_text(pb.text).split():
            candidate, _rest = cls._split_leading_marker(token)
            if candidate == marker:
                return True
        return False

    @classmethod
    def _find_implicit_verse_1_idx(cls, boxes: list[PageBox]) -> int | None:
        for idx, pb in enumerate(boxes):
            text = cls._clean_box_text(pb.text)
            if not text or pb.x > 60:
                continue
            token = cls._leading_token(text)
            if cls._split_leading_marker(token)[0] is not None:
                continue
            lookahead = boxes[idx : idx + 4]
            if any(cls._box_has_explicit_marker(next_box, 2) for next_box in lookahead):
                return idx
        return None

    @classmethod
    def _clean_chapter_start_boxes(cls, boxes: list[PageBox], chapter: int) -> list[PageBox]:
        cleaned: list[PageBox] = []
        for idx, pb in enumerate(boxes):
            text = pb.text.strip()
            if idx == 0 and chapter == 1:
                text = _DECORATIVE_BOOK_OPENER_PAT.sub("", text, count=1).strip()
            if idx == 0 and chapter > 1:
                text = re.sub(rf"^{chapter}\s+", "", text).strip()
            if (
                idx > 0
                and cleaned
                and pb.x < 20
                and cleaned[-1].text
                and not cleaned[-1].text.rstrip().endswith((".", "!", "?", ":", ";"))
                and cls._leading_token(text) == "Z"
            ):
                text = re.sub(r"^Z\s+", "", text).strip()
            cleaned.append(PageBox(x=pb.x, y_top=pb.y_top, y_bot=pb.y_bot, sz=pb.sz, text=text))
        return [pb for pb in cleaned if pb.text]

    def _page_can_start_chapter(
        self,
        raw_boxes: list[PageBox],
        book: str,
        chapter: int,
        pg_idx: int,
    ) -> bool:
        if chapter == 1 and self._book_start_pages.get(book) == pg_idx:
            return True

        header_name = _VAULT_TO_HEADER.get(book)
        if not header_name:
            return False

        for pb in raw_boxes:
            if pb.y_top <= 560:
                continue
            norm = re.sub(r"\s+", " ", pb.text.strip())
            m_header = _HEADER_PAT.match(norm) or _HEADER_PREFIX_PAT.match(norm)
            if not m_header:
                continue
            if m_header.group(1).strip() != header_name:
                continue
            chapters = [int(n.strip()) for n in m_header.group(2).split(",")]
            if chapter in chapters:
                return True
        return False

    @staticmethod
    def _is_plausible_marker(candidate: int, current_verse: int | None) -> bool:
        if candidate < 1 or candidate > 176:
            return False
        if current_verse is None:
            return True
        if candidate == 1 and current_verse >= 5:
            return True
        if candidate <= current_verse:
            return False
        if candidate > current_verse + 25:
            return False
        return True

    @staticmethod
    def _token_ends_sentence(token: str) -> bool:
        return token.rstrip(')"\']}\u201d\u2019').endswith((".", "!", "?", ":", ";"))

    @classmethod
    def _repair_boundary_marker(
        cls,
        token: str,
        current_verse: int | None,
        next_token: str,
    ) -> int | None:
        expected = current_verse + 1 if current_verse is not None else None
        if expected is None:
            return None

        next_token = next_token.strip()
        next_starts_prose = bool(next_token) and (
            next_token[0].isalpha() or next_token[0] in {'"', "“", "'", "‘"}
        )
        if not next_starts_prose:
            return None

        digits = re.sub(r"\D", "", token)
        if digits:
            for start in range(len(digits)):
                for end in range(start + 1, min(len(digits), start + 3) + 1):
                    if int(digits[start:end]) == expected:
                        return expected
            if len(digits) == 1:
                digit = int(digits)
                if str(expected).startswith(digits):
                    return expected
                if expected <= 9 and expected in _SINGLE_DIGIT_MARKER_CONFUSIONS.get(digit, set()):
                    return expected
            if len(token) <= 4:
                return expected

        if len(token) <= 4 and (_GLYPH_JUNK.match(token) or token == "Z"):
            return expected
        return None

    @classmethod
    def _marker_from_token(
        cls,
        token: str,
        current_verse: int | None,
        at_boundary: bool,
        next_token: str,
    ) -> tuple[int | None, str]:
        candidate, rest = cls._split_leading_marker(token)
        if candidate is not None and cls._is_plausible_marker(candidate, current_verse):
            return candidate, rest
        if at_boundary:
            repaired = cls._repair_boundary_marker(token, current_verse, next_token)
            if repaired is not None:
                return repaired, ""
        return None, token

    @classmethod
    def _parse_verse_stream_stateful(
        cls,
        text: str,
        starting_verse: int | None,
        allow_preamble_as_verse1: bool = True,
    ) -> tuple[dict[int, str], int | None, bool]:
        """
        Parse a text stream into verse chunks while preserving verse continuity
        across pages and rejecting implausible verse jumps from OCR noise.
        """
        text = cls._clean_box_text(text)
        tokens = text.split()
        result: dict[int, str] = {}
        current_verse = starting_verse
        current_tokens: list[str] = []
        hit_reset = False
        ignored_high_markers = False

        def flush_buffer() -> None:
            nonlocal current_tokens
            if not current_tokens:
                return
            verse_num = current_verse if current_verse is not None else 1
            if current_verse is None and not allow_preamble_as_verse1:
                current_tokens = []
                return
            joined = re.sub(r"\s+", " ", " ".join(current_tokens)).strip()
            if joined:
                existing = result.get(verse_num, "")
                result[verse_num] = f"{existing} {joined}".strip() if existing else joined
            current_tokens = []

        def flush_implicit_verse_1(trim_to_last_sentence: bool = False) -> None:
            nonlocal current_tokens
            if not current_tokens:
                return
            joined = re.sub(r"\s+", " ", " ".join(current_tokens)).strip()
            if trim_to_last_sentence:
                sentences = re.split(r"(?<=[.!?])\s+", joined)
                if len(sentences) > 1:
                    joined = sentences[-1].strip()
            if joined:
                existing = result.get(1, "")
                result[1] = f"{existing} {joined}".strip() if existing else joined
            current_tokens = []

        for token in tokens:
            if _PAGE_NUM_PAT.match(token):
                continue

            if current_verse is not None and _CHAPTER_RESET_PAT.match(token):
                flush_buffer()
                hit_reset = True
                break

            candidate, rest = cls._split_leading_marker(token)
            if (
                candidate is not None
                and current_verse is None
                and not allow_preamble_as_verse1
                and candidate > 5
            ):
                ignored_high_markers = True
                current_tokens = []
                continue
            if (
                candidate is not None
                and current_verse is not None
                and current_verse >= 20
                and candidate <= 5
            ):
                flush_buffer()
                hit_reset = True
                break
            if candidate is not None and cls._is_plausible_marker(candidate, current_verse):
                if current_verse is not None and candidate == 1 and current_verse >= 5:
                    flush_buffer()
                    hit_reset = True
                    break
                if current_verse is None and not allow_preamble_as_verse1 and 2 <= candidate <= 5:
                    flush_implicit_verse_1(trim_to_last_sentence=ignored_high_markers)
                    ignored_high_markers = False
                flush_buffer()
                current_verse = candidate
                if rest:
                    current_tokens.append(rest)
                continue

            current_tokens.append(token)

        flush_buffer()
        return result, current_verse, hit_reset

    @classmethod
    def _parse_ordered_boxes_stateful(
        cls,
        boxes: list[PageBox],
        starting_verse: int | None,
        allow_preamble_as_verse1: bool = True,
    ) -> tuple[dict[int, str], int | None, bool]:
        """
        Parse already ordered body lines while keeping line boundaries intact.

        This is stricter than flattening a whole page into one string: it lets the
        parser repair malformed boundary markers using local sequence context
        without losing column/line structure on shared pages.
        """
        result: dict[int, str] = {}
        current_verse = starting_verse
        current_tokens: list[str] = []
        hit_reset = False
        ignored_high_markers = False

        def flush_buffer() -> None:
            nonlocal current_tokens
            if not current_tokens:
                return
            verse_num = current_verse if current_verse is not None else 1
            if current_verse is None and not allow_preamble_as_verse1:
                current_tokens = []
                return
            joined = re.sub(r"\s+", " ", " ".join(current_tokens)).strip()
            if joined:
                existing = result.get(verse_num, "")
                result[verse_num] = f"{existing} {joined}".strip() if existing else joined
            current_tokens = []

        def flush_implicit_verse_1(trim_to_last_sentence: bool = False) -> None:
            nonlocal current_tokens
            if not current_tokens:
                return
            joined = re.sub(r"\s+", " ", " ".join(current_tokens)).strip()
            if trim_to_last_sentence:
                sentences = re.split(r"(?<=[.!?])\s+", joined)
                if len(sentences) > 1:
                    joined = sentences[-1].strip()
            if joined:
                existing = result.get(1, "")
                result[1] = f"{existing} {joined}".strip() if existing else joined
            current_tokens = []

        for pb in boxes:
            text = cls._clean_box_text(pb.text)
            if not text:
                continue
            tokens = text.split()
            prev_ended_sentence = True
            for idx, token in enumerate(tokens):
                if _PAGE_NUM_PAT.match(token):
                    continue

                at_boundary = idx == 0 or prev_ended_sentence
                next_token = tokens[idx + 1] if idx + 1 < len(tokens) else ""
                marker, rest = cls._marker_from_token(token, current_verse, at_boundary, next_token)

                if (
                    marker is not None
                    and current_verse is None
                    and not allow_preamble_as_verse1
                    and marker > 5
                ):
                    ignored_high_markers = True
                    current_tokens = []
                    prev_ended_sentence = False
                    continue
                if marker is not None and current_verse is not None and marker == 1 and current_verse >= 5:
                    flush_buffer()
                    hit_reset = True
                    break
                if (
                    marker is not None
                    and current_verse is None
                    and not allow_preamble_as_verse1
                    and 2 <= marker <= 5
                ):
                    flush_implicit_verse_1(trim_to_last_sentence=ignored_high_markers)
                    ignored_high_markers = False
                if marker is not None:
                    flush_buffer()
                    current_verse = marker
                    if rest:
                        current_tokens.append(rest)
                    prev_ended_sentence = False
                    continue

                current_tokens.append(token)
                prev_ended_sentence = cls._token_ends_sentence(token)

            if hit_reset:
                break

        flush_buffer()
        return result, current_verse, hit_reset

    @staticmethod
    def _page_has_chapter_opener(boxes: list[PageBox]) -> bool:
        return any(b.sz >= 15.0 for b in boxes)

    # ── OCR glyph-recovery ─────────────────────────────────────────────────────

    @staticmethod
    def _group_words_by_line(words: list[dict], page_width: float) -> list[list[dict]]:
        if not words:
            return []
        col_split = page_width / 2
        ordered = sorted(words, key=lambda w: (w["x0"] >= col_split, round(w["top"]), w["x0"]))
        lines: list[list[dict]] = []
        current_line: list[dict] = []
        for w in ordered:
            if not current_line:
                current_line.append(w)
                continue
            last = current_line[-1]
            is_same_col = (w["x0"] < col_split) == (last["x0"] < col_split)
            if abs(w["top"] - last["top"]) < 3.0 and (w["x0"] - last["x1"]) < 50.0 and is_same_col:
                current_line.append(w)
                continue
            lines.append(current_line)
            current_line = [w]
        if current_line:
            lines.append(current_line)
        return lines

    @staticmethod
    def _is_marker_candidate_word(word: dict, line_words: list[dict], idx: int) -> bool:
        text = str(word["text"]).strip()
        if not text or len(text) > 4:
            return False
        size = float(word["size"])
        if size < 8.5 or size > 10.2:
            return False
        if _PAGE_NUM_PAT.match(text) or text.endswith(":") or text.endswith(")") or text.startswith("("):
            return False

        has_glyph_junk = bool(_GLYPH_JUNK.match(text))
        if has_glyph_junk:
            return True

        if not text.isdigit() or len(text) > 3:
            return False

        prev_text = str(line_words[idx - 1]["text"]).strip() if idx > 0 else ""
        next_text = str(line_words[idx + 1]["text"]).strip() if idx + 1 < len(line_words) else ""
        at_line_start = idx == 0
        prev_ends_sentence = prev_text.endswith((".", ";", ":", "?", "!", '"', "”", "'"))
        next_starts_prose = bool(next_text) and (next_text[0].isupper() or next_text[0] in {'"', "“", "'"})
        return next_starts_prose and (at_line_start or prev_ends_sentence)

    @staticmethod
    def _ocr_digits_from_crop(page: object, bbox: tuple[float, float, float, float], psm: int) -> str | None:
        img = page.crop(bbox).to_image(resolution=600).original
        text = pytesseract.image_to_string(
            img,
            config=f"--psm {psm} -c tessedit_char_whitelist=0123456789",
        ).strip()
        m = re.search(r"\d{1,3}", text)
        return m.group(0) if m else None

    @classmethod
    def _recover_marker_word(cls, page: object, word: dict, line_words: list[dict], idx: int) -> str | None:
        original_text = str(word["text"]).strip()
        x0 = float(word["x0"])
        top = float(word["top"])
        x1 = float(word["x1"])
        bottom = float(word["bottom"])

        token_bbox = (
            max(0.0, x0 - 2.0),
            max(0.0, top - 2.0),
            min(float(page.width), x1 + 2.0),
            min(float(page.height), bottom + 2.0),
        )
        token_digits = cls._ocr_digits_from_crop(page, token_bbox, psm=10)

        next_x = float(line_words[idx + 1]["x0"]) if idx + 1 < len(line_words) else x1 + 50.0
        context_bbox = (
            max(0.0, x0),
            max(0.0, top - 3.0),
            min(float(page.width), max(x1 + 50.0, next_x + 40.0)),
            min(float(page.height), bottom + 3.0),
        )
        context_digits = cls._ocr_digits_from_crop(page, context_bbox, psm=6)

        if _GLYPH_JUNK.match(original_text):
            return token_digits or context_digits
        if original_text.isdigit():
            if context_digits:
                if len(original_text) == 1:
                    return context_digits
                if len(context_digits) == len(original_text):
                    return context_digits
            return token_digits
        return token_digits or context_digits

    @classmethod
    def _ocr_fix_words(cls, words: list[dict], page: object) -> list[dict]:
        """Recover likely verse-marker words via targeted OCR crops.

        Full-page OCR is too noisy for NOAB. The durable win is much narrower:
        OCR only short, verse-sized marker candidates and use a wider line-prefix
        crop only when the isolated token remains ambiguous.
        """
        if not _HAS_OCR:
            return words

        fixed = [{**w} for w in words]
        for line_words in cls._group_words_by_line(fixed, float(page.width)):
            for idx, word in enumerate(line_words):
                if not cls._is_marker_candidate_word(word, line_words, idx):
                    continue
                replacement = cls._recover_marker_word(page, word, line_words, idx)
                if replacement:
                    word["text"] = replacement
        return fixed

    # ── PDF index building ─────────────────────────────────────────────────────

    def _words_to_boxes(self, words: list[dict], page_height: float, page_width: float) -> list[PageBox]:
        """Group pdfplumber words into PageBox lines based on vertical position and column."""
        if not words:
            return []

        col_split = page_width / 2
        # Sort by column first, then top, then x0 to group effectively
        words.sort(key=lambda w: (w["x0"] >= col_split, round(w["top"]), w["x0"]))

        boxes = []
        current_line = []
        for w in words:
            if not current_line:
                current_line.append(w)
                continue

            last = current_line[-1]
            is_same_col = (w["x0"] < col_split) == (last["x0"] < col_split)
            # Same line if top is within 3 pts, horizontal gap < 30 pts, and same column
            if abs(w["top"] - last["top"]) < 3.0 and (w["x0"] - last["x1"]) < 50.0 and is_same_col:
                current_line.append(w)
            else:
                self._append_line_to_boxes(boxes, current_line, page_height)
                current_line = [w]

        if current_line:
            self._append_line_to_boxes(boxes, current_line, page_height)

        return boxes

    @staticmethod
    def _append_line_to_boxes(boxes: list[PageBox], current_line: list[dict], page_height: float) -> None:
        text = " ".join(cw["text"] for cw in current_line)
        sz = sum(cw["size"] for cw in current_line) / len(current_line)
        y_top = page_height - min(cw["top"] for cw in current_line)
        y_bot = page_height - max(cw["bottom"] for cw in current_line)
        x = min(cw["x0"] for cw in current_line)
        boxes.append(PageBox(x=x, y_top=y_top, y_bot=y_bot, sz=sz, text=text))

    def _build_chapter_index(self) -> None:
        """
        Single-pass scan: build chapter-to-pages index.
        Only extracts words (no OCR) for speed; page boxes are built
        lazily with OCR in _extract_page_boxes when chapters are read.
        """
        header_pages: dict[tuple[str, int], list[int]] = {}

        with pdfplumber.open(self._pdf_path) as pdf:
            for pg_idx, page in enumerate(pdf.pages):
                self._page_widths[pg_idx] = float(page.width)
                page_height = float(page.height)
                words = page.extract_words(extra_attrs=["size"])
                raw_boxes = self._words_to_boxes(words, page_height, float(page.width))

                # Sort header keys by length (descending) to avoid collisions (e.g. "I JOHN" before "JOHN")
                header_keys = sorted(_HEADER_TO_VAULT.keys(), key=len, reverse=True)
                
                for pb in raw_boxes:
                    norm = re.sub(r"\s+", " ", pb.text.strip())
                    
                    # 1. Check for running chapter header (standard numbered header)
                    m_header = _HEADER_PAT.match(norm) or _HEADER_PREFIX_PAT.match(norm)
                    if m_header and pb.y_top > 560 and 8.0 <= pb.sz <= 10.5:
                        book_str = m_header.group(1).strip()
                        # Use length-sorted keys for precise matching
                        matched_book = None
                        for k in header_keys:
                            if k == book_str:
                                matched_book = _HEADER_TO_VAULT[k]
                                break
                        if matched_book:
                            nums_str = m_header.group(2)
                            for ch_num in [int(n.strip()) for n in nums_str.split(",")]:
                                header_pages.setdefault((matched_book, ch_num), []).append(pg_idx)
                    
                    # 2. Check for Book Title (e.g. "ACCORDING TO JOHN")
                    # Usually large font (sz > 10) in the top half of the page
                    elif _BOOK_TITLE_PAT.match(norm) and pb.sz > 10.0 and pb.y_top > 300:
                        # Extract the book name from the title using length-sorted keys and word boundaries
                        for b_key in header_keys:
                            # Use \b to ensure we match "JOHN" and not "I JOHN" partially
                            if re.search(r"\b" + re.escape(b_key) + r"\b", norm):
                                # SECURE: Don't let Gospel "JOHN" match "LETTER OF JOHN"
                                if b_key == "JOHN" and ("LETTER" in norm or "EPISTLE" in norm):
                                    continue
                                b_vault = _HEADER_TO_VAULT[b_key]
                                self._book_start_pages.setdefault(b_vault, pg_idx)
                                break

        # Build final index: prepend start page (one before first header page)
        for key, pages in header_pages.items():
            pages.sort()
            start = max(0, pages[0] - 1)
            self._chapter_pages[key] = sorted(set([start] + pages))

        self._fill_chapter_gaps()

    def _fill_chapter_gaps(self) -> None:
        """
        Infer pages for chapters that never got a running header (single-page chapters
        like Matthew 1 or Isaiah 53).  For each book, fill gaps between known chapters
        using the boundary pages of the adjacent chapters.  Also adds a missing chapter 1
        using the first-known chapter's prepended start page.
        """
        by_book: dict[str, list[int]] = {}
        for book, ch in self._chapter_pages:
            by_book.setdefault(book, []).append(ch)

        for book, chapters in by_book.items():
            chapters.sort()

            # Fill gaps between adjacent detected chapters
            for i in range(len(chapters) - 1):
                curr, nxt = chapters[i], chapters[i + 1]
                for missing in range(curr + 1, nxt):
                    prev_pages = self._chapter_pages[(book, curr)]
                    next_pages = self._chapter_pages[(book, nxt)]
                    boundary_page = next_pages[0]
                    self._chapter_pages[(book, curr)] = sorted(set(prev_pages + [boundary_page]))
                    self._chapter_pages[(book, missing)] = sorted(
                        set([boundary_page] + next_pages)
                    )

            # Missing chapter 1: infer from book start page through the page
            # immediately before chapter 2 begins, if book-start evidence exists.
            if chapters[0] > 1 and 1 not in chapters:
                start_page = self._book_start_pages.get(book)
                if start_page is None:
                    min_ch = chapters[0]
                    min_pages = self._chapter_pages[(book, min_ch)]
                    self._chapter_pages[(book, 1)] = [min_pages[0]]
                    continue

                next_pages = self._chapter_pages[(book, chapters[0])]
                end_page = max(start_page, next_pages[0] - 1)
                self._chapter_pages[(book, 1)] = list(range(start_page, end_page + 1))

    # ── Page box extraction ────────────────────────────────────────────────────

    def _extract_page_boxes(self, pg_idx: int) -> list[PageBox]:
        """Return page boxes for the given page index, building them on first access.

        OCR glyph-recovery is applied here so only pages actually needed for
        chapter extraction pay the ~1.8s OCR cost per page.
        """
        if pg_idx in self._page_box_cache:
            return self._page_box_cache[pg_idx]

        with pdfplumber.open(self._pdf_path) as pdf:
            page = pdf.pages[pg_idx]
            page_height = float(page.height)
            page_width = float(page.width)
            words = page.extract_words(extra_attrs=["size"])
            words = self._ocr_fix_words(words, page)
            raw_boxes = self._words_to_boxes(words, page_height, page_width)

            boxes: list[PageBox] = []
            for pb in raw_boxes:
                norm = re.sub(r"\s+", " ", pb.text.strip())
                m = _HEADER_PREFIX_PAT.match(norm)
                if m and pb.y_top > 560 and 8.0 <= pb.sz <= 10.5:
                    suffix = norm[m.end():]
                    pb = PageBox(x=pb.x, y_top=pb.y_top, y_bot=pb.y_bot, sz=pb.sz, text=suffix)
                boxes.append(pb)

            self._page_box_cache[pg_idx] = boxes

        return self._page_box_cache[pg_idx]
