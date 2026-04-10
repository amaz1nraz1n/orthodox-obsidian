"""
Adapter: ManleyArchiveSource

Reads Johanna Manley's *The Bible and the Holy Fathers for Orthodox* from the
Internet Archive OCR text derivative and yields Fathers companions keyed to the
scripture chapter being commented on.

The source is patristic-only:
  - read_text()  -> empty
  - read_notes() -> empty
  - read_intros() -> empty
  - read_fathers() -> ChapterFathers grouped by (book, chapter)

Input paths may be either:
  - a local OCR text file used by tests, or
  - the Archive.org item URL from sources.yaml.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlparse
from urllib.request import urlopen

from vault_builder.domain.canon import BOOK_ABBREVIATIONS, BOOK_FOLDER, book_file_prefix
from vault_builder.domain.models import (
    Book,
    BookIntro,
    ChapterFathers,
    ChapterNotes,
    PatristicExcerpt,
    PatristicType,
)
from vault_builder.ports.patristic_source import PatristicSource
from vault_builder.ports.source import ScriptureSource

logger = logging.getLogger(__name__)

_BOOK_HEADING_TO_BOOK: dict[str, str] = {
    # Base canonical names.
    **{book.upper(): book for book in BOOK_FOLDER},
    # Common OCR / Bible-title variants.
    "PSALM": "Psalms",
    "PSALMS": "Psalms",
    "ACTS OF THE APOSTLES": "Acts",
    "SONG OF SONGS": "Song of Solomon",
    "SONG OF SOLOMON": "Song of Solomon",
    "1 SAMUEL": "I Kingdoms",
    "I SAMUEL": "I Kingdoms",
    "2 SAMUEL": "II Kingdoms",
    "II SAMUEL": "II Kingdoms",
    "1 KINGS": "III Kingdoms",
    "I KINGS": "III Kingdoms",
    "2 KINGS": "IV Kingdoms",
    "II KINGS": "IV Kingdoms",
    "1 CHRONICLES": "I Chronicles",
    "I CHRONICLES": "I Chronicles",
    "2 CHRONICLES": "II Chronicles",
    "II CHRONICLES": "II Chronicles",
    "1 ESDRAS": "I Esdras",
    "I ESDRAS": "I Esdras",
    "1 MACCABEES": "I Maccabees",
    "I MACCABEES": "I Maccabees",
    "2 MACCABEES": "II Maccabees",
    "II MACCABEES": "II Maccabees",
    "3 MACCABEES": "III Maccabees",
    "III MACCABEES": "III Maccabees",
    "1 CORINTHIANS": "I Corinthians",
    "I CORINTHIANS": "I Corinthians",
    "2 CORINTHIANS": "II Corinthians",
    "II CORINTHIANS": "II Corinthians",
    "1 THESSALONIANS": "I Thessalonians",
    "I THESSALONIANS": "I Thessalonians",
    "2 THESSALONIANS": "II Thessalonians",
    "II THESSALONIANS": "II Thessalonians",
    "1 TIMOTHY": "I Timothy",
    "I TIMOTHY": "I Timothy",
    "2 TIMOTHY": "II Timothy",
    "II TIMOTHY": "II Timothy",
    "1 PETER": "I Peter",
    "I PETER": "I Peter",
    "2 PETER": "II Peter",
    "II PETER": "II Peter",
    "1 JOHN": "I John",
    "I JOHN": "I John",
    "2 JOHN": "II John",
    "II JOHN": "II John",
    "3 JOHN": "III John",
    "III JOHN": "III John",
}

_BOOK_HEADING_KEYS = sorted(_BOOK_HEADING_TO_BOOK, key=len, reverse=True)
_BOOK_HEADING_PAT = re.compile(
    r"^(" + "|".join(re.escape(k) for k in _BOOK_HEADING_KEYS) + r")\s+(\d{1,3})\b",
    re.IGNORECASE,
)

_ATTRIB_SPLIT_RE = re.compile(r"^(?P<author>.+?)\.\s+(?P<work>.+)$")
_ON_REF_RE = re.compile(
    r"(?i)^(?P<prefix>.+?)\s+on\s+(?P<book>[A-Za-z][A-Za-z .'-]+?)\s+(?P<chapter>[IVXLC\d]+)"
    r"(?P<verses>(?:,\s*\d+(?:\s*-\s*\d+)?)*)$"
)
_BODY_REF_PAT_TEMPLATE = r"(?i)\b{book}\.?\s+(\d+):(\d+)(?:\s*[-–—]\s*(\d+))?"
_PAGE_NUM_RE = re.compile(r"^\d{1,4}$")
_VERSE_START_RE = re.compile(r"^(\d{1,3})\s+")
_CONTEXT_HEADER_RE = re.compile(
    r"\b(WEEK|SUNDAY|MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|LITURGY|"
    r"MATINS|TRIODION|TRIODIAN|PASCHA|PENTECOST|APPENDIX|GREAT\s+LENT|"
    r"\d+(?:st|nd|rd|th)\s+WEEK|(?:OGL|APe|OPA|CFW|OPE)\))\b",
    re.IGNORECASE,
)
_BIBLIOGRAPHY_ENTRY_RE = re.compile(r"^[A-Z]\d+\.\s")
_BLOCKED_AUTHORS = {"scofield"}
_ROMAN_RE = re.compile(r"^(?=[IVXLC]+$)M*(?:CM|CD|D?C{0,3})"
                        r"(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$")
_OCR_ARTIFACT_CHARS_RE = re.compile(r"[|{}@=£$]")
_OCR_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bB¥"), "B#"),
    (re.compile(r"\bbegotton\b", re.IGNORECASE), "begotten"),
    (re.compile(r"\bDOVETING\b"), "DOUBTING"),
    (re.compile(r"\bJobn\b"), "John"),
    (re.compile(r"\bJudg-\s*ments\b", re.IGNORECASE), "Judgments"),
    (re.compile(r"\bCorin-\s*thians\b", re.IGNORECASE), "Corinthians"),
    (re.compile(r"\bMat-\s*thew\b", re.IGNORECASE), "Matthew"),
    (re.compile(r"\bHomi-\s*ly\b", re.IGNORECASE), "Homily"),
    (re.compile(r"\bHom-\s*bom\s*ilies\b", re.IGNORECASE), "Homilies"),
    (re.compile(r"\bCen-\s*tury\b", re.IGNORECASE), "Century"),
    (re.compile(r"\bThes-\s*salonians\b", re.IGNORECASE), "Thessalonians"),
    (re.compile(r"\bLen-\s*ten\b", re.IGNORECASE), "Lenten"),
    (re.compile(r"\bMysta-\s*gogy\b", re.IGNORECASE), "Mystagogy"),
    (re.compile(r"\bSmyr-\s*naeans\b", re.IGNORECASE), "Smyrnaeans"),
    (re.compile(r"\bConcern-\s*ing\b", re.IGNORECASE), "Concerning"),
    (re.compile(r"\bColos-\s*sians\b", re.IGNORECASE), "Colossians"),
    (re.compile(r"\bDis-\s*Ii\s*courses\b", re.IGNORECASE), "Discourses"),
    (re.compile(r"\bHea\s+ABA!\s+", re.IGNORECASE), ""),
    (re.compile(r"\bk\s+Myst\.\s*Cat\.II,", re.IGNORECASE), "Myst. Cat.II,"),
    (re.compile(r"\bsce\b", re.IGNORECASE), "see"),
    (re.compile(r"\bseck\b", re.IGNORECASE), "seek"),
    (re.compile(r"Velimirov[ií]ć", re.IGNORECASE), "Velimirovic"),
)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _strip_st_prefix(text: str) -> str:
    return re.sub(r"^(?:St\.|Saint)\s+", "", text.strip(), flags=re.IGNORECASE)


def _roman_to_int(value: str) -> int:
    value = value.strip().upper()
    if value.isdigit():
        return int(value)
    numerals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(value):
        cur = numerals[ch]
        if cur < prev:
            total -= cur
        else:
            total += cur
            prev = cur
    return total


def _is_page_number_block(block: str) -> bool:
    return bool(_PAGE_NUM_RE.fullmatch(block.strip()))


def _is_context_header(block: str) -> bool:
    return bool(_CONTEXT_HEADER_RE.search(block))


def _strip_context_headers(block: str) -> str:
    lines = block.splitlines()
    kept = [line for line in lines if not _is_context_header(line)]
    return "\n".join(kept).strip()


def _normalize_ocr_text(text: str) -> str:
    text = _OCR_ARTIFACT_CHARS_RE.sub(" ", text)
    for pattern, replacement in _OCR_FIXES:
        text = pattern.sub(replacement, text)
    text = re.sub(r"([A-Za-z]{2,})-\s+[A-Za-z]\s+([A-Za-z]{2,})", r"\1\2", text)
    text = re.sub(r"([A-Za-z]{2,})-\s+([A-Za-z]{2,})", r"\1\2", text)
    text = re.sub(r" {2,}", " ", text)
    return text


def _is_title_candidate(block: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", block)
    return len(letters) >= 10 and block == block.upper() and not _is_context_header(block)


def _book_sort_key(book: str) -> tuple[int, int]:
    folder, order = BOOK_FOLDER.get(book, ("99 - Other", 99))
    return (0 if folder.startswith("01") else 1 if folder.startswith("02") else 2, order)


def _book_aliases(book: str) -> list[str]:
    aliases = {book}
    abbr = BOOK_ABBREVIATIONS.get(book)
    if abbr:
        aliases.add(abbr)
        aliases.add(abbr.replace(" ", ""))
    aliases.add(book_file_prefix(book))
    if book == "Psalms":
        aliases.update({"Psalm", "Psalms", "Ps"})
    if book.startswith("I "):
        aliases.add(book.replace("I ", "1 ", 1))
    if book.startswith("II "):
        aliases.add(book.replace("II ", "2 ", 1))
    if book.startswith("III "):
        aliases.add(book.replace("III ", "3 ", 1))
    return sorted(aliases, key=len, reverse=True)


def _find_same_book_ref(text: str, book: str) -> tuple[int, int] | None:
    for alias in _book_aliases(book):
        pat = re.compile(_BODY_REF_PAT_TEMPLATE.format(book=re.escape(alias)), re.IGNORECASE)
        m = pat.search(text)
        if not m:
            continue
        verse_start = int(m.group(2))
        verse_end = int(m.group(3)) if m.group(3) else None
        return verse_start, verse_end or verse_start
    return None


def _trim_body_to_commentary(body: str) -> str:
    lines = body.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if _is_title_candidate(stripped):
            return "\n".join(lines[idx:]).strip()
    return ""


_TRAILING_ARTIFACT_RE = re.compile(r"\s*[|{}]+[^A-Za-z]*$")
_LEADING_PIPE_RE = re.compile(r"^\s*\|\s*")


def _is_noise_line(raw_line: str, cleaned_line: str) -> bool:
    stripped = cleaned_line.strip()
    if not stripped:
        return False
    letters = sum(1 for c in stripped if c.isalpha())
    total = len(stripped)
    if letters / total < 0.5:
        return True
    if len(stripped.split()) <= 3 and letters < 5:
        return True
    raw_stripped = raw_line.strip()
    if re.search(r"[|{}@]", raw_stripped) and letters < 5:
        return True
    return False


def _clean_body_text(text: str) -> str:
    text = _normalize_ocr_text(text.replace("\u201e", "\u201c"))

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        cleaned = _TRAILING_ARTIFACT_RE.sub("", line)
        cleaned = _LEADING_PIPE_RE.sub("", cleaned)
        cleaned = _normalize_whitespace(cleaned)
        if _is_noise_line(line, cleaned):
            continue
        cleaned_lines.append(cleaned)

    return "\n".join(cleaned_lines).strip()


def _is_plausible_author(author: str) -> bool:
    author = author.strip()
    if not author:
        return False
    if len(author) > 80:
        return False
    if any(ch.isdigit() for ch in author):
        return False
    if not re.search(r"[A-Za-z]", author):
        return False
    if author.islower():
        return False
    if len(author.split()) > 12:
        return False
    tail = re.sub(r"[\s.,;:—-]+$", "", author)
    if tail.split()[-1] in {"St", "Rev", "Bp", "Dr"}:
        return False
    return True


def _recover_citation_text(block_raw: str) -> str:
    """
    Recover the attribution line for a bibliography block.

    Some OCR blocks split the work title across a hyphenated wrap immediately
    before the B# marker. In that case the line containing B# is incomplete on
    its own, so we fall back to the whole block joined onto one line.
    """
    lines = [line.strip() for line in block_raw.splitlines() if line.strip()]
    if not lines:
        return block_raw.strip()

    citation_line = next((line for line in lines if "B#" in line), lines[-1])
    pre_b = citation_line.split("B#", 1)[0].strip()
    if pre_b and _ATTRIB_SPLIT_RE.match(pre_b):
        return citation_line

    joined = _normalize_whitespace(" ".join(lines))
    joined_pre_b = joined.split("B#", 1)[0].strip()
    if joined_pre_b and _ATTRIB_SPLIT_RE.match(joined_pre_b):
        return joined

    return citation_line


def _parse_explicit_on_ref(text: str) -> tuple[str | None, int | None, int | None, str | None]:
    """
    Parse lines like:
      "Homily LIX on Matthew XVIII, 4, 5"

    Returns (work, verse_start, verse_end, section).
    """
    m = _ON_REF_RE.match(text)
    if not m:
        return None, None, None, None

    prefix = _normalize_whitespace(m.group("prefix"))
    chapter = _roman_to_int(m.group("chapter"))
    verses = _normalize_whitespace(m.group("verses").lstrip(","))
    verse_numbers = [int(v) for v in re.findall(r"\d+", verses)]
    verse_start = verse_numbers[0] if verse_numbers else None
    verse_end = verse_numbers[-1] if len(verse_numbers) > 1 else verse_start
    work = f"{prefix} on {m.group('book').strip()} {chapter}"
    section = verses or None
    return work, verse_start, verse_end, section


def _classify_patristic_type(text: str) -> PatristicType:
    lower = text.lower()
    if any(token in lower for token in ("stichera", "tropar", "liturgy", "prayer of", "prayer ", "canon")):
        return PatristicType.LITURGICAL
    if "homily" in lower or "homilies" in lower:
        return PatristicType.HOMILY
    if "commentary" in lower:
        return PatristicType.COMMENTARY
    return PatristicType.COMMENTARY


class ManleyArchiveSource(ScriptureSource, PatristicSource):
    """
    Parse Manley's OCR text and emit Fathers companions only.

    sample_only/sample_chapters mirror the other source adapters: sample mode
    restricts output to the explicitly requested chapters.
    """

    def __init__(
        self,
        path: str,
        sample_only: bool = True,
        sample_chapters: Optional[set[tuple[str, int]]] = None,
    ) -> None:
        self.path = path
        self.sample_only = sample_only
        self.sample_chapters = sample_chapters or set()

    def read_text(self) -> Iterator[Book]:
        return iter([])

    def read_notes(self) -> Iterator[ChapterNotes]:
        return iter([])

    def read_intros(self) -> Iterator[BookIntro]:
        return iter([])

    def read_fathers(self) -> Iterator[ChapterFathers]:
        text = self._load_ocr_text()
        fathers_by_chapter = self._parse_ocr_text(text)

        if self.sample_only:
            if self.sample_chapters:
                fathers_by_chapter = {
                    key: value
                    for key, value in fathers_by_chapter.items()
                    if key in self.sample_chapters
                }
            else:
                fathers_by_chapter = {}

        for key in sorted(fathers_by_chapter, key=lambda item: (_book_sort_key(item[0]), item[1])):
            yield fathers_by_chapter[key]

    def _load_ocr_text(self) -> str:
        if os.path.exists(self.path):
            return Path(self.path).read_text(encoding="utf-8")

        if self.path.startswith(("http://", "https://")):
            if "archive.org/details/" in self.path:
                return self._load_archive_text(self.path)
            with urlopen(self.path, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="ignore")

        raise FileNotFoundError(f"Manley OCR source not found: {self.path}")

    def _load_archive_text(self, item_url: str) -> str:
        identifier = self._archive_identifier(item_url)
        meta_url = f"https://archive.org/metadata/{identifier}"
        logger.info("Fetching Manley archive metadata: %s", meta_url)
        with urlopen(meta_url, timeout=60) as resp:
            metadata = json.loads(resp.read().decode("utf-8", errors="ignore"))

        txt_name = self._pick_txt_derivative(metadata)
        if not txt_name:
            raise RuntimeError(f"No OCR text derivative found for Archive item {identifier}")

        download_url = f"https://archive.org/download/{identifier}/{quote(txt_name)}"
        logger.info("Fetching Manley OCR text: %s", download_url)
        with urlopen(download_url, timeout=60) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    @staticmethod
    def _archive_identifier(item_url: str) -> str:
        parsed = urlparse(item_url)
        m = re.search(r"/details/([^/?#]+)", parsed.path)
        if m:
            return m.group(1)
        if parsed.netloc.endswith("archive.org") and parsed.path:
            return parsed.path.strip("/")
        raise ValueError(f"Cannot determine Archive.org identifier from {item_url!r}")

    @staticmethod
    def _pick_txt_derivative(metadata: dict) -> str | None:
        files = metadata.get("files", [])
        names = [f.get("name", "") for f in files if isinstance(f, dict)]
        for name in names:
            if name.endswith("_djvu.txt"):
                return name
        for name in names:
            if name.endswith(".txt"):
                return name
        return None

    def _parse_ocr_text(self, text: str) -> dict[tuple[str, int], ChapterFathers]:
        chapters: dict[tuple[str, int], ChapterFathers] = {}
        current_book: str | None = None
        current_chapter: int | None = None
        current_reading_start: int | None = None
        awaiting_scripture = False
        in_bibliography = False
        buffer: list[str] = []

        def finalize(citation_text: str) -> None:
            nonlocal buffer
            if current_book is None or current_chapter is None:
                buffer = []
                return
            if not buffer:
                return

            body = _trim_body_to_commentary("\n\n".join(buffer))
            if not body:
                buffer = []
                return
            body = _clean_body_text(body)
            if not body:
                buffer = []
                return

            pre_b = citation_text.split("B#", 1)[0].strip()
            pre_b = _normalize_whitespace(pre_b)
            pre_b = _strip_st_prefix(pre_b)
            author, work, verse_start, verse_end, section = self._parse_attribution(
                pre_b,
                body,
                current_book,
                current_chapter,
                current_reading_start,
            )
            if not author or not work:
                buffer = []
                return

            if not _is_plausible_author(author):
                buffer = []
                return

            full_cite = _normalize_ocr_text(f"{author} {work} {citation_text}").lower()
            if any(blocked in full_cite for blocked in _BLOCKED_AUTHORS):
                buffer = []
                return

            excerpt_type = _classify_patristic_type(f"{author} {work} {body}")
            key = (current_book, current_chapter)
            if key not in chapters:
                chapters[key] = ChapterFathers(
                    book=current_book,
                    chapter=current_chapter,
                    source="Manley",
                )

            chapters[key].add_excerpt(
                excerpt_type,
                PatristicExcerpt(
                    father=author,
                    work=work,
                    content=body,
                    verse_start=verse_start or 1,
                    verse_end=verse_end,
                    section=section,
                ),
            )
            buffer = []

        blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
        for raw_block in blocks:
            block_raw = _normalize_ocr_text(raw_block.strip("\n"))
            block = _normalize_whitespace(block_raw)
            if not block:
                continue

            heading_match = _BOOK_HEADING_PAT.match(block)
            if heading_match:
                if buffer:
                    buffer = []
                current_book = _BOOK_HEADING_TO_BOOK[heading_match.group(1).upper()]
                current_chapter = int(heading_match.group(2))
                current_reading_start = None
                awaiting_scripture = True
                in_bibliography = False
                continue

            if current_book is None or current_chapter is None:
                continue

            if in_bibliography:
                continue

            if _is_page_number_block(block):
                continue

            if awaiting_scripture:
                verse_match = _VERSE_START_RE.match(block)
                if verse_match:
                    current_reading_start = int(verse_match.group(1))
                    awaiting_scripture = False
                continue

            if _BIBLIOGRAPHY_ENTRY_RE.match(block):
                in_bibliography = True
                continue

            if "B#" in block:
                citation_line = _recover_citation_text(block_raw)
                pre_b = citation_line.split("B#", 1)[0].strip()
                if pre_b:
                    buffer.append(pre_b)
                finalize(citation_line)
                continue

            cleaned = _strip_context_headers(block_raw)
            if cleaned:
                buffer.append(_normalize_ocr_text(cleaned))

        return chapters

    def _parse_attribution(
        self,
        citation_text: str,
        body_text: str,
        current_book: str,
        current_chapter: int,
        current_reading_start: int | None,
    ) -> tuple[str | None, str | None, int | None, int | None, str | None]:
        m = _ATTRIB_SPLIT_RE.match(citation_text)
        if not m:
            return None, None, None, None, None

        author = _normalize_whitespace(m.group("author"))
        author = _normalize_ocr_text(author)
        work_text = _normalize_ocr_text(_normalize_whitespace(m.group("work").rstrip(".")))

        verse_start = current_reading_start or 1
        verse_end: int | None = None
        section: str | None = None

        body_ref = _find_same_book_ref(body_text, current_book)
        if body_ref is not None:
            verse_start, verse_end = body_ref

        explicit = _parse_explicit_on_ref(work_text)
        if explicit[0]:
            work_text, explicit_start, explicit_end, explicit_section = explicit
            if explicit_start is not None:
                verse_start = explicit_start
            if explicit_end is not None:
                verse_end = explicit_end
            section = explicit_section

        if verse_end is None:
            verse_end = None

        # Keep the attribution title concise; strip trailing page-list artifacts.
        work_text = work_text.strip(" ,.")

        return author, work_text, verse_start, verse_end, section
