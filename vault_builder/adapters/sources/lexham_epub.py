"""
Adapter: LexhamEpubSource

Reads the Lexham English Septuagint (LES) EPUB and yields domain Book objects
containing per-verse text for the Orthodox canon OT books.

EPUB structure:
  - 79 XHTML spine files (f1.xhtml – f79.xhtml); f1-f7 are front matter
  - Each content file covers one or more books; all chapters of a book may
    span multiple files (e.g. Genesis: f8 + f9)
  - Book header:   <p class="x1F">  with <a id="{CODE}">
  - Chapter heading: <p class="x15"> with <a id="{CODE}.{N}"> (chapter anchor)
    and <a id="{CODE}.{N}_BibleLXX2_..._{N}_1"> (verse 1 anchor) inside the
    same heading paragraph; pericope title in <i> — skip the text here
  - Verse content paragraphs: classes x12, x13, x16, x17, x31; prose and
    poetic; multiple verses inline, delimited by verse anchor <a> tags
  - Verse 1 span:  <span class="x20"><b>N</b> </span> — chapter/psalm number
    drop-cap; skip
  - Later verse spans: <span class="x21">N </span> — inline verse numbers; skip
  - Footnote markers: <a class="x1B" href="..."><i>a</i></a> — strip entirely
  - Section headers within chapters: <p class="x22"> — skip text (editorial)

Verse anchor ID pattern:
  {CODE}.{chapter}_BibleLXX2_{BookShort}_{chapter}_{verse}
  e.g.  GE.1_BibleLXX2_Ge_1_14   PS.50_BibleLXX2_Ps_50_1

Esdras B (ES2) is split at parse time: ES2 chapters 1-10 map to Ezra 1-10
(no offset); ES2 chapters 11-23 map to Nehemiah 1-13 (offset -10).
ES2 is not in LEXHAM_CODE_TO_BOOK; the chapter-detection blocks handle it
directly.
"""

import logging
import re
import zipfile
from typing import Any, Iterator, Optional, cast

from bs4 import BeautifulSoup

from vault_builder.domain.models import Book, Chapter, ChapterNotes, StudyNote, Verse

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Lexham EPUB book code → canonical vault book name
# Codes not present here are skipped (front matter, alternate texts, out-of-canon)
# --------------------------------------------------------------------------- #
LEXHAM_CODE_TO_BOOK: dict[str, str] = {
    "GE":    "Genesis",
    "EX":    "Exodus",
    "LE":    "Leviticus",
    "NU":    "Numbers",
    "DT":    "Deuteronomy",
    "JOS":   "Joshua",
    "JDG":   "Judges",
    "RU":    "Ruth",
    "KI1":   "I Kingdoms",
    "KI2":   "II Kingdoms",
    "KI3":   "III Kingdoms",
    "KI4":   "IV Kingdoms",
    "CH1":   "I Chronicles",
    "CH2":   "II Chronicles",
    "ES1":   "I Esdras",
    # ES2 (Esdras B) handled separately in _parse_file/_parse_file_notes
    "TOB":   "Tobit",
    "JUD":   "Judith",
    "ES":    "Esther",
    "MAC1":  "I Maccabees",
    "MAC2":  "II Maccabees",
    "MAC3":  "III Maccabees",
    "PS":    "Psalms",
    "PR":    "Proverbs",
    "EC":    "Ecclesiastes",
    "SO":    "Song of Solomon",
    "JOB":   "Job",
    "WIS":   "Wisdom of Solomon",
    "SIR":   "Sirach",
    "BR":    "Baruch",
    "LJE":   "Epistle of Jeremiah",
    "DA":    "Daniel",
    "IS":    "Isaiah",
    "JE":    "Jeremiah",
    "LA":    "Lamentations",
    "EZE":   "Ezekiel",
    "HO":    "Hosea",
    "AM":    "Amos",
    "MIC":   "Micah",
    "JOE":   "Joel",
    "OB":    "Obadiah",
    "JON":   "Jonah",
    "NA":    "Nahum",
    "HAB":   "Habakkuk",
    "ZEP":   "Zephaniah",
    "HAG":   "Haggai",
    "ZEC":   "Zechariah",
    "MAL":   "Malachi",
    # Skipped: DAA (alternate Daniel), EN (Enoch), TOBA (alternate Tobit),
    #          ODE (Odes), PSSOL (Psalms of Solomon), MAC4 (IV Maccabees),
    #          INTRO — see module docstring; ES2 handled via chapter-offset split
}

# Paragraph classes that are headings: process verse anchors but skip their text.
# x15 = chapter heading (also contains verse 1 anchor + pericope title)
# x22 = editorial section heading within a chapter (may contain verse anchor)
_HEADING_P_CLASSES: set[str] = {"x15", "x22"}

# Paragraph classes to skip entirely (no verse anchors, no text to collect)
_SKIP_P_CLASSES: set[str] = {"x1F"}   # book titles — handled by book detection

# Span classes to skip entirely (verse numbers, spacing)
# Space and Space2 are both used for spacing glyphs

# Span classes whose full content should be skipped
_SKIP_SPAN_CLASSES: set[str] = {
    "x20",   # drop-cap chapter/psalm number (bold)
    "x21",   # inline verse numbers (most prose books)
    "x27",   # inline verse numbers (Psalms poetry variant)
    "x2A",   # inline verse numbers (poetic variant)
    "x30",   # inline verse numbers (poetic variant)
    "x37",   # inline verse numbers (Psalms 100+)
    "x38",   # inline verse numbers (poetic variant)
    "Space",  # spacing glyphs (short)
    "Space1", # spacing glyphs (alternate short)
    "Space2", # spacing glyphs (long)
    "x2C",   # alternate inline footnote marker (rare; leaks letter/digit into verse text)
}

# Verse anchor: CODE.chapter_BibleLXX2_BookShort_chapter_verse
# BookShort may include digits and underscores (e.g. "1_Kgdms", "1_Mac", "2_Mac")
# so [\w]+ is used instead of [A-Za-z]+
_VERSE_ANCHOR_RE = re.compile(
    r"^[A-Z0-9]+\.(\d+)_BibleLXX2_[\w]+_\d+_(\d+)$"
)

# Chapter anchor: CODE.N  (no underscores, no BibleLXX2)
_CHAPTER_ANCHOR_RE = re.compile(r"^([A-Z0-9]+)\.(\d+)$")


class LexhamEpubSource:
    """
    Reads the Lexham English Septuagint EPUB and yields Book domain objects.

    In sample_only mode, only chapters listed in sample_chapters are extracted.
    In full mode (sample_only=False), all mapped canonical OT books are extracted.
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
        """Parse the EPUB and yield one Book per canonical OT book."""
        # book_name -> chapter_num -> verse_num -> text
        raw: dict[str, dict[int, dict[int, str]]] = {}
        # book_name -> chapter_num -> after_verse_num -> [marker_text, ...]
        raw_markers: dict[str, dict[int, dict[int, list[str]]]] = {}

        with zipfile.ZipFile(self.epub_path) as z:
            spine_files = self._spine_order(z)
            for fname in spine_files:
                if not fname.endswith(".xhtml"):
                    continue
                html = z.read(f"OEBPS/{fname}").decode("utf-8", errors="ignore")
                self._parse_file(html, raw, raw_markers)

        for book_name, chapters in sorted(raw.items()):
            book = Book(name=book_name)
            for ch_num in sorted(chapters):
                chapter = Chapter(
                    book=book_name,
                    number=ch_num,
                    after_markers=raw_markers.get(book_name, {}).get(ch_num, {}),
                )
                for v_num in sorted(chapters[ch_num]):
                    text = chapters[ch_num][v_num].strip()
                    if text:
                        chapter.verses[v_num] = Verse(number=v_num, text=text)
                if chapter.verses:
                    book.chapters[ch_num] = chapter
            if book.chapters:
                yield book

    # ── Spine ────────────────────────────────────────────────────────────────

    def _spine_order(self, z: zipfile.ZipFile):
        from bs4 import XMLParsedAsHTMLWarning
        import warnings
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        opf = z.read("OEBPS/content.opf").decode("utf-8", errors="ignore")
        soup = BeautifulSoup(opf, "lxml")
        items = {i.get("id"): i.get("href") for i in soup.find_all("item")}
        return [items[r.get("idref")] for r in soup.find_all("itemref") if r.get("idref") in items]

    # ── File parser ──────────────────────────────────────────────────────────

    def _parse_file(
        self,
        html: str,
        raw: dict[str, dict[int, dict[int, str]]],
        raw_markers: dict[str, dict[int, dict[int, list[str]]]],
    ) -> None:
        import warnings
        from bs4 import XMLParsedAsHTMLWarning
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

        soup = BeautifulSoup(html, "lxml")
        paras = soup.find_all("p")

        current_book: Optional[str] = None
        current_chapter: Optional[int] = None
        current_verse: Optional[int] = None

        for para in paras:
            cls_list = para.get("class") or []
            if isinstance(cls_list, str):
                cls_list = [cls_list]
            cls = set(cls_list)

            # Book title — update current book, no verse text
            if "x1F" in cls:
                # Book anchor is inside this paragraph
                for a in para.find_all("a", id=True):
                    code = a["id"].strip()
                    if code in LEXHAM_CODE_TO_BOOK:
                        current_book = LEXHAM_CODE_TO_BOOK[code]
                        current_chapter = None
                        current_verse = None
                    elif code == "ES2":
                        current_book = "Ezra"  # chapter anchors will correct to Nehemiah when ch > 10
                        current_chapter = None
                        current_verse = None
                continue

            # Chapter/section headings — extract anchors only, skip visible text
            if cls & _HEADING_P_CLASSES:
                for a in para.find_all("a", id=True):
                    aid = a["id"].strip()
                    m_ch = _CHAPTER_ANCHOR_RE.match(aid)
                    if m_ch:
                        code, ch_num = m_ch.group(1), int(m_ch.group(2))
                        if code in LEXHAM_CODE_TO_BOOK:
                            current_book = LEXHAM_CODE_TO_BOOK[code]
                            current_chapter = ch_num
                            current_verse = None
                        elif code == "ES2":
                            if ch_num <= 10:
                                current_book, current_chapter = "Ezra", ch_num
                            else:
                                current_book, current_chapter = "Nehemiah", ch_num - 10
                            current_verse = None
                        continue
                    m_v = _VERSE_ANCHOR_RE.match(aid)
                    if m_v:
                        current_verse = int(m_v.group(2))
                continue

            # Skip book-title paragraphs (already handled above)
            if cls & _SKIP_P_CLASSES:
                continue

            # Diapsalma / "Musical interlude" — inter-verse liturgical rubric (x34).
            # Record as an after-marker for the preceding verse; do not collect as verse text.
            if "x34" in cls:
                if current_book and current_chapter is not None and current_verse is not None:
                    if self.sample_only and (current_book, current_chapter) not in self.sample_chapters:
                        continue
                    marker = para.get_text().strip()
                    if marker:
                        (
                            raw_markers
                            .setdefault(current_book, {})
                            .setdefault(current_chapter, {})
                            .setdefault(current_verse, [])
                            .append(marker)
                        )
                continue

            # We have a verse-bearing paragraph
            if current_book is None or current_chapter is None:
                continue
            if self.sample_only and (current_book, current_chapter) not in self.sample_chapters:
                continue

            # Walk children to extract text and verse transitions
            for event in self._walk_para(para):
                if event[0] == "verse_start":
                    current_verse = event[1]
                elif event[0] == "footnote_marker" and current_verse is not None:
                    marker = (
                        f'<sup class="nt-tn">[[{current_book} {current_chapter}'
                        f" \u2014 Lexham Notes#v{current_verse}|*]]</sup>"
                    )
                    raw.setdefault(current_book, {}).setdefault(current_chapter, {})
                    existing = raw[current_book][current_chapter].get(current_verse, "")
                    raw[current_book][current_chapter][current_verse] = (
                        (existing + marker) if existing else marker
                    )
                elif event[0] == "text" and current_verse is not None:
                    text = event[1]
                    raw.setdefault(current_book, {}).setdefault(current_chapter, {})
                    existing = raw[current_book][current_chapter].get(current_verse, "")
                    raw[current_book][current_chapter][current_verse] = (
                        (existing + " " + text) if existing else text
                    )

    # ── Notes extraction ─────────────────────────────────────────────────────

    def read_notes(self) -> Iterator[ChapterNotes]:
        """Parse the EPUB and yield one ChapterNotes per chapter that has footnotes."""
        with zipfile.ZipFile(self.epub_path) as z:
            raw_f79 = z.read("OEBPS/f79.xhtml").decode("utf-8", errors="ignore")
        fn_text: dict[str, str] = self._load_footnote_definitions(raw_f79)

        raw: dict[str, dict[int, dict[int, list[str]]]] = {}

        with zipfile.ZipFile(self.epub_path) as z:
            spine_files = self._spine_order(z)
            for fname in spine_files:
                if not fname.endswith(".xhtml") or fname == "f79.xhtml":
                    continue
                html = z.read(f"OEBPS/{fname}").decode("utf-8", errors="ignore")
                self._parse_file_notes(html, raw, fn_text)

        for book_name, chapters in sorted(raw.items()):
            for ch_num in sorted(chapters):
                notes_obj = ChapterNotes(book=book_name, chapter=ch_num, source="Lexham")
                for verse_num in sorted(chapters[ch_num]):
                    for content in chapters[ch_num][verse_num]:
                        ref = f"{ch_num}:{verse_num}"
                        notes_obj.translator_notes.append(
                            StudyNote(verse_number=verse_num, ref_str=ref, content=content)
                        )
                if notes_obj.translator_notes:
                    yield notes_obj

    @staticmethod
    def _load_footnote_definitions(html: str) -> dict[str, str]:
        """
        Parse f79.xhtml and return {anchor_id: note_text}.

        Each entry is a <p class="List1"> with <a id="FN.N.L_c0_e0">.
        The paragraph text is "{letter}{note_text}" — strip the leading letter sigil.
        Intro footnotes (FN.Roman.N) are included but will never be matched by chapter refs.
        """
        import warnings as _w
        from bs4 import XMLParsedAsHTMLWarning
        _w.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

        soup = BeautifulSoup(html, "lxml")
        result: dict[str, str] = {}
        for p in soup.find_all("p", class_="List1"):
            for a in p.find_all("a", id=True):
                aid = a["id"].strip()
                if not aid.startswith("FN."):
                    continue
                raw_text = p.get_text()
                stripped = re.sub(r"^[a-zA-Z]\s*", "", raw_text).strip()
                if stripped:
                    result[aid] = stripped
        return result

    def _parse_file_notes(
        self,
        html: str,
        raw: dict[str, dict[int, dict[int, list[str]]]],
        fn_text: dict[str, str],
    ) -> None:
        """
        Parse one XHTML spine file, collecting footnote refs per verse.

        Uses the same book/chapter/verse tracking as _parse_file, but instead of
        collecting verse text, collects x1B href anchors and looks them up in fn_text.
        """
        import warnings as _w
        from bs4 import XMLParsedAsHTMLWarning
        _w.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

        soup = BeautifulSoup(html, "lxml")
        paras = soup.find_all("p")

        current_book: Optional[str] = None
        current_chapter: Optional[int] = None
        current_verse: Optional[int] = None

        for para in paras:
            cls_list = para.get("class") or []
            if isinstance(cls_list, str):
                cls_list = [cls_list]
            cls = set(cls_list)

            if "x1F" in cls:
                for a in para.find_all("a", id=True):
                    code = a["id"].strip()
                    if code in LEXHAM_CODE_TO_BOOK:
                        current_book = LEXHAM_CODE_TO_BOOK[code]
                        current_chapter = None
                        current_verse = None
                    elif code == "ES2":
                        current_book = "Ezra"  # chapter anchors will correct to Nehemiah when ch > 10
                        current_chapter = None
                        current_verse = None
                continue

            if cls & _HEADING_P_CLASSES:
                for a in para.find_all("a", id=True):
                    aid = a["id"].strip()
                    m_ch = _CHAPTER_ANCHOR_RE.match(aid)
                    if m_ch:
                        code, ch_num = m_ch.group(1), int(m_ch.group(2))
                        if code in LEXHAM_CODE_TO_BOOK:
                            current_book = LEXHAM_CODE_TO_BOOK[code]
                            current_chapter = ch_num
                            current_verse = None
                        elif code == "ES2":
                            if ch_num <= 10:
                                current_book, current_chapter = "Ezra", ch_num
                            else:
                                current_book, current_chapter = "Nehemiah", ch_num - 10
                            current_verse = None
                        continue
                    m_v = _VERSE_ANCHOR_RE.match(aid)
                    if m_v:
                        current_verse = int(m_v.group(2))
                continue

            if cls & _SKIP_P_CLASSES:
                continue

            if current_book is None or current_chapter is None:
                continue
            if self.sample_only and (current_book, current_chapter) not in self.sample_chapters:
                continue

            for event in self._walk_node_for_notes(para):
                if event[0] == "verse_start":
                    current_verse = event[1]
                elif event[0] == "footnote_ref" and current_verse is not None:
                    anchor_id = event[1]
                    text = fn_text.get(anchor_id)
                    if text:
                        (
                            raw
                            .setdefault(current_book, {})
                            .setdefault(current_chapter, {})
                            .setdefault(current_verse, [])
                            .append(text)
                        )

    def _walk_node_for_notes(self, node: Any) -> Any:
        """
        Recursively yield ("verse_start", verse_num) and ("footnote_ref", anchor_id)
        events from a verse-bearing paragraph, in DOM order.

        Ignores all other content (plain text, spans, etc.).
        """
        if not hasattr(node, "children"):
            return
        for child in node.children:
            if not hasattr(child, "name"):
                continue

            name = child.name

            if name == "a":
                cls = child.get("class") or []
                if isinstance(cls, str):
                    cls = [cls]

                if "x1B" in cls:
                    href = child.get("href", "")
                    if "#" in href:
                        anchor_id = href.split("#", 1)[1]
                        if anchor_id:
                            yield ("footnote_ref", anchor_id)
                    continue

                aid = (child.get("id") or "").strip()
                m = _VERSE_ANCHOR_RE.match(aid)
                if m:
                    yield ("verse_start", int(m.group(2)))
                continue

            yield from self._walk_node_for_notes(child)

    # ── Paragraph walker ─────────────────────────────────────────────────────

    def _walk_para(self, para: Any) -> Any:
        """
        Walk a verse paragraph recursively.
        Yields ("verse_start", verse_num, None) when a verse anchor is found,
        or ("text", None, text_str) for accumulated text between anchors.

        Text fragments within a segment are concatenated without stripping so
        that drop-cap structures like F<span>OR THE END</span> join as
        "FOR THE END" rather than "F OR THE END".  The caller strips the
        final verse text.

        Footnote markers (<a class="x1B">) and verse-number spans are skipped.
        Recurses into spans so nested verse anchors (e.g. inside x32) are found.
        """
        buf: list[str] = []

        def flush():
            if buf:
                text = "".join(buf)
                import re as _re
                text = _re.sub(r"[ \t\xa0]+", " ", text).strip()
                if text:
                    yield ("text", text)
                buf.clear()

        for event in self._walk_node(para):
            if event[0] == "verse_start":
                yield from flush()
                yield event
            elif event[0] == "footnote_marker":
                yield from flush()
                yield event
            else:
                buf.append(cast(str, event[1]))

        yield from flush()

    def _walk_node(self, node: Any) -> Any:
        """Recursively yield ("verse_start", verse_num) or ("text_raw", raw_str)."""
        if not hasattr(node, "children"):
            yield ("text_raw", str(node))
            return
        for child in node.children:
            if not hasattr(child, "name"):
                yield ("text_raw", str(child))
                continue

            name = child.name

            if name == "a":
                cls = child.get("class") or []
                if isinstance(cls, str):
                    cls = [cls]
                if "x1B" in cls:
                    yield ("footnote_marker", None)
                    continue
                aid = (child.get("id") or "").strip()
                m = _VERSE_ANCHOR_RE.match(aid)
                if m:
                    yield ("verse_start", int(m.group(2)))
                # Other <a> tags carry no visible text
                continue

            if name == "span":
                cls = child.get("class") or []
                if isinstance(cls, str):
                    cls = [cls]
                if set(cls) & _SKIP_SPAN_CLASSES:
                    continue  # verse number or spacing span
                # Recurse — may contain nested verse anchors or drop-cap text
                yield from self._walk_node(child)
                continue

            if name in ("i", "em"):
                text = child.get_text()
                if text.strip():
                    yield ("text_raw", f"*{text.strip()}*")
                continue

            if name in ("b", "strong"):
                text = child.get_text()
                if text.strip():
                    yield ("text_raw", f"**{text.strip()}**")
                continue

            # Other inline elements — recurse
            yield from self._walk_node(child)
