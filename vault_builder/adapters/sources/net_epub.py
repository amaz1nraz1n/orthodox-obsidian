"""
Adapter: NetEpubSource

Reads the NET Bible 2.1 EPUB and yields Chapter objects (verse text) and
ChapterNotes objects (translator's apparatus) for requested chapters.

EPUB structure:
  - Each book: one TOC file (fileN.xhtml) + paired chapter files
  - Chapter file: fileN+chapter.xhtml — contains verse text
  - Notes file:   fileN+chapter_notes.xhtml — contains typed footnotes
  - Book→TOC mapping: parsed from OEBPS/toc.ncx

Note families → ChapterNotes slot mapping:
  tn  (Translator's Note)   → footnotes
  tc  (Text-Critical Note)  → variants
  sn  (Study Note)          → citations
  map (Map Note)            → cross_references

See docs/net-epub-source-structure.md for full structural documentation.
"""

import io
import logging
import re
import zipfile
from typing import Union

from bs4 import BeautifulSoup

from vault_builder.domain.canon import LXX_TO_MT
from vault_builder.domain.models import Chapter, ChapterNotes, StudyNote, Verse

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# NET EPUB book title (from NCX) → vault canonical book name
# --------------------------------------------------------------------------- #
_NET_EPUB_TITLE_TO_VAULT: dict[str, str] = {
    "Genesis":          "Genesis",
    "Exodus":           "Exodus",
    "Leviticus":        "Leviticus",
    "Numbers":          "Numbers",
    "Deuteronomy":      "Deuteronomy",
    "Joshua":           "Joshua",
    "Judges":           "Judges",
    "Ruth":             "Ruth",
    "1 Samuel":         "I Kingdoms",
    "2 Samuel":         "II Kingdoms",
    "1 Kings":          "III Kingdoms",
    "2 Kings":          "IV Kingdoms",
    "1 Chronicles":     "I Chronicles",
    "2 Chronicles":     "II Chronicles",
    "Ezra":             "Ezra",
    "Nehemiah":         "Nehemiah",
    "Esther":           "Esther",
    "Job":              "Job",
    "Psalms":           "Psalms",
    "Proverbs":         "Proverbs",
    "Ecclesiastes":     "Ecclesiastes",
    "Song of Solomon":  "Song of Solomon",
    "Isaiah":           "Isaiah",
    "Jeremiah":         "Jeremiah",
    "Lamentations":     "Lamentations",
    "Ezekiel":          "Ezekiel",
    "Daniel":           "Daniel",
    "Hosea":            "Hosea",
    "Joel":             "Joel",
    "Amos":             "Amos",
    "Obadiah":          "Obadiah",
    "Jonah":            "Jonah",
    "Micah":            "Micah",
    "Nahum":            "Nahum",
    "Habakkuk":         "Habakkuk",
    "Zephaniah":        "Zephaniah",
    "Haggai":           "Haggai",
    "Zechariah":        "Zechariah",
    "Malachi":          "Malachi",
    "Matthew":          "Matthew",
    "Mark":             "Mark",
    "Luke":             "Luke",
    "John":             "John",
    "Acts":             "Acts",
    "Romans":           "Romans",
    "1 Corinthians":    "I Corinthians",
    "2 Corinthians":    "II Corinthians",
    "Galatians":        "Galatians",
    "Ephesians":        "Ephesians",
    "Philippians":      "Philippians",
    "Colossians":       "Colossians",
    "1 Thessalonians":  "I Thessalonians",
    "2 Thessalonians":  "II Thessalonians",
    "1 Timothy":        "I Timothy",
    "2 Timothy":        "II Timothy",
    "Titus":            "Titus",
    "Philemon":         "Philemon",
    "Hebrews":          "Hebrews",
    "James":            "James",
    "1 Peter":          "I Peter",
    "2 Peter":          "II Peter",
    "1 John":           "I John",
    "2 John":           "II John",
    "3 John":           "III John",
    "Jude":             "Jude",
    "Revelation":       "Revelation",
}

# Inverse map: vault canonical name → NCX book name (for file lookups)
_VAULT_TO_NET_EPUB_TITLE: dict[str, str] = {v: k for k, v in _NET_EPUB_TITLE_TO_VAULT.items()}

# Verse-text paragraph classes to process (skip paragraphtitle, headers, etc.)
_VERSE_PARA_CLASSES = {"bodytext", "poetry", "bodyblock", "otpoetry"}

def _html_to_markdown(tag) -> str:
    """
    Convert a BeautifulSoup tag's content to Markdown text.

    Rules:
      <i>text</i>          → _text_
      <b>text</b>          → **text**  (type-marker <b> already extracted before call)
      <span class="greek">, <span class="hebrew">, <span class="translit">
                           → unwrapped (Unicode content kept as-is)
      All other tags       → get_text() fallback (content preserved, tags dropped)
    """
    parts: list[str] = []
    for node in tag.children:
        if not hasattr(node, "name") or node.name is None:
            # NavigableString
            parts.append(str(node))
        elif node.name == "i":
            inner = node.get_text()
            parts.append(f"_{inner}_" if inner.strip() else inner)
        elif node.name == "b":
            inner = node.get_text()
            parts.append(f"**{inner}**" if inner.strip() else inner)
        elif node.name == "span":
            # Greek, Hebrew, translit — content is already Unicode; just unwrap
            parts.append(node.get_text())
        else:
            parts.append(node.get_text())
    return "".join(parts)


# Note type bold markers → ChapterNotes slot names
_NOTE_TYPE_TO_SLOT = {
    "tn":  "translator_notes",
    "tc":  "variants",
    "sn":  "footnotes",
    "map": "cross_references",
}

# Inline note marker symbols and CSS classes (tc > tn > sn precedence)
_NET_NOTE_MARKER: dict[str, tuple[str, str]] = {
    "tc": ("\u2021", "nt-tc"),
    "tn": ("*",      "nt-tn"),
    "sn": ("\u2020", "nt-fn"),
}


class NetEpubSource:
    """
    Reads the NET Bible 2.1 EPUB and returns Chapter / ChapterNotes per request.

    epub_path may be a file path string or a file-like object (BytesIO), which
    allows in-memory test fixtures to be used without touching disk.
    """

    def __init__(self, epub_path: Union[str, "io.BytesIO"]) -> None:
        self._epub = zipfile.ZipFile(epub_path)
        self._toc: dict[str, int] = self._parse_ncx()  # vault_book_name → TOC file num

    # ── Public interface ───────────────────────────────────────────────────────

    def read_chapter(self, book: str, chapter: int) -> Chapter:
        """Return a Chapter object with verse text and pericope headings."""
        file_num = self._chapter_file_num(book, chapter)
        html = self._read_xhtml(file_num)
        try:
            notes_html = self._read_notes_xhtml(file_num)
            note_type_map = self._build_note_type_map(notes_html)
        except Exception:
            note_type_map = None
        verse_texts, pericopes = self._parse_chapter(html, note_type_map, book, chapter)

        result = Chapter(book=book, number=chapter, pericopes=pericopes)
        for v_num, text in verse_texts.items():
            result.verses[v_num] = Verse(number=v_num, text=text)
        return result

    def read_notes(self, book: str, chapter: int) -> ChapterNotes:
        """Return a ChapterNotes object for the given book + chapter."""
        file_num = self._chapter_file_num(book, chapter)
        text_html = self._read_xhtml(file_num)
        notes_html = self._read_notes_xhtml(file_num)

        note_verse_map = self._build_note_verse_map(text_html)
        return self._parse_notes(notes_html, book, chapter, note_verse_map)

    # ── NCX parsing ───────────────────────────────────────────────────────────

    def _parse_ncx(self) -> dict[str, int]:
        """Parse toc.ncx → {vault_book_name: TOC_file_num}."""
        raw = self._epub.read("OEBPS/toc.ncx").decode("utf-8")
        soup = BeautifulSoup(raw, "xml")
        result: dict[str, int] = {}
        for navpoint in soup.find_all("navPoint"):
            content_tag = navpoint.find("content")
            if content_tag is None:
                continue
            src = content_tag.get("src", "")
            m = re.match(r"file(\d+)\.xhtml$", src)
            if not m:
                continue
            file_num = int(m.group(1))
            text_tag = navpoint.find("text")
            if text_tag is None:
                continue
            ncx_name = text_tag.get_text().strip()
            vault_name = _NET_EPUB_TITLE_TO_VAULT.get(ncx_name)
            if vault_name:
                result[vault_name] = file_num
        return result

    # ── File number resolution ─────────────────────────────────────────────────

    def _chapter_file_num(self, book: str, chapter: int) -> int:
        """Return the file number for a given vault book name + LXX chapter."""
        toc_num = self._toc[book]
        if book == "Psalms":
            # NET uses MT numbering; convert LXX chapter → MT for file lookup
            mt_chapter = LXX_TO_MT.get(chapter, chapter)
            if mt_chapter is None:
                raise ValueError(f"Psalm {chapter} (LXX) has no MT equivalent")
            return toc_num + mt_chapter
        return toc_num + chapter

    # ── EPUB file reading ──────────────────────────────────────────────────────

    def _read_xhtml(self, file_num: int) -> str:
        return self._epub.read(f"OEBPS/file{file_num}.xhtml").decode("utf-8")

    def _read_notes_xhtml(self, file_num: int) -> str:
        return self._epub.read(f"OEBPS/file{file_num}_notes.xhtml").decode("utf-8")

    # ── Note type map ──────────────────────────────────────────────────────────

    def _build_note_type_map(self, notes_html: str) -> dict[str, str]:
        """Parse notes HTML → {note_id: primary_type} using tc > tn > sn precedence."""
        _PRECEDENCE = {"tc": 0, "tn": 1, "sn": 2}
        soup = BeautifulSoup(notes_html, "xml")
        result: dict[str, str] = {}
        for note_para in soup.find_all("p", id=True):
            note_id = note_para.get("id", "")
            if not note_id.startswith("n"):
                continue
            best_type: str | None = None
            best_rank = 999
            for typed_para in note_para.find_all("p", recursive=False):
                bold = typed_para.find("b")
                if bold is None:
                    continue
                t = bold.get_text().strip()
                rank = _PRECEDENCE.get(t, 999)
                if rank < best_rank:
                    best_rank = rank
                    best_type = t
            if best_type:
                result[note_id] = best_type
        return result

    # ── Verse text extraction ──────────────────────────────────────────────────

    def _parse_chapter(
        self,
        html: str,
        note_type_map: dict[str, str] | None = None,
        book: str | None = None,
        chapter: int | None = None,
    ) -> tuple[dict[int, str], dict[int, str]]:
        """
        Parse chapter text HTML → (verse_texts, pericopes).

        verse_texts: {verse_num: clean_text}
        pericopes:   {first_verse_num: pericope_title}

        Algorithm:
          1. Strip all <sup> elements (cleans note refs AND paragraphtitle digit artifacts)
          2. Walk paragraphs in document order:
             - paragraphtitle → stash as pending pericope title (last wins if consecutive)
             - bodytext/poetry → associate pending title with first verse span found
          3. Replace verse spans with sentinels; join paragraph texts; split on sentinels
        """
        soup = BeautifulSoup(html, "xml")
        body = soup.find("body")
        if body is None:
            return {}, {}

        _use_markers = note_type_map is not None and book is not None and chapter is not None
        for sup in body.find_all("sup"):
            if _use_markers:
                a_child = sup.find("a", recursive=False)
                if a_child is not None:
                    note_id = a_child.get("id", "")
                    if note_id.startswith("n"):
                        sup.replace_with(f"__NOTE_{note_id}__")
                        continue
            sup.decompose()

        def _para_classes(para) -> set:
            cls = para.get("class") or []
            return set(cls.split() if isinstance(cls, str) else cls)

        # Pass 1: pericope title → first verse of that pericope
        pericopes: dict[int, str] = {}
        pending_title: str | None = None
        for para in body.find_all("p"):
            classes = _para_classes(para)
            if "paragraphtitle" in classes:
                title = re.sub(r"\s+", " ", para.get_text(" ", strip=True)).strip()
                # Suppress bare "Psalm N" headings — these are MT chapter titles
                # that bleed in from NET's numbering; the LXX chapter identity is
                # already encoded in the hub filename and frontmatter.
                if title and not re.match(r"^Psalm \d+$", title):
                    pending_title = title  # last consecutive heading wins
            elif classes & _VERSE_PARA_CLASSES and pending_title is not None:
                span = para.find("span", class_="verse")
                if span:
                    try:
                        verse_num = int(span.get_text().split(":")[1])
                        pericopes[verse_num] = pending_title
                        pending_title = None
                    except (IndexError, ValueError):
                        pass

        # Pass 2: replace verse spans with sentinels; collect verse paragraph texts
        for span in body.find_all("span", class_="verse"):
            ref = span.get_text()
            try:
                verse_num = int(ref.split(":")[1])
            except (IndexError, ValueError):
                continue
            span.replace_with(f"__VERSE_{verse_num}__")

        parts = []
        for para in body.find_all("p"):
            classes = _para_classes(para)
            if classes & _VERSE_PARA_CLASSES:
                text = para.get_text(" ", strip=True)
                if text:
                    parts.append(text)

        combined = " ".join(parts)
        segments = re.split(r"__VERSE_(\d+)__", combined)

        verse_texts: dict[int, str] = {}
        for i in range(1, len(segments), 2):
            try:
                verse_num = int(segments[i])
            except ValueError:
                continue
            text = segments[i + 1] if i + 1 < len(segments) else ""
            text = re.sub(r"\s+", " ", text).strip()
            text = re.sub(r"\s+([,;:.!?])", r"\1", text)
            if _use_markers:
                def _resolve(m: re.Match) -> str:
                    nid = m.group(1)
                    ptype = note_type_map.get(nid)  # type: ignore[union-attr]
                    if not ptype:
                        return ""
                    sym, cls = _NET_NOTE_MARKER.get(ptype, ("", ""))
                    if not sym:
                        return ""
                    return f'<sup class="{cls}">[[{book} {chapter} — NET Notes#^v{verse_num}|{sym}]]</sup>'
                text = re.sub(r"__NOTE_(n\d+)__", _resolve, text)
            else:
                text = re.sub(r"__NOTE_(n\d+)__", "", text)
            if text:
                verse_texts[verse_num] = text

        return verse_texts, pericopes

    # ── Note→verse attribution ────────────────────────────────────────────────

    def _build_note_verse_map(self, html: str) -> dict[str, int]:
        """
        Parse text HTML → {note_anchor_id: verse_num}.

        Walks paragraphs in document order:
          - paragraphtitle / psasuper → note anchors assigned to verse 0 (intro)
          - bodytext / poetry / bodyblock / otpoetry → note anchors assigned to
            the current verse (tracked via <span class="verse"> markers)
        """
        soup = BeautifulSoup(html, "xml")
        body = soup.find("body")
        if body is None:
            return {}

        note_verse: dict[str, int] = {}
        current_verse: int | None = None
        _INTRO_CLASSES = {"paragraphtitle", "psasuper"}

        for para in body.find_all("p"):
            classes = para.get("class") or []
            if isinstance(classes, str):
                classes = [classes]
            class_set = set(classes)

            if class_set & _INTRO_CLASSES:
                for elem in para.descendants:
                    if not hasattr(elem, "name") or elem.name is None:
                        continue
                    if elem.name == "a":
                        anchor_id = elem.get("id", "")
                        if anchor_id.startswith("n"):
                            note_verse[anchor_id] = 0
            elif class_set & _VERSE_PARA_CLASSES:
                for elem in para.descendants:
                    if not hasattr(elem, "name") or elem.name is None:
                        continue
                    if elem.name == "span" and "verse" in (elem.get("class") or []):
                        ref = elem.get_text()
                        try:
                            current_verse = int(ref.split(":")[1])
                        except (IndexError, ValueError):
                            pass
                    elif elem.name == "a":
                        anchor_id = elem.get("id", "")
                        if anchor_id.startswith("n") and current_verse is not None:
                            note_verse[anchor_id] = current_verse

        return note_verse

    # ── Notes file parsing ────────────────────────────────────────────────────

    def _parse_notes(
        self,
        html: str,
        book: str,
        chapter: int,
        note_verse_map: dict[str, int],
    ) -> ChapterNotes:
        """Parse notes HTML → ChapterNotes using note_verse_map for attribution."""
        soup = BeautifulSoup(html, "xml")
        notes_obj = ChapterNotes(book=book, chapter=chapter, source="NET")

        for note_para in soup.find_all("p", id=True):
            note_id = note_para.get("id", "")
            if not note_id.startswith("n"):
                continue

            verse_num = note_verse_map.get(note_id)
            if verse_num is None:
                logger.debug("Note %s has no verse mapping — skipped", note_id)
                continue

            ref_str = "intro" if verse_num == 0 else f"{chapter}:{verse_num}"

            for typed_para in note_para.find_all("p", recursive=False):
                bold = typed_para.find("b")
                if bold is None:
                    continue
                note_type = bold.get_text().strip()
                slot = _NOTE_TYPE_TO_SLOT.get(note_type)
                if slot is None:
                    continue

                bold.extract()
                content = _html_to_markdown(typed_para)
                content = re.sub(r"\s+", " ", content).strip()

                note = StudyNote(
                    verse_number=verse_num,
                    ref_str=ref_str,
                    content=content,
                )
                getattr(notes_obj, slot).append(note)

        return notes_obj
