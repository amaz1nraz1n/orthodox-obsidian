"""
Adapter: NetsEpubSource

Reads A New English Translation of the Septuagint (NETS), Oxford 2007 EPUB
and yields domain Book and ChapterNotes objects for the full LXX canon.

EPUB structure:
  - OPF: OEBPS/html/volume.opf
  - Spine: 42 chapter files (chapter01.html – chapter42.html, with a/b variants)
           + ~800 page_N.html (footnote definitions only)
  - Each chapter file contains one book (or pair for Twelve Prophets split)

Book boundary:
  - The chapter file itself maps to a book via NETS_CHAPTER_TO_BOOK
  - Bible text begins after <p class="attribute"> (translator byline)

Verse marker patterns (three coexist):
  1. <strong>N</strong> — chapter-opening verse 1 (in <p class="noindent">)
  2. <sup>N</sup> — mid-paragraph verse
  3. Plain text "N " at paragraph start (Pattern 3) — no wrapper tag

Psalm numbering:
  - <sup>3(1)</sup> → verse 3 (LXX primary; MT in parens stripped)

Footnotes:
  - Inline: <sup><a id="pgNen_X"/><a class="nounder" href="page_N.html#pgNenX">X</a></sup>
  - Definition: page_N.html → <p class="endnote" id="pgNenX">...</p>
  - All notes → NoteType.TRANSLATOR (user decision 3-A)

GBS anchors (<a id="GBS.*"/>) — strip entirely.
"""

import logging
import re
import warnings
import zipfile
from typing import Iterator, Optional

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from vault_builder.domain.models import (
    Book,
    BookIntro,
    Chapter,
    ChapterNotes,
    NoteType,
    StudyNote,
    Verse,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Chapter file → canonical vault book name
# --------------------------------------------------------------------------- #
NETS_CHAPTER_TO_BOOK: dict[str, str] = {
    "chapter01": "Genesis",
    "chapter02": "Exodus",
    "chapter03": "Leviticus",
    "chapter04": "Numbers",
    "chapter05": "Deuteronomy",
    "chapter06": "Joshua",
    "chapter07": "Judges",
    "chapter08": "Ruth",
    "chapter09": "1 Samuel",
    "chapter10": "2 Samuel",
    "chapter11": "1 Kings",
    "chapter12": "2 Kings",
    "chapter13": "1 Chronicles",
    "chapter14": "2 Chronicles",
    "chapter15": "1 Esdras",
    "chapter16": "2 Esdras",
    "chapter17": "Esther",
    "chapter18": "Judith",
    "chapter19": "Tobit",
    "chapter20": "1 Maccabees",
    "chapter21": "2 Maccabees",
    "chapter22": "3 Maccabees",
    "chapter23": "4 Maccabees",
    "chapter24": "Psalms",           # also contains Prayer of Manasseh
    "chapter24a": "Prayer of Manasseh",
    "chapter25": "Proverbs",
    "chapter26": "Ecclesiastes",
    "chapter27": "Song of Songs",
    "chapter28": "Job",
    "chapter29": "Wisdom of Solomon",
    "chapter30": "Sirach",
    "chapter31": "Psalms of Solomon",
    "chapter31a": "Psalms of Solomon",  # continuation
    "chapter33": "The Twelve Prophets",  # Hosea–Micah
    "chapter33a": "The Twelve Prophets",  # Obadiah–Malachi
    "chapter34": "Isaiah",
    "chapter34a": "Isaiah",
    "chapter35": "Jeremiah",
    "chapter35a": "Jeremiah",
    "chapter36": "Baruch",
    "chapter37": "Lamentations",
    "chapter38": "Letter of Jeremiah",
    "chapter39": "Ezekiel",
    "chapter40": "Susanna",
    "chapter41": "Daniel",
    "chapter42": "Bel and the Dragon",
}

# Twelve Prophets individual book mapping within chapter33/chapter33a
# Detected by book-heading <h2> or chapter reset patterns
_TWELVE_PROPHETS: list[str] = [
    "Hosea", "Amos", "Micah", "Joel", "Obadiah", "Jonah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
]

# Paragraph classes that carry Bible text
_TEXT_P_CLASSES: set[str] = {
    "noindent", "indent",
    "indenthanging1", "indenthanging1a", "indenthanging1c", "indenthanging1d",
    "indenthanging11", "indenthanging31",
    "blockquote1", "blockquote2",
}

# Chapter heading pattern: <p class="center"><strong>N</strong></p>
_CHAPTER_NUMBER_RE = re.compile(r"^\d+$")

# Inline footnote anchor: href="page_N.html#pgNenX" → capture anchor target
_FN_HREF_RE = re.compile(r"page_\d+\.html#(.+)")

# Verse number at start of plain-text paragraph (Pattern 3): "6 " or "14 "
# Must be followed by a space or be the entire text node start
_PLAIN_VERSE_RE = re.compile(r"^(\d+)\s+")

# Psalm verse with dual numbering: 3(1) → capture first (LXX) number
_DUAL_VERSE_RE = re.compile(r"^(\d+)\(\d+\)$")

# GBS anchor IDs to strip
_GBS_ID_RE = re.compile(r"^GBS\.")


class NetsEpubSource:
    """
    Reads the NETS EPUB and yields Book / ChapterNotes / BookIntro domain objects.

    In sample_only mode, only chapters listed in sample_chapters are extracted.
    """

    def __init__(
        self,
        epub_path: str,
        sample_only: bool = True,
        sample_chapters: Optional[set[tuple[str, int]]] = None,
    ) -> None:
        self.epub_path = epub_path
        self.sample_only = sample_only
        self.sample_chapters = sample_chapters or set()

    # ── Public interface ──────────────────────────────────────────────────────

    def read_text(self) -> Iterator[Book]:
        """Yield one Book per LXX canonical book with verse text."""
        raw: dict[str, dict[int, dict[int, str]]] = {}

        with zipfile.ZipFile(self.epub_path) as z:
            page_cache: dict[str, str] = {}

            for chapter_key, book_name in NETS_CHAPTER_TO_BOOK.items():
                html_name = f"OEBPS/html/{chapter_key}.html"
                if html_name not in z.namelist():
                    continue
                html = z.read(html_name).decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html, "lxml")
                _, bible_paras = self._split_intro_and_text(soup)

                self._parse_text(bible_paras, book_name, raw, z, page_cache)

        for book_name in sorted(raw):
            book = Book(name=book_name)
            for ch_num in sorted(raw[book_name]):
                chapter = Chapter(book=book_name, number=ch_num)
                for v_num in sorted(raw[book_name][ch_num]):
                    text = raw[book_name][ch_num][v_num].strip()
                    if text:
                        chapter.add_verse(v_num, text)
                if chapter.verses:
                    book.add_chapter(chapter)
            if book.chapters:
                yield book

    def read_notes(self) -> Iterator[ChapterNotes]:
        """Yield one ChapterNotes per chapter that has footnotes."""
        raw: dict[str, dict[int, dict[int, list[str]]]] = {}

        with zipfile.ZipFile(self.epub_path) as z:
            page_cache: dict[str, str] = {}

            for chapter_key, book_name in NETS_CHAPTER_TO_BOOK.items():
                html_name = f"OEBPS/html/{chapter_key}.html"
                if html_name not in z.namelist():
                    continue
                html = z.read(html_name).decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html, "lxml")
                _, bible_paras = self._split_intro_and_text(soup)

                self._parse_notes(bible_paras, book_name, raw, z, page_cache)

        for book_name in sorted(raw):
            for ch_num in sorted(raw[book_name]):
                notes_obj = ChapterNotes(book=book_name, chapter=ch_num, source="NETS")
                for verse_num in sorted(raw[book_name][ch_num]):
                    for content in raw[book_name][ch_num][verse_num]:
                        ref = f"{ch_num}:{verse_num}"
                        notes_obj.add_note(
                            NoteType.TRANSLATOR,
                            StudyNote(verse_number=verse_num, ref_str=ref, content=content),
                        )
                if notes_obj.translator_notes:
                    yield notes_obj

    def read_intros(self) -> Iterator[BookIntro]:
        """Yield one BookIntro per book for the translator's introduction."""
        with zipfile.ZipFile(self.epub_path) as z:
            for chapter_key, book_name in NETS_CHAPTER_TO_BOOK.items():
                # Skip continuation files — intro is only in the first file per book
                if chapter_key.endswith("a") and chapter_key != "chapter24a":
                    continue
                # Skip Prayer of Manasseh — it's a subsection of chapter24
                if chapter_key == "chapter24a":
                    continue

                html_name = f"OEBPS/html/{chapter_key}.html"
                if html_name not in z.namelist():
                    continue

                if self.sample_only:
                    # Only emit intros for sampled books
                    sampled_books = {b for b, _ in self.sample_chapters}
                    if book_name not in sampled_books:
                        continue

                html = z.read(html_name).decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html, "lxml")
                intro_text, _ = self._split_intro_and_text(soup)
                if intro_text.strip():
                    yield BookIntro(book=book_name, source="NETS", content=intro_text)

    # ── Intro/text split ──────────────────────────────────────────────────────

    def _split_intro_and_text(self, soup: BeautifulSoup) -> tuple[str, list]:
        """
        Split a chapter file into intro text and bible paragraph elements.

        The <p class="attribute"> (translator byline) is the delimiter:
        everything before it is intro; everything after is Bible text.

        Returns (intro_text_str, [bible_para_elements]).
        """
        all_paras = soup.find_all(["p", "h1", "h2", "h3", "h4", "h5"])
        intro_parts: list[str] = []
        bible_paras: list = []
        found_attr = False

        for el in all_paras:
            cls = set(el.get("class") or [])
            if "attribute" in cls:
                found_attr = True
                continue
            if not found_attr:
                text = el.get_text(" ", strip=True)
                if text:
                    intro_parts.append(text)
            else:
                bible_paras.append(el)

        return "\n\n".join(intro_parts), bible_paras

    # ── Text parsing ──────────────────────────────────────────────────────────

    def _detect_chapter_start(self, para: Tag) -> Optional[int]:
        """
        Check if a paragraph signals a new chapter.

        Two patterns:
          A) Prose: <p class="noindent"><strong>N</strong>...  → chapter N (verse 1)
          B) Psalms: <p class="center"><strong>Psalm N(M)</strong></p> → chapter N (LXX)

        Returns the chapter number if detected, else None.
        """
        cls = set(para.get("class") or [])
        strong = para.find("strong")
        if not strong:
            return None
        text = strong.get_text().strip()

        # Pattern B: Psalm heading
        if "center" in cls:
            psalm_m = re.match(r"Psalm\s+(\d+)", text)
            if psalm_m:
                return int(psalm_m.group(1))
            if _CHAPTER_NUMBER_RE.match(text):
                return int(text)
            return None

        # Pattern A: prose chapter — noindent para starting with <strong>N</strong>
        if "noindent" in cls and _CHAPTER_NUMBER_RE.match(text):
            return int(text)

        return None

    def _parse_text(
        self,
        bible_paras: list,
        book_name: str,
        raw: dict,
        z: zipfile.ZipFile,
        page_cache: dict,
    ) -> None:
        """Walk bible paragraphs and collect verse text into raw dict."""
        current_book = book_name
        current_chapter: Optional[int] = None
        current_verse: Optional[int] = None

        for para in bible_paras:
            if not isinstance(para, Tag):
                continue
            cls = set(para.get("class") or [])
            tag = para.name

            # Book heading within a multi-book chapter file (Twelve Prophets)
            if tag in ("h2", "h3") and "h2a" in cls:
                heading = para.get_text().strip()
                for prophet in _TWELVE_PROPHETS:
                    if prophet.lower() in heading.lower():
                        current_book = prophet
                        current_chapter = None
                        current_verse = None
                        break
                continue

            # Chapter detection
            detected_chapter = self._detect_chapter_start(para)
            if detected_chapter is not None:
                current_chapter = detected_chapter
                # For Psalm-style (center class), don't process verse text here
                if "center" in cls:
                    current_verse = None
                    continue
                # For prose (noindent): verse 1 is in THIS paragraph after <strong>N</strong>.
                # Pre-set to 1 so text before any <sup> is attributed correctly.
                current_verse = 1

            if current_chapter is None:
                continue

            # Skip if not in sample
            if self.sample_only and (current_book, current_chapter) not in self.sample_chapters:
                continue

            # Walk the paragraph for verse events and text
            for event in self._walk_para(para):
                kind = event[0]
                if kind == "verse_start":
                    new_verse = event[1]
                    # Skip the chapter-opener <strong>N</strong> event — already handled above
                    if detected_chapter is not None and new_verse == detected_chapter:
                        continue
                    current_verse = new_verse
                elif kind == "text" and current_verse is not None:
                    text = event[1]
                    (
                        raw
                        .setdefault(current_book, {})
                        .setdefault(current_chapter, {})
                    )
                    existing = raw[current_book][current_chapter].get(current_verse, "")
                    raw[current_book][current_chapter][current_verse] = (
                        (existing + " " + text) if existing else text
                    )

    # ── Notes parsing ─────────────────────────────────────────────────────────

    def _parse_notes(
        self,
        bible_paras: list,
        book_name: str,
        raw: dict,
        z: zipfile.ZipFile,
        page_cache: dict,
    ) -> None:
        """Walk bible paragraphs, resolve footnotes, collect into raw dict."""
        current_book = book_name
        current_chapter: Optional[int] = None
        current_verse: Optional[int] = None

        for para in bible_paras:
            if not isinstance(para, Tag):
                continue
            cls = set(para.get("class") or [])
            tag = para.name

            if tag in ("h2", "h3") and "h2a" in cls:
                heading = para.get_text().strip()
                for prophet in _TWELVE_PROPHETS:
                    if prophet.lower() in heading.lower():
                        current_book = prophet
                        current_chapter = None
                        current_verse = None
                        break
                continue

            detected_chapter = self._detect_chapter_start(para)
            if detected_chapter is not None:
                current_chapter = detected_chapter
                if "center" in cls:
                    current_verse = None
                    continue
                current_verse = 1

            if current_chapter is None:
                continue
            if self.sample_only and (current_book, current_chapter) not in self.sample_chapters:
                continue

            for event in self._walk_para(para):
                kind = event[0]
                if kind == "verse_start":
                    new_verse = event[1]
                    if detected_chapter is not None and new_verse == detected_chapter:
                        continue
                    current_verse = new_verse
                elif kind == "footnote_ref" and current_verse is not None:
                    anchor_id, page_file = event[1], event[2]
                    if page_file not in page_cache:
                        page_path = f"OEBPS/html/{page_file}"
                        if page_path in z.namelist():
                            page_cache[page_file] = z.read(page_path).decode("utf-8", errors="ignore")
                    page_html = page_cache.get(page_file, "")
                    note_text = self._resolve_footnote_from_html(anchor_id, page_html)
                    if note_text:
                        (
                            raw
                            .setdefault(current_book, {})
                            .setdefault(current_chapter, {})
                            .setdefault(current_verse, [])
                            .append(note_text)
                        )

    # ── Paragraph walker ──────────────────────────────────────────────────────

    def _walk_para(self, para: Tag) -> Iterator[tuple]:
        """
        Walk a bible paragraph. Yields:
          ("verse_start", verse_num)        — on any verse marker pattern
          ("footnote_ref", anchor_id, page) — on inline footnote marker
          ("text", text_str)                — accumulated text between markers

        Handles all three NETS verse marker patterns:
          1. <strong>N</strong>           — chapter-opening verse
          2. <sup>N</sup>                 — mid-paragraph verse
          3. Plain "N " at para start     — bare text node verse
        """
        buf: list[str] = []

        def flush():
            if buf:
                text = re.sub(r"[ \t\xa0]+", " ", "".join(buf)).strip()
                if text:
                    yield ("text", text)
                buf.clear()

        # Check for Pattern 3: plain verse number at paragraph start
        # We check the first text node of the paragraph
        para_start_checked = False

        def _walk(node, is_para_root: bool = False):
            nonlocal para_start_checked

            if getattr(node, "name", None) is None:
                # Text node (NavigableString — .name is None)
                text = str(node)
                if is_para_root and not para_start_checked:
                    para_start_checked = True
                    m = _PLAIN_VERSE_RE.match(text.lstrip())
                    if m:
                        yield from flush()
                        yield ("verse_start", int(m.group(1)))
                        remainder = text.lstrip()[m.end():]
                        if remainder.strip():
                            buf.append(remainder)
                        return
                if text.strip():
                    buf.append(text)
                return

            for child in node.children:
                if getattr(child, "name", None) is None:
                    # NavigableString text node
                    text = str(child)
                    if is_para_root and not para_start_checked:
                        para_start_checked = True
                        stripped = text.lstrip()
                        m = _PLAIN_VERSE_RE.match(stripped)
                        if m:
                            yield from flush()
                            yield ("verse_start", int(m.group(1)))
                            remainder = stripped[m.end():]
                            if remainder.strip():
                                buf.append(remainder)
                            continue
                    if text.strip():
                        buf.append(text)
                    continue

                name = child.name
                if name is None:
                    continue

                # GBS anchors — strip
                if name == "a":
                    aid = child.get("id") or ""
                    if _GBS_ID_RE.match(aid):
                        continue
                    # Inline footnote: has class "nounder" and href to page_N.html
                    cls = set(child.get("class") or [])
                    if "nounder" in cls:
                        href = child.get("href", "")
                        m = _FN_HREF_RE.match(href)
                        if m:
                            anchor_target = m.group(1)
                            page_file = href.split("#")[0]
                            yield from flush()
                            yield ("footnote_ref", anchor_target, page_file)
                            continue
                    # Inline ID anchor (back-link target for footnote) — skip
                    if aid and not _GBS_ID_RE.match(aid):
                        continue
                    continue

                # <strong> — Pattern 1: chapter-opening verse number OR emphasis
                if name == "strong":
                    text = child.get_text().strip()
                    if _CHAPTER_NUMBER_RE.match(text):
                        yield from flush()
                        para_start_checked = True
                        yield ("verse_start", int(text))
                        continue
                    # Not a verse number — keep as bold text
                    if text:
                        buf.append(f"**{text}**")
                    continue

                # <sup> — Pattern 2: mid-paragraph verse OR dual-number Psalm verse
                if name == "sup":
                    # Check if it's a footnote marker wrapper (contains <a class="nounder">)
                    inner_a = child.find("a", class_="nounder")
                    if inner_a:
                        href = inner_a.get("href", "")
                        m = _FN_HREF_RE.match(href)
                        if m:
                            anchor_target = m.group(1)
                            page_file = href.split("#")[0]
                            yield from flush()
                            yield ("footnote_ref", anchor_target, page_file)
                            continue
                        # Footnote sup with only back-link anchor — skip
                        continue
                    text = child.get_text().strip()
                    # Dual Psalm number: 3(1) → 3
                    dm = _DUAL_VERSE_RE.match(text)
                    if dm:
                        yield from flush()
                        para_start_checked = True
                        yield ("verse_start", int(dm.group(1)))
                        continue
                    if _CHAPTER_NUMBER_RE.match(text):
                        yield from flush()
                        para_start_checked = True
                        yield ("verse_start", int(text))
                        continue
                    # Not a verse number — skip (superscript footnote letter)
                    continue

                if name == "br":
                    buf.append(" ")
                    continue

                if name in ("i", "em"):
                    text = child.get_text()
                    if text.strip():
                        buf.append(f"*{text.strip()}*")
                    continue

                if name in ("b",):
                    text = child.get_text()
                    if text.strip():
                        buf.append(f"**{text.strip()}**")
                    continue

                # Recurse
                yield from _walk(child)

        yield from _walk(para, is_para_root=True)
        yield from flush()

    # ── Footnote resolution ───────────────────────────────────────────────────

    def _resolve_footnote_from_html(self, anchor_id: str, page_html: str) -> Optional[str]:
        """
        Find the endnote with id=anchor_id in page_N.html and return its text.

        Endnote structure:
          <p class="endnote"><a id="pgNenX"/>
            <sup><a class="nounder" href="...">X</a></sup>
            Note text here
          </p>
        """
        if not page_html:
            return None
        soup = BeautifulSoup(page_html, "lxml")
        anchor = soup.find("a", id=anchor_id)
        if not anchor:
            return None
        # The anchor is inside <p class="endnote"> or <p class="endnote1">
        para = anchor.find_parent("p")
        if not para:
            return None
        # Remove the back-link <sup> (first child after anchor)
        # Collect all text excluding the <sup> back-link
        parts: list[str] = []
        for child in para.children:
            if not hasattr(child, "name"):
                text = str(child).strip()
                if text:
                    parts.append(text)
                continue
            if child.name == "sup":
                continue  # skip back-link superscript
            if child.name in ("em", "i"):
                text = child.get_text().strip()
                if text:
                    parts.append(f"*{text}*")
                continue
            text = child.get_text().strip()
            if text:
                parts.append(text)
        note_text = " ".join(parts).strip()
        return note_text if note_text else None
