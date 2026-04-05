"""
Adapter: AlterEpubSource

Reads Robert Alter's "The Hebrew Bible" (3-volume EPUB) and yields domain
Book objects with per-verse text and translator footnotes.

EPUB structure:
  - OPF: OEBPS/content.opf
  - Chapter files: Vol{V}_Pt{P}[a-h]Chapter{NN}.xhtml  (Torah + Prophets)
                   Vol3_Pt{P}_Chapter_{N}.xhtml          (Writings, most)
                   Vol3_Psalm_{N}.xhtml                  (Psalms — GATED)
                   Vol3_Pt10_Ezra_ch{N}.xhtml
                   Vol3_Pt10_Nehemiah_ch{N}.xhtml
                   Vol3_Pt11_Chronicles1_ch{N}.xhtml
                   Vol3_Pt11_Chronicles2_ch{N}.xhtml

Verse markers:
  - Bare <sup>N</sup> inline in prose paragraphs (no footnote)
  - <sup><a href="#fnN" id="rfnN">N</a></sup> (footnote-linked verse)
  - Multiple verses may share one paragraph (literary layout)

Footnotes: <p class="footnote" id="fnN"> after <hr class="footnote_divider"/>
           in the same .xhtml file as the text.

All footnotes route to NoteType.TRANSLATOR.

Divine name: L<small>ORD</small> → LORD (plain text).

Psalms extraction is GATED pending psalter-concordance.json (MT↔LXX mapping).
"""

import logging
import re
import zipfile
from typing import Iterator, Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from vault_builder.domain.models import Book, Chapter, ChapterNotes, NoteType, StudyNote

logger = logging.getLogger(__name__)

# ── Filename → (book, chapter) mapping ───────────────────────────────────────

# Maps filename prefix → canonical vault book name.
# Vol1/Vol2: prefix is everything before "Chapter{NN}.xhtml"
# Vol3: handled by separate regexes below.
_PREFIX_TO_BOOK: dict[str, str] = {
    # Torah
    "Vol1_Pt1":  "Genesis",
    "Vol1_Pt2":  "Exodus",
    "Vol1_Pt3":  "Leviticus",
    "Vol1_Pt4":  "Numbers",
    "Vol1_Pt5":  "Deuteronomy",
    # Prophets
    "Vol2_Pt1":  "Joshua",
    "Vol2_Pt2":  "Judges",
    "Vol2_Pt3":  "I Kingdoms",
    "Vol2_Pt3a": "II Kingdoms",
    "Vol2_Pt4":  "III Kingdoms",
    "Vol2_Pt4a": "IV Kingdoms",
    "Vol2_Pt5":  "Isaiah",
    "Vol2_Pt6":  "Jeremiah",
    "Vol2_Pt7":  "Ezekiel",
    "Vol2_Pt8a": "Hosea",
    "Vol2_Pt8b": "Joel",
    "Vol2_Pt8c": "Amos",
    "Vol2_Pt8d": "Obadiah",
    "Vol2_Pt9a": "Jonah",
    "Vol2_Pt9b": "Micah",
    "Vol2_Pt9c": "Nahum",
    "Vol2_Pt9d": "Habakkuk",
    "Vol2_Pt9e": "Zephaniah",
    "Vol2_Pt9f": "Haggai",
    "Vol2_Pt9g": "Zechariah",
    "Vol2_Pt9h": "Malachi",
    # Writings (Pt2–Pt9)
    "Vol3_Pt2":  "Proverbs",
    "Vol3_Pt3":  "Job",
    "Vol3_Pt4":  "Song of Solomon",
    "Vol3_Pt5":  "Ruth",
    "Vol3_Pt6":  "Lamentations",
    "Vol3_Pt7":  "Ecclesiastes",
    "Vol3_Pt8":  "Esther",
    "Vol3_Pt9":  "Daniel",
}

# Vol1/Vol2 chapter files: prefix + "Chapter" + digits
_VOL12_RE = re.compile(r"^(Vol[12]_Pt\d+[a-h]?)Chapter(\d+)\.xhtml$")

# Vol3 Writings (Pt2–Pt9): prefix + "_Chapter_" + digits
_VOL3_STD_RE = re.compile(r"^(Vol3_Pt[2-9])_Chapter_(\d+)\.xhtml$")

# Vol3 Ezra/Nehemiah/Chronicles
_VOL3_EZRA_RE      = re.compile(r"^Vol3_Pt10_Ezra_ch(\d+)\.xhtml$")
_VOL3_NEHEMIAH_RE  = re.compile(r"^Vol3_Pt10_Nehemiah_ch(\d+)\.xhtml$")
_VOL3_CHRON1_RE    = re.compile(r"^Vol3_Pt11_Chronicles1_ch(\d+)\.xhtml$")
_VOL3_CHRON2_RE    = re.compile(r"^Vol3_Pt11_Chronicles2_ch(\d+)\.xhtml$")

# Psalms: GATED — skip extraction
_PSALM_RE = re.compile(r"^Vol3_Psalm_\d+\.xhtml$")

# Footnote definition: <p class="footnote" id="fnN">
_FN_DEF_RE = re.compile(r"^fn\d+$")

# Inline <sup> text must be a bare integer to count as a verse number
_VERSE_NUM_RE = re.compile(r"^\d+$")


def _filename_to_book_chapter(fname: str) -> Optional[tuple[str, int]]:
    """Return (canonical_book_name, chapter_num) for a spine filename, or None."""
    # Strip OEBPS/ prefix if present
    base = fname.split("/")[-1]

    if _PSALM_RE.match(base):
        return None  # Psalms gated

    m = _VOL12_RE.match(base)
    if m:
        book = _PREFIX_TO_BOOK.get(m.group(1))
        return (book, int(m.group(2))) if book else None

    m = _VOL3_STD_RE.match(base)
    if m:
        book = _PREFIX_TO_BOOK.get(m.group(1))
        return (book, int(m.group(2))) if book else None

    m = _VOL3_EZRA_RE.match(base)
    if m:
        return ("Ezra", int(m.group(1)))

    m = _VOL3_NEHEMIAH_RE.match(base)
    if m:
        return ("Nehemiah", int(m.group(1)))

    m = _VOL3_CHRON1_RE.match(base)
    if m:
        return ("I Chronicles", int(m.group(1)))

    m = _VOL3_CHRON2_RE.match(base)
    if m:
        return ("II Chronicles", int(m.group(1)))

    return None


# ── HTML cleaning helpers ─────────────────────────────────────────────────────

def _extract_text_clean(node: Tag) -> str:
    """Extract text from a node, rendering small-caps LORD and stripping artifacts."""
    parts: list[str] = []
    _collect_text(node, parts)
    text = "".join(parts)
    # Collapse whitespace
    text = re.sub(r"[ \t\xa0]+", " ", text).strip()
    return text


def _collect_text(node, parts: list[str]) -> None:
    """Recursively collect text, handling <small> → uppercase and stripping spans."""
    if isinstance(node, NavigableString):
        parts.append(str(node))
        return
    if not isinstance(node, Tag):
        return

    tag = node.name

    # <small> children of tetragrammaton: uppercase the text
    if tag == "small":
        parts.append(node.get_text().upper())
        return

    # Strip page-break spans and hide spans entirely
    if tag == "span":
        cls = node.get("class") or []
        if isinstance(cls, str):
            cls = [cls]
        if "hide" in cls:
            return
        epub_type = node.get("epub:type", "")
        if epub_type == "pagebreak" or "right_" in " ".join(cls):
            return
        # Drop-cap span: keep text, strip the span wrapper
        if any(c.startswith("dropcap") for c in cls):
            parts.append(node.get_text())
            return

    for child in node.children:
        _collect_text(child, parts)


# ── Footnote loader ───────────────────────────────────────────────────────────

def _load_footnotes(html: str) -> dict[str, str]:
    """
    Parse one chapter .xhtml and return {fn_id: note_text} for all
    <p class="footnote"> elements after the <hr class="footnote_divider"/>.

    Footnote format:  "N. note text..."  — strip the leading "N. " sigil.
    """
    import warnings
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    soup = BeautifulSoup(html, "lxml")
    result: dict[str, str] = {}

    # Find the divider
    divider = soup.find("hr", class_="footnote_divider")
    if not divider:
        return result

    for sib in divider.find_next_siblings():
        if not isinstance(sib, Tag):
            continue
        cls = sib.get("class") or []
        if isinstance(cls, str):
            cls = [cls]
        if "footnote" not in cls and "footnotei" not in cls:
            continue
        fn_id = sib.get("id", "")
        if not fn_id or not _FN_DEF_RE.match(fn_id):
            continue
        raw = sib.get_text(" ", strip=True)
        # Strip leading "N. " or "N . " sigil (get_text(" ") inserts spaces)
        cleaned = re.sub(r"^\d+\s*\.\s*", "", raw).strip()
        if cleaned:
            result[fn_id] = cleaned

    return result


# ── Verse parser ──────────────────────────────────────────────────────────────

def _parse_verses(html: str) -> tuple[dict[int, str], dict[str, int]]:
    """
    Parse one chapter .xhtml and return:
      verses: {verse_num: text}
      fn_to_verse: {fn_id: verse_num}  — which footnote belongs to which verse

    Walks all prose/poetry paragraphs, splits on inline <sup> verse markers,
    accumulates multi-verse paragraphs correctly.
    """
    import warnings
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    soup = BeautifulSoup(html, "lxml")

    # Classes to skip (chapter headings, book titles, footnote area)
    _SKIP_CLASSES = {"cn", "cn1", "ct", "footnoteh", "footnote", "footnotei"}
    # Classes that carry verse text
    _TEXT_CLASSES = {
        "noindentpb", "noindentp", "noindent", "noindentb", "noindent1", "noindent1b",
        "noindent2b", "indent", "indentb", "center", "centerb",
        "poem2", "poem3", "poem4", "poem4a", "poem4s", "poem5", "poem6", "poem7",
        "poem8", "poem9", "poem10", "poem11", "poem12",
    }

    verses: dict[int, str] = {}
    fn_to_verse: dict[str, int] = {}
    current_verse: Optional[int] = None
    past_divider = False

    for elem in soup.find_all(True):
        if not isinstance(elem, Tag):
            continue

        # Stop at footnote divider
        if elem.name == "hr":
            cls = elem.get("class") or []
            if isinstance(cls, str):
                cls = [cls]
            if "footnote_divider" in cls:
                past_divider = True
                break

        if elem.name != "p" or past_divider:
            continue

        cls = elem.get("class") or []
        if isinstance(cls, str):
            cls = [cls]
        cls_set = set(cls)

        if cls_set & _SKIP_CLASSES:
            continue
        if not (cls_set & _TEXT_CLASSES):
            continue

        # Walk children of this paragraph, splitting on <sup> verse markers
        buf: list[str] = []

        def flush_verse():
            nonlocal current_verse
            if current_verse is not None and buf:
                text = re.sub(r"[ \t\xa0]+", " ", "".join(buf)).strip()
                if text:
                    existing = verses.get(current_verse, "")
                    verses[current_verse] = (existing + " " + text).strip() if existing else text
            buf.clear()

        for child in elem.children:
            if isinstance(child, NavigableString):
                buf.append(str(child))
                continue

            if not isinstance(child, Tag):
                continue

            if child.name == "sup":
                # Could be: bare verse num OR verse num wrapping <a>
                inner = child.get_text().strip()
                if _VERSE_NUM_RE.match(inner):
                    flush_verse()
                    current_verse = int(inner)
                    # Record footnote mapping if <sup> wraps an <a>
                    a = child.find("a", href=True)
                    if a:
                        href = a.get("href", "")
                        fn_id = href.lstrip("#")
                        if fn_id and current_verse is not None:
                            fn_to_verse[fn_id] = current_verse
                else:
                    buf.append(child.get_text())
                continue

            if child.name == "span":
                span_cls = child.get("class") or []
                if isinstance(span_cls, str):
                    span_cls = [span_cls]
                if "hide" in span_cls:
                    continue
                epub_type = child.get("epub:type", "")
                if epub_type == "pagebreak" or any("right_" in c for c in span_cls):
                    continue
                if any(c.startswith("dropcap") for c in span_cls):
                    buf.append(child.get_text())
                    continue
                buf.append(_collect_span_text(child))
                continue

            if child.name == "small":
                buf.append(child.get_text().upper())
                continue

            if child.name == "a":
                href = child.get("href", "")
                # Inline footnote link wrapping a <sup>: already handled via <sup>
                sup = child.find("sup")
                if sup:
                    inner = sup.get_text().strip()
                    if _VERSE_NUM_RE.match(inner):
                        flush_verse()
                        current_verse = int(inner)
                        fn_id = href.lstrip("#")
                        if fn_id and current_verse is not None:
                            fn_to_verse[fn_id] = current_verse
                    continue
                # Word-level anchor (id only, no href content): skip
                if not href:
                    continue
                # Other <a> — collect text
                buf.append(child.get_text())
                continue

            if child.name in ("i", "em"):
                text = child.get_text()
                if text.strip():
                    buf.append(f"*{text}*")
                continue

            if child.name in ("b", "strong"):
                text = child.get_text()
                if text.strip():
                    buf.append(f"**{text}**")
                continue

            # Anything else: collect text
            buf.append(_collect_span_text(child))

        flush_verse()

    return verses, fn_to_verse


def _collect_span_text(node: Tag) -> str:
    """Collect text from a span/inline element, handling nested small-caps."""
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            if child.name == "small":
                parts.append(child.get_text().upper())
            elif child.name in ("i", "em"):
                t = child.get_text()
                parts.append(f"*{t}*" if t.strip() else t)
            elif child.name in ("b", "strong"):
                t = child.get_text()
                parts.append(f"**{t}**" if t.strip() else t)
            else:
                parts.append(_collect_span_text(child))
    return "".join(parts)


# ── Source class ──────────────────────────────────────────────────────────────

class AlterEpubSource:
    """
    Reads Robert Alter's Hebrew Bible EPUB and yields Book domain objects.

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

    def read_intros(self) -> Iterator:
        return iter([])

    def read_text(self) -> Iterator[Book]:
        """Parse the EPUB and yield one Book per canonical OT book."""
        # book → chapter → verse → text
        raw: dict[str, dict[int, dict[int, str]]] = {}

        with zipfile.ZipFile(self.epub_path) as z:
            for fname in self._spine_files(z):
                result = _filename_to_book_chapter(fname.split("/")[-1])
                if result is None:
                    continue
                book_name, ch_num = result
                if self.sample_only and (book_name, ch_num) not in self.sample_chapters:
                    continue
                try:
                    html = z.read(fname).decode("utf-8", errors="ignore")
                except KeyError:
                    logger.warning("Missing spine file: %s", fname)
                    continue
                verses, _ = _parse_verses(html)
                for v_num, text in verses.items():
                    (
                        raw
                        .setdefault(book_name, {})
                        .setdefault(ch_num, {})[v_num]
                    ) = text

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
        """Parse the EPUB and yield ChapterNotes with NoteType.TRANSLATOR notes."""
        with zipfile.ZipFile(self.epub_path) as z:
            for fname in self._spine_files(z):
                result = _filename_to_book_chapter(fname.split("/")[-1])
                if result is None:
                    continue
                book_name, ch_num = result
                if self.sample_only and (book_name, ch_num) not in self.sample_chapters:
                    continue
                try:
                    html = z.read(fname).decode("utf-8", errors="ignore")
                except KeyError:
                    continue
                _, fn_to_verse = _parse_verses(html)
                footnotes = _load_footnotes(html)
                if not footnotes:
                    continue
                notes_obj = ChapterNotes(book=book_name, chapter=ch_num, source="Alter")
                for fn_id, text in footnotes.items():
                    verse_num = fn_to_verse.get(fn_id)
                    if verse_num is None:
                        continue
                    ref = f"{ch_num}:{verse_num}"
                    notes_obj.add_note(
                        NoteType.TRANSLATOR,
                        StudyNote(verse_number=verse_num, ref_str=ref, content=text),
                    )
                if notes_obj.translator_notes:
                    yield notes_obj

    def _spine_files(self, z: zipfile.ZipFile) -> list[str]:
        import warnings
        from bs4 import XMLParsedAsHTMLWarning
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        opf = z.read("OEBPS/content.opf").decode("utf-8", errors="ignore")
        soup = BeautifulSoup(opf, "lxml")
        items = {i.get("id"): i.get("href") for i in soup.find_all("item")}
        return [
            f"OEBPS/{items[r.get('idref')]}"
            for r in soup.find_all("itemref")
            if r.get("idref") in items
        ]
