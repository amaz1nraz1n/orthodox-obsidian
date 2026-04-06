"""
Adapter: DbhEpubSource

Reads the David Bentley Hart NT EPUB and yields domain Book and ChapterNotes
objects for all 27 NT books.

EPUB structure (Calibre-converted, one file per book):
  - Books: text/part0011.html (Matthew) through text/part0037.html (Revelation)
  - Book headings: <h2 class="h1" id="chNN"> (multi-chapter)
                   <h2 class="h2a" id="chNN"> (single-chapter — no h3 follows)
  - Chapter headings: <h3 class="h2"><span class="smallcaps1">CHAPTER ONE</span></h3>
    Chapter names are spelled out; strip "CHAPTER " and convert ordinal to int.
  - Verse text: <p class="indent"> paragraphs containing multiple verses.
    Verse numbers: <span class="superscript">N</span> (digit-only content).
    Footnote markers: <span class="superscript"><a class="calibre6" ...>letter</a></span>
  - GOD/god typography: G<span class="smallcaps">OD</span> → plain "GOD".
    Smallcaps span content is concatenated WITHOUT a preceding space.
  - Footnote definitions: <p class="notes" id="footnote-NNN"> at bottom of same file.
    Letter-indexed (a, b, c…) per book; IDs count downward (Calibre artefact).
    All footnotes → NoteType.TRANSLATOR.
  - Single-chapter books: Philemon, II John, III John, Jude — implicit chapter 1.
  - Bylines ("BY PAUL", "ATTRIBUTED TO PAUL") appear as plain <p> paragraphs
    between the book h2 and the first h3; they contain no verse markers and
    are naturally skipped by the verse-text parser.
"""

import re
import warnings
import zipfile
from typing import Iterator, Optional

from bs4 import BeautifulSoup, NavigableString, Tag, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from vault_builder.domain.models import Book, Chapter, ChapterNotes, NoteType, StudyNote, Verse

# ── Book file map (spine order) ───────────────────────────────────────────────

_PART_TO_BOOK: dict[str, str] = {
    "text/part0011.html": "Matthew",
    "text/part0012.html": "Mark",
    "text/part0013.html": "Luke",
    "text/part0014.html": "John",
    "text/part0015.html": "Acts",
    "text/part0016.html": "Romans",
    "text/part0017.html": "I Corinthians",
    "text/part0018.html": "II Corinthians",
    "text/part0019.html": "Galatians",
    "text/part0020.html": "Ephesians",
    "text/part0021.html": "Philippians",
    "text/part0022.html": "Colossians",
    "text/part0023.html": "I Thessalonians",
    "text/part0024.html": "II Thessalonians",
    "text/part0025.html": "I Timothy",
    "text/part0026.html": "II Timothy",
    "text/part0027.html": "Titus",
    "text/part0028.html": "Philemon",
    "text/part0029.html": "Hebrews",
    "text/part0030.html": "James",
    "text/part0031.html": "I Peter",
    "text/part0032.html": "II Peter",
    "text/part0033.html": "I John",
    "text/part0034.html": "II John",
    "text/part0035.html": "III John",
    "text/part0036.html": "Jude",
    "text/part0037.html": "Revelation",
}

# Single-chapter books: no <h3> chapter heading, treat as chapter 1.
_SINGLE_CHAPTER_BOOKS: frozenset[str] = frozenset({
    "Philemon", "II John", "III John", "Jude",
})

# ── Chapter ordinal → integer ─────────────────────────────────────────────────

_ORDINAL: dict[str, int] = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
    "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10,
    "ELEVEN": 11, "TWELVE": 12, "THIRTEEN": 13, "FOURTEEN": 14,
    "FIFTEEN": 15, "SIXTEEN": 16, "SEVENTEEN": 17, "EIGHTEEN": 18,
    "NINETEEN": 19, "TWENTY": 20,
    "TWENTY-ONE": 21, "TWENTY-TWO": 22, "TWENTY-THREE": 23,
    "TWENTY-FOUR": 24, "TWENTY-FIVE": 25, "TWENTY-SIX": 26,
    "TWENTY-SEVEN": 27, "TWENTY-EIGHT": 28,
}


def _parse_chapter_number(h3: Tag) -> Optional[int]:
    """Extract chapter number from <h3 class="h2"><span class="smallcaps1">CHAPTER N</span></h3>."""
    span = h3.find("span", class_="smallcaps1")
    if not span:
        return None
    text = span.get_text(strip=True).upper()
    if not text.startswith("CHAPTER "):
        return None
    ordinal = text[len("CHAPTER "):].strip()
    return _ORDINAL.get(ordinal)


# ── Verse text collection ─────────────────────────────────────────────────────

def _collect_verse_segments(
    p: Tag,
    book: str,
    chapter: int,
    fn_map: dict[int, tuple[str, int, int]],
) -> dict[int, str]:
    """
    Parse a single <p class="indent"> paragraph into a mapping of
    verse_number → verse_text.  Also populates fn_map with footnote
    positions (footnote_id → (book, chapter, verse)).

    Text is built as a list of fragments per verse and joined without
    extra spaces so that G + OD → "GOD" (no space injected between
    a NavigableString and an adjacent smallcaps span).
    """
    verses: dict[int, list[str]] = {}
    current_verse: Optional[int] = None

    def add(text: str) -> None:
        if current_verse is not None and text:
            verses.setdefault(current_verse, []).append(text)

    def walk(node: Tag) -> None:
        nonlocal current_verse
        children = list(node.children)
        i = 0
        while i < len(children):
            child = children[i]
            if isinstance(child, NavigableString):
                add(str(child))
                i += 1
                continue

            if not isinstance(child, Tag):
                i += 1
                continue

            cls = child.get("class") or []

            # ── Verse-number superscript ──────────────────────────── #
            if child.name == "span" and "superscript" in cls:
                inner_a = child.find("a", class_="calibre6")
                if inner_a:
                    # Footnote marker — record and embed deep-link
                    href = inner_a.get("href", "")
                    fn_id = _extract_fn_id(href)
                    if fn_id is not None and current_verse is not None:
                        fn_map[fn_id] = (book, chapter, current_verse)
                        marker = (
                            f'<sup class="nt-tn">'
                            f'[[{book} {chapter} — DBH Notes#^fn{fn_id}|‡]]'
                            f'</sup>'
                        )
                        add(marker)
                else:
                    # Verse number — may be split across two consecutive
                    # digit superscripts (Calibre artefact, e.g. "1"+"8"→18)
                    num_text = child.get_text(strip=True)
                    if num_text.isdigit():
                        # Peek at next sibling
                        if i + 1 < len(children):
                            nxt = children[i + 1]
                            if (
                                isinstance(nxt, Tag)
                                and nxt.name == "span"
                                and "superscript" in (nxt.get("class") or [])
                                and not nxt.find("a", class_="calibre6")
                            ):
                                nxt_text = nxt.get_text(strip=True)
                                if nxt_text.isdigit():
                                    num_text = num_text + nxt_text
                                    i += 1  # consume the second span
                        current_verse = int(num_text)

            # ── GOD small-caps — concatenate without space ────────── #
            elif child.name == "span" and "smallcaps" in cls and "smallcaps1" not in cls:
                add(child.get_text())

            # ── Italic / emphasis ─────────────────────────────────── #
            elif child.name in ("em", "i"):
                inner = child.get_text()
                if inner.strip():
                    add(f"*{inner}*")

            # ── All other elements — recurse ──────────────────────── #
            else:
                walk(child)

            i += 1

    walk(p)

    result: dict[int, str] = {}
    for vnum, frags in verses.items():
        text = "".join(frags)
        # Collapse runs of whitespace (but not within GOD — already handled)
        text = re.sub(r"[ \t]+", " ", text).strip()
        if text:
            result[vnum] = text
    return result


def _extract_fn_id(href: str) -> Optional[int]:
    """Extract numeric footnote ID from href like 'part0014.html#footnote-339'."""
    m = re.search(r"footnote-(\d+)$", href)
    return int(m.group(1)) if m else None


# ── Main adapter class ────────────────────────────────────────────────────────

class DbhEpubSource:
    """
    Reads the DBH NT EPUB and yields Book / ChapterNotes domain objects.
    """

    def __init__(
        self,
        epub_path: str,
        sample_only: bool = True,
        sample_chapters: Optional[set[tuple[str, int]]] = None,
    ) -> None:
        self.epub_path = epub_path
        self.sample_only = sample_only
        self.sample_chapters: set[tuple[str, int]] = sample_chapters or set()

    def read_intros(self) -> Iterator:
        return iter([])

    def read_text(self) -> Iterator[Book]:
        with zipfile.ZipFile(self.epub_path) as zf:
            for part, book_name in _PART_TO_BOOK.items():
                if not self._book_in_scope(book_name):
                    continue
                book = self._parse_book_text(zf, part, book_name)
                if book and book.chapters:
                    yield book

    def read_notes(self) -> Iterator[ChapterNotes]:
        with zipfile.ZipFile(self.epub_path) as zf:
            for part, book_name in _PART_TO_BOOK.items():
                if not self._book_in_scope(book_name):
                    continue
                yield from self._parse_book_notes(zf, part, book_name)

    # ── Scope helpers ─────────────────────────────────────────────────────── #

    def _book_in_scope(self, book_name: str) -> bool:
        if not self.sample_only:
            return True
        return any(b == book_name for b, _ in self.sample_chapters)

    def _chapter_in_scope(self, book_name: str, chapter: int) -> bool:
        if not self.sample_only:
            return True
        return (book_name, chapter) in self.sample_chapters

    # ── Book text parsing ─────────────────────────────────────────────────── #

    def _parse_book_text(
        self,
        zf: zipfile.ZipFile,
        part: str,
        book_name: str,
    ) -> Optional[Book]:
        html = zf.read(part).decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")

        is_single = book_name in _SINGLE_CHAPTER_BOOKS
        current_chapter: Optional[int] = 1 if is_single else None

        # raw[chapter][verse] = text
        raw: dict[int, dict[int, str]] = {}
        fn_map: dict[int, tuple[str, int, int]] = {}

        for el in soup.find_all(["h3", "p"]):
            if not isinstance(el, Tag):
                continue

            if el.name == "h3" and "h2" in (el.get("class") or []):
                ch_num = _parse_chapter_number(el)
                if ch_num is not None:
                    current_chapter = ch_num
                continue

            if el.name == "p" and "indent" in (el.get("class") or []):
                if current_chapter is None:
                    continue
                if not self._chapter_in_scope(book_name, current_chapter):
                    continue
                verse_texts = _collect_verse_segments(el, book_name, current_chapter, fn_map)
                ch_data = raw.setdefault(current_chapter, {})
                for vnum, text in verse_texts.items():
                    if vnum in ch_data:
                        ch_data[vnum] = ch_data[vnum] + " " + text
                    else:
                        ch_data[vnum] = text

        if not raw:
            return None

        book = Book(name=book_name)
        for ch_num in sorted(raw):
            chapter = Chapter(book=book_name, number=ch_num)
            for v_num in sorted(raw[ch_num]):
                text = raw[ch_num][v_num].strip()
                if text:
                    chapter.add_verse(v_num, text)
            if chapter.verses:
                book.add_chapter(chapter)
        return book

    # ── Notes parsing ─────────────────────────────────────────────────────── #

    def _parse_book_notes(
        self,
        zf: zipfile.ZipFile,
        part: str,
        book_name: str,
    ) -> Iterator[ChapterNotes]:
        html = zf.read(part).decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")

        is_single = book_name in _SINGLE_CHAPTER_BOOKS
        current_chapter: Optional[int] = 1 if is_single else None

        # Pass 1: walk verse paragraphs to build fn_map and chapter sequence
        fn_map: dict[int, tuple[str, int, int]] = {}
        ch_order: list[int] = []

        for el in soup.find_all(["h3", "p"]):
            if not isinstance(el, Tag):
                continue
            if el.name == "h3" and "h2" in (el.get("class") or []):
                ch_num = _parse_chapter_number(el)
                if ch_num is not None:
                    current_chapter = ch_num
                continue
            if el.name == "p" and "indent" in (el.get("class") or []):
                if current_chapter is None:
                    continue
                if current_chapter not in ch_order:
                    ch_order.append(current_chapter)
                _collect_verse_segments(el, book_name, current_chapter, fn_map)

        # Pass 2: parse footnote definitions (DOM order = reading order)
        fn_defs: dict[int, str] = {}
        for p in soup.find_all("p", class_="notes"):
            fn_id = _extract_fn_id(p.get("id", ""))
            if fn_id is None:
                continue
            # Strip the backlink anchor (first <a> child)
            for a in p.find_all("a", class_="calibre4"):
                a.decompose()
            text = _render_fn_body(p)
            if text:
                fn_defs[fn_id] = text

        # Group by chapter; maintain DOM order via fn_map insertion order
        by_chapter: dict[int, ChapterNotes] = {}
        # Process footnotes in DOM order (fn_map is insertion-ordered)
        for fn_id, (bk, ch, verse) in fn_map.items():
            if not self._chapter_in_scope(bk, ch):
                continue
            text = fn_defs.get(fn_id)
            if not text:
                continue
            if ch not in by_chapter:
                by_chapter[ch] = ChapterNotes(book=bk, chapter=ch, source="DBH")
            note = StudyNote(
                verse_number=verse,
                ref_str=f"{ch}:{verse}",
                content=text,
                anchor_id=f"fn{fn_id}",
                sort_key=verse,
            )
            by_chapter[ch].add_note(NoteType.TRANSLATOR, note)

        for ch in sorted(by_chapter):
            yield by_chapter[ch]


def _render_fn_body(p: Tag) -> str:
    """Render a <p class="notes"> body to plain Markdown text.

    Preserves:
      - <span class="greek"> content as-is (polytonic Unicode)
      - <em class="calibre5"> as *italic* (transliteration)
      - <em class="calibre7"> as *italic* (sub-superscript in transliteration)
      - <span class="superscript1"> as plain text (part of transliteration)
    Strips the leading 'a. ' / 'b. ' letter label (handled by anchor).
    """
    parts: list[str] = []
    skip_label = True  # skip the "a. " letter label at the start

    for child in p.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if skip_label:
                # Strip leading whitespace and "a. "-style label
                stripped = text.lstrip()
                if stripped.startswith(". ") or stripped == ".":
                    skip_label = False
                    text = stripped[2:] if stripped.startswith(". ") else ""
                elif not stripped:
                    continue
                else:
                    skip_label = False
            parts.append(text)
        elif isinstance(child, Tag):
            skip_label = False
            if child.name in ("em", "i"):
                inner = child.get_text()
                if inner.strip():
                    parts.append(f"*{inner}*")
            elif child.name == "span":
                parts.append(child.get_text())
            else:
                parts.append(child.get_text())

    text = "".join(parts)
    return re.sub(r"[ \t]+", " ", text).strip()
