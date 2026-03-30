"""
Adapter: EobEpubSource

Reads the Eastern/Greek Orthodox Bible (EOB) NT EPUB and yields domain Book
objects containing per-verse text for all 27 NT books.

EPUB structure (EOB-2 split format, 128 HTML files):
  - Spine order in content.opf determines reading sequence
  - Book headings: <h1> containing book name + Greek title
  - Chapter markers: various <p> classes (style38pt..., style375pt..., chapternumber, etc.)
    whose entire text content is a single integer 1–28; detected by content, not class
  - Verse 1: implicit — text of the first <p class="msonormal1"> after the chapter marker,
    before the first <sup class="calibre31"> in that paragraph
  - Verses 2+: inline <sup class="calibre31">N</sup> within msonormal1 paragraphs
  - Poetry continuation: <p class="poetry1..."> treated as verse text continuation
  - Endnote refs: <a id="_ednrefN"> — stripped entirely
  - Section topics: <p class="sectiontopic"> — skipped
  - Appendices/endnotes: h1 not matching any NT book resets collection (stops bleed)
"""

import logging
import re
import zipfile
from typing import Iterator, Optional
from xml.etree import ElementTree

from bs4 import BeautifulSoup, NavigableString, Tag

from vault_builder.domain.models import Book, Chapter, ChapterNotes, StudyNote, Verse

logger = logging.getLogger(__name__)

# ── Note classification ───────────────────────────────────────────────────── #

_RE_BRACKET = re.compile(r"^\[\d+\w*\]\s*")

_RE_VARIANTS = re.compile(
    r"^(?:"
    r"(?:CT|TR|PT)\s+(?:reads?|omits?|adds?|has\b|ends?|includes?|refers?)"
    r"|(?:Other|A\s+few|Some|Several|Many|Most)\s+manuscripts\b"
    r"|Other\s+ancient\s+"
    r"|NT\s+agrees\s+with\b"
    r")",
    re.IGNORECASE,
)

_RE_ALTERNATIVES = re.compile(
    r"^(?:"
    r"Or\s+"
    r"|Lit\.\s+"
    r"|Literally\s+"
    r"|Other\s+translations?\s+"
    r"|Also\s+translated\s+"
    r")",
    re.IGNORECASE,
)

_RE_TRANSLATOR = re.compile(r"^(?:The\s+)?Greek\s+", re.IGNORECASE)

_RE_CROSS_REF = re.compile(
    r"^(?:"
    r"(?:See|Compare|Cf\.)\s+(?!Appendix\b)"
    r"|(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth"
    r"|Samuel|Kings|Chronicles|Ezra|Nehemiah|Tobit|Judith|Esther|Maccabees"
    r"|Job|Psalm|Proverb|Ecclesiastes|Song|Wisdom|Sirach|Isaias|Isaiah"
    r"|Jeremiah|Lamentations|Baruch|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah"
    r"|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi"
    r"|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians"
    r"|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews"
    r"|James|Peter|Jude|Revelation)\b"
    r")",
    re.IGNORECASE,
)

_RE_CITATION = re.compile(
    r"^(?:"
    r"(?:St\.|Saint|According\s+to\s+(?:St\.|Saint))\s+[A-Z]"
    r"|(?:St\.|Saint)\s+\w+\s+(?:says?|writes?|interprets?|comments?|notes?|explains?)"
    r")",
    re.IGNORECASE,
)

_RE_BACKGROUND_START = re.compile(
    r"^(?:"
    r"In\s+(?:the\s+)?(?:ancient|early|first\s+century|biblical)"
    r"|The\s+\w+\s+(?:River|Sea|Mountain|City|Province|Region|Desert)\s+was\b"
    r")",
    re.IGNORECASE,
)

_RE_BACKGROUND_LOCATION = re.compile(
    r"\bwas\s+(?:a|an|the)\s+(?:city|town|region|river|sea|mountain|province|area|place)\b",
    re.IGNORECASE,
)


def _classify_eob_note(text: str) -> str:
    """Return the ChapterNotes slot name for a raw EOB endnote string."""
    body = _RE_BRACKET.sub("", text)
    if _RE_VARIANTS.match(body):
        return "variants"
    if _RE_ALTERNATIVES.match(body):
        return "alternatives"
    if _RE_TRANSLATOR.match(body):
        return "translator_notes"
    if _RE_CROSS_REF.match(body):
        return "cross_references"
    if _RE_CITATION.match(body):
        return "citations"
    if _RE_BACKGROUND_START.match(body) or _RE_BACKGROUND_LOCATION.search(body):
        return "background_notes"
    return "footnotes"


# ── Book title mapping ────────────────────────────────────────────────────── #

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

_NT_BOOK_ORDER = list(_EOB_TITLE_TO_BOOK.values())

# CSS classes that carry verse text (prose and poetry)
_VERSE_P_CLASSES = {
    "msonormal1",
    "poetry1cxspfirst",
    "poetry1cxspmiddle",
    "poetry1cxsplast",
}

# CSS classes that indicate a poetry line break
_POETRY_P_CLASSES = {"poetry1cxspfirst", "poetry1cxspmiddle", "poetry1cxsplast"}

# CSS class on verse-number superscripts
_VERSE_SUP_CLASS = "calibre31"


class EobEpubSource:
    """
    Reads the EOB NT EPUB (EOB-2 split format) and yields Book domain objects.
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

    def read_text(self) -> Iterator[Book]:
        """Parse the EPUB and yield one Book per NT book, in canonical order."""
        raw: dict[str, dict[int, dict[int, str]]] = {}
        self._parse_epub(raw)

        for book_name in _NT_BOOK_ORDER:
            if book_name not in raw:
                continue
            book = Book(name=book_name)
            for ch_num in sorted(raw[book_name]):
                chapter = Chapter(book=book_name, number=ch_num)
                for v_num in sorted(raw[book_name][ch_num]):
                    text = raw[book_name][ch_num][v_num].strip()
                    if text:
                        chapter.verses[v_num] = Verse(number=v_num, text=text)
                if chapter.verses:
                    book.chapters[ch_num] = chapter
            if book.chapters:
                yield book

    # ── EPUB parser ───────────────────────────────────────────────────────── #

    def read_notes(self) -> Iterator[ChapterNotes]:
        """Two-pass endnote extraction.

        Pass 1: walk verse text to build ednref_num → (book, chapter, verse).
        Pass 2: parse split_124–127 for note definitions.
        Yields one ChapterNotes per in-scope (book, chapter).
        """
        ednref_map: dict[int, tuple[str, int, int]] = {}
        raw: dict[str, dict[int, dict[int, str]]] = {}
        self._parse_epub(raw, ednref_map=ednref_map)

        # Pass 2: parse definition files
        note_defs: dict[int, str] = {}
        with zipfile.ZipFile(self.epub_path) as zf:
            for split_num in range(124, 128):
                path = f"text/part0000_split_{split_num:03d}.html"
                try:
                    html = zf.read(path).decode("utf-8", errors="replace")
                except KeyError:
                    continue
                soup = BeautifulSoup(html, "lxml")
                for div in soup.find_all("div", id=re.compile(r"^edn\d+$")):
                    n = int(div["id"][3:])
                    for a in div.find_all("a", id=re.compile(r"^_edn\d+$")):
                        a.decompose()
                    text = " ".join(div.get_text(" ", strip=True).split())
                    if text:
                        note_defs[n] = text

        # Group by (book, chapter), routing each note to its classified slot
        by_chapter: dict[tuple[str, int], ChapterNotes] = {}
        for n in sorted(ednref_map):
            book, chapter, verse = ednref_map[n]
            if self.sample_only and (book, chapter) not in self.sample_chapters:
                continue
            text = note_defs.get(n)
            if not text:
                continue
            key = (book, chapter)
            if key not in by_chapter:
                by_chapter[key] = ChapterNotes(book=book, chapter=chapter, source="EOB")
            slot = _classify_eob_note(text)
            note = StudyNote(verse_number=verse, ref_str=f"{chapter}:{verse}", content=text)
            getattr(by_chapter[key], slot).append(note)

        for key in sorted(by_chapter):
            yield by_chapter[key]

    def _parse_epub(
        self,
        raw: dict[str, dict[int, dict[int, str]]],
        ednref_map: Optional[dict[int, tuple[str, int, int]]] = None,
    ) -> None:
        with zipfile.ZipFile(self.epub_path) as zf:
            spine_paths = _get_spine(zf)

            current_book: Optional[str] = None
            current_chapter: Optional[int] = None
            current_verse: Optional[int] = None

            for path in spine_paths:
                try:
                    html = zf.read(path).decode("utf-8", errors="replace")
                except KeyError:
                    logger.warning("Spine file missing from EPUB: %s", path)
                    continue

                soup = BeautifulSoup(html, "lxml")
                if not soup.body:
                    continue

                for el in soup.find_all(["h1", "p"]):
                    if not isinstance(el, Tag):
                        continue

                    # ── Book heading ──────────────────────────────────────── #
                    if el.name == "h1":
                        book_name = _detect_book(el)
                        if book_name is not None:
                            current_book = book_name
                            current_chapter = None
                            current_verse = None
                        elif current_book is not None:
                            # Unknown h1 after collecting data = appendix/endnotes
                            logger.debug(
                                "Non-book h1 after %s; stopping collection: %s",
                                current_book,
                                el.get_text(" ", strip=True)[:60],
                            )
                            current_book = None
                            current_chapter = None
                            current_verse = None
                        continue

                    # ── p elements ───────────────────────────────────────── #
                    classes = el.get("class") or []

                    # Chapter marker — any <p> whose entire text is a single integer 1–28
                    # (covers style38pt..., style375pt..., chapternumber, and variants)
                    ch_text = el.get_text(strip=True)
                    if (
                        ch_text.isdigit()
                        and 1 <= int(ch_text) <= 28
                        and not el.find("sup", class_=_VERSE_SUP_CLASS)
                        and current_book is not None
                    ):
                        current_chapter = int(ch_text)
                        current_verse = 1
                        continue

                    # Verse text paragraph
                    if current_book is None or current_chapter is None:
                        continue
                    if not self._in_scope(current_book, current_chapter):
                        continue
                    if not (set(classes) & _VERSE_P_CLASSES):
                        continue

                    # Poetry line break — insert newline before this continuation
                    is_poetry = bool(set(classes) & _POETRY_P_CLASSES)
                    if is_poetry and current_verse is not None:
                        ch_data = raw.get(current_book, {}).get(current_chapter, {})
                        if current_verse in ch_data:
                            ch_data[current_verse] += "\n"

                    current_verse = _parse_verse_para(
                        el, current_book, current_chapter, current_verse, raw, ednref_map
                    )

    def _in_scope(self, book: str, chapter: int) -> bool:
        if not self.sample_only:
            return True
        return (book, chapter) in self.sample_chapters


# ── Module-level helpers ──────────────────────────────────────────────────── #

def _get_spine(zf: zipfile.ZipFile) -> list[str]:
    """Return ordered HTML file paths from the EPUB spine."""
    container_xml = zf.read("META-INF/container.xml").decode("utf-8")
    root = ElementTree.fromstring(container_xml)
    ns_c = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
    rootfile_el = root.find(".//c:rootfile", ns_c)
    if rootfile_el is None:
        raise ValueError("Cannot find rootfile in META-INF/container.xml")
    opf_path = rootfile_el.get("full-path", "content.opf")
    opf_dir = opf_path.rsplit("/", 1)[0] + "/" if "/" in opf_path else ""

    opf_xml = zf.read(opf_path).decode("utf-8")
    opf_root = ElementTree.fromstring(opf_xml)
    ns_opf = {"opf": "http://www.idpf.org/2007/opf"}

    id_to_href: dict[str, str] = {}
    for item in opf_root.findall(".//opf:manifest/opf:item", ns_opf):
        item_id = item.get("id")
        href = item.get("href")
        media_type = item.get("media-type", "")
        if item_id and href and "html" in media_type:
            id_to_href[item_id] = opf_dir + href

    paths: list[str] = []
    for itemref in opf_root.findall(".//opf:spine/opf:itemref", ns_opf):
        idref = itemref.get("idref")
        if idref and idref in id_to_href:
            paths.append(id_to_href[idref])
    return paths


def _detect_book(h1: Tag) -> Optional[str]:
    """Return canonical book name if h1 is a NT book heading, else None."""
    raw = h1.get_text(" ", strip=True)
    # Remove all parenthetical expressions (Greek subtitle, "(ACCORDING TO)", etc.)
    # This also eliminates mixed Latin chars inside Greek text (e.g. "ΚΟΛOΣΣΑΕΙΣ")
    cleaned = re.sub(r"\([^)]*\)", " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().upper()
    # Strip gospel title prefix
    cleaned = re.sub(r"^ACCORDING TO\s+", "", cleaned)
    return _EOB_TITLE_TO_BOOK.get(cleaned)


def _collect_inline_text(elem: Tag) -> str:
    """Collect text from an inline element, skipping endnote-ref anchors."""
    parts: list[str] = []
    for child in elem.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            if child.name == "a" and str(child.get("id", "")).startswith("_ednref"):
                continue
            parts.append(_collect_inline_text(child))
    return " ".join(" ".join(parts).split())


def _parse_verse_para(
    p: Tag,
    book: str,
    chapter: int,
    current_verse: Optional[int],
    raw: dict[str, dict[int, dict[int, str]]],
    ednref_map: Optional[dict[int, tuple[str, int, int]]] = None,
) -> Optional[int]:
    """
    Parse verse text from a single paragraph into raw accumulator.
    Returns the updated current_verse number.

    Uses recursive tree walk so verse-number <sup> markers inside nested
    <span> wrappers (e.g. <span class="calibre27">) are not missed.
    """
    return _walk(p, current_verse, book, chapter, raw, ednref_map)


def _walk(
    node: Tag,
    current_verse: Optional[int],
    book: str,
    chapter: int,
    raw: dict[str, dict[int, dict[int, str]]],
    ednref_map: Optional[dict[int, tuple[str, int, int]]] = None,
) -> Optional[int]:
    """Depth-first traversal of a paragraph node, collecting verse text."""
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if text.strip() and current_verse is not None:
                _add_text(raw, book, chapter, current_verse, text)

        elif isinstance(child, Tag):
            # Endnote reference anchor — record mapping and emit inline marker
            if child.name == "a" and (child.get("id") or "").startswith("_ednref"):
                if current_verse is not None:
                    if ednref_map is not None:
                        try:
                            n = int(child["id"][7:])  # "_ednref1003" → 1003
                            ednref_map[n] = (book, chapter, current_verse)
                        except (ValueError, KeyError):
                            pass
                    marker = (
                        f'<sup class="nt-fn">[[{book} {chapter} — EOB Notes#^v{current_verse}|†]]</sup>'
                    )
                    _add_text(raw, book, chapter, current_verse, marker)

            # Verse-number superscript — advance counter (don't recurse)
            elif child.name == "sup" and _VERSE_SUP_CLASS in (child.get("class") or []):
                sup_text = child.get_text(strip=True)
                if sup_text.isdigit():
                    current_verse = int(sup_text)

            # Italic — wrap with Markdown markers
            elif child.name in ("i", "em") and current_verse is not None:
                inline = _collect_inline_text(child)
                if inline:
                    _add_text(raw, book, chapter, current_verse, f"*{inline}*")

            # Bold — wrap with Markdown markers
            elif child.name in ("b", "strong") and current_verse is not None:
                inline = _collect_inline_text(child)
                if inline:
                    _add_text(raw, book, chapter, current_verse, f"**{inline}**")

            # Any other inline element (span, etc.) — recurse
            else:
                current_verse = _walk(child, current_verse, book, chapter, raw, ednref_map)

    return current_verse


def _add_text(
    raw: dict[str, dict[int, dict[int, str]]],
    book: str,
    chapter: int,
    verse: int,
    text: str,
) -> None:
    # Normalize internal whitespace (newlines → space, collapse runs)
    text = " ".join(text.split())
    if not text:
        return
    raw.setdefault(book, {}).setdefault(chapter, {})
    existing = raw[book][chapter].get(verse, "")
    raw[book][chapter][verse] = (existing + " " + text).strip() if existing else text
