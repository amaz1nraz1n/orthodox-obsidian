"""
Adapter: OsbEpubSource

Parses the Orthodox Study Bible EPUB and yields domain objects.

  read_text()  → Iterator[Book]         (verse text from main HTML files)
  read_notes() → Iterator[ChapterNotes] (study articles + footnotes)

The EPUB has two distinct note sources:
  Pass A — Inline gray study articles in the main book HTML files
            (<div style="background-color: gray;">)
  Pass B — Per-verse footnotes in OEBPS/study1.html – study11.html
            (<div class="footnotedef">)
"""

import logging
import os
import re
import zipfile
from typing import Any, Iterator, Optional, cast

from bs4 import BeautifulSoup, NavigableString, Tag

from vault_builder.domain.models import (
    Book,
    Chapter,
    ChapterNotes,
    StudyArticle,
    StudyNote,
    Verse,
)
from vault_builder.ports.source import ScriptureSource

logger = logging.getLogger(__name__)

# ── EPUB-specific lookup tables ───────────────────────────────────────────────

# Maps EPUB verse-anchor prefix to vault book name.
# Pattern: {PREFIX}_vchap{chapter}-{verse}
PREFIX_TO_BOOK: dict[str, str] = {
    "Gen": "Genesis", "Exod": "Exodus", "Lev": "Leviticus",
    "Num": "Numbers", "Deut": "Deuteronomy",
    "Josh": "Joshua", "Judg": "Judges", "Ruth": "Ruth",
    "K1gdms": "I Kingdoms", "K2gdms": "II Kingdoms",
    "K3gdms": "III Kingdoms", "K4gdms": "IV Kingdoms",
    "C1hr": "I Chronicles", "C2hr": "II Chronicles",
    "E1sd": "I Esdras", "Ezra": "Ezra", "Neh": "Nehemiah",
    "Tob": "Tobit", "Jdt": "Judith", "Esth": "Esther",
    "M1acc": "I Maccabees", "M2acc": "II Maccabees", "M3acc": "III Maccabees",
    "Ps": "Psalms", "Job": "Job", "Prov": "Proverbs",
    "Eccl": "Ecclesiastes", "Song": "Song of Solomon",
    "Wis": "Wisdom of Solomon", "Sir": "Sirach",
    "Hos": "Hosea", "Amos": "Amos", "Mic": "Micah", "Joel": "Joel",
    "obad": "Obadiah", "Jonah": "Jonah", "Nah": "Nahum",
    "Hab": "Habakkuk", "Zeph": "Zephaniah", "Hag": "Haggai",
    "zech": "Zechariah", "Mal": "Malachi",
    "Isa": "Isaiah", "Jer": "Jeremiah", "Bar": "Baruch",
    "Lam": "Lamentations", "EpJer": "Epistle of Jeremiah",
    "Ezek": "Ezekiel", "Dan": "Daniel",
    "Sus": "Susanna", "Bel": "Bel and the Dragon",
    "Matt": "Matthew", "Mark": "Mark", "Luke": "Luke",
    "John": "John", "Acts": "Acts", "Rom": "Romans",
    "C1or": "I Corinthians", "C2or": "II Corinthians",
    "Gal": "Galatians", "Eph": "Ephesians", "Phil": "Philippians",
    "Col": "Colossians", "T1hess": "I Thessalonians", "T2hess": "II Thessalonians",
    "T1im": "I Timothy", "T2im": "II Timothy",
    "Titus": "Titus", "Phlm": "Philemon", "Heb": "Hebrews",
    "Jas": "James", "P1et": "I Peter", "P2et": "II Peter",
    "J1ohn": "I John", "J2ohn": "II John", "J3ohn": "III John",
    "Jude": "Jude", "Rev": "Revelation",
}

# Maps EPUB HTML filenames (base, no extension, no trailing continuation digit)
# to vault book names.  Continuation files like "Genesis1.html" strip the digit.
HTML_BOOK_MAP: dict[str, str] = {
    "1Chronicles": "I Chronicles", "1Corinthians": "I Corinthians",
    "1Ezra": "I Esdras", "1John": "I John", "1Kingdoms": "I Kingdoms",
    "1Maccabees": "I Maccabees", "1Peter": "I Peter",
    "1Thessalonians": "I Thessalonians", "1Timothy": "I Timothy",
    "2Chronicles": "II Chronicles", "2Corinthians": "II Corinthians",
    "2Ezra": "Ezra", "2John": "II John", "2Kingdoms": "II Kingdoms",
    "2Maccabees": "II Maccabees", "2Peter": "II Peter",
    "2Thessalonians": "II Thessalonians", "2Timothy": "II Timothy",
    "3John": "III John", "3Kingdoms": "III Kingdoms", "3Maccabees": "III Maccabees",
    "4Kingdoms": "IV Kingdoms", "Acts": "Acts", "Amos": "Amos",
    "Baruch": "Baruch", "Colossians": "Colossians", "Daniel": "Daniel",
    "Deuteronomy": "Deuteronomy", "Ecclesiastes": "Ecclesiastes",
    "Ephesians": "Ephesians", "EpistleofJeremiah": "Epistle of Jeremiah",
    "Esther": "Esther", "Exodus": "Exodus", "Ezekiel": "Ezekiel",
    "Galatians": "Galatians", "Genesis": "Genesis", "Habakkuk": "Habakkuk",
    "Haggai": "Haggai", "Hebrews": "Hebrews", "Hosea": "Hosea",
    "Isaiah": "Isaiah", "James": "James", "Jeremiah": "Jeremiah",
    "Job": "Job", "Joel": "Joel", "John": "John", "Jonah": "Jonah",
    "Joshua": "Joshua", "Jude": "Jude", "Judges": "Judges", "Judith": "Judith",
    "Lamentations": "Lamentations", "Leviticus": "Leviticus", "Luke": "Luke",
    "Malachi": "Malachi", "Mark": "Mark", "Matthew": "Matthew",
    "Micah": "Micah", "Nahum": "Nahum", "Nehemiah": "Nehemiah",
    "Numbers": "Numbers", "Obadiah": "Obadiah", "Philemon": "Philemon",
    "Philippians": "Philippians", "Proverbs": "Proverbs", "Psalms": "Psalms",
    "Revelation": "Revelation", "Romans": "Romans", "Ruth": "Ruth",
    "SongofSongs": "Song of Solomon", "Titus": "Titus", "Tobit": "Tobit",
    "WisdomofSirach": "Sirach", "WisdomofSolomon": "Wisdom of Solomon",
    "Zechariah": "Zechariah", "Zephaniah": "Zephaniah",
}

# Paragraph CSS classes that contain verse text; all others are ignored.
_VERSE_P_CLASSES: set[str] = {"chapter1", "rindent", "psalm2"}

_VERSE_ANCHOR_PAT = re.compile(r"^([A-Za-z0-9]+)_vchap(\d+)-(\d+)$")
_VERSE_HREF_PAT = re.compile(r"^(\w+\.html)#\w+_vchap(\d+)-(\d+)")
_REF_STR_PAT = re.compile(r"^(\d+):(\d+)(?:[-–—](\d+))?")  # Support various dash types
_FN_ANCHOR_PAT = re.compile(r"^fn\d+$")

_FOOTNOTE_FILE_TO_TYPE: dict[str, str] = {
    "variant.html":         "variants",
    "x-liturgical.html":    "liturgical",
    "citation.html":        "citations",
    "alternative.html":     "alternatives",
    "translation.html":     "translator_notes",
    "background.html":      "background_notes",
    "crossReference.html":  "cross_references",
}

_NOTE_TYPE_TO_MARKER: dict[str, tuple[str, str]] = {
    "footnotes":        ("†",  "nt-fn"),
    "variants":         ("‡",  "nt-tc"),
    "liturgical":       ("☩", "nt-lit"),
    "citations":        ("¶",  "nt-cit"),
    "alternatives":     ("⁺",  "nt-alt"),
    "translator_notes": ("*",  "nt-tn"),
    "background_notes": ("◦",  "nt-bg"),
    "cross_references": ("§",  "nt-cross"),
}


# ── HTML → Markdown helpers ───────────────────────────────────────────────────

def _footnote_marker_html(href: str, book: str, chapter: int, verse: int) -> str:
    """Return an Obsidian-renderable superscript note marker for an OSB inline footnote link.

    href is the value of the <a href="..."> inside a footnote <sup>.
    Returns empty string if the href does not map to a known note type.
    """
    base = href.split("#")[0]
    if re.match(r"study\d+\.html$", base):
        note_type = "footnotes"
    else:
        note_type = _FOOTNOTE_FILE_TO_TYPE.get(base)
    if note_type is None:
        return ""
    symbol, css_class = _NOTE_TYPE_TO_MARKER.get(note_type, ("", ""))
    if not symbol:
        return ""
    fragment = href.split("#")[1] if "#" in href else ""
    anchor = f"^{fragment}" if fragment else f"^v{verse}"
    return f'<sup class="{css_class}">[[{book} {chapter} — OSB Notes#{anchor}|{symbol}]]</sup>'


def _resolve_html_book(html_filename: str) -> Optional[str]:
    """Map 'Genesis1.html' or '1John.html' to vault book name."""
    base = re.sub(r"\.html$", "", html_filename)
    return HTML_BOOK_MAP.get(base) or HTML_BOOK_MAP.get(
        re.sub(r"(?<=[a-z])\d+$", "", base)
    )


def _verse_href_to_wikilink(href: str, display: str) -> str:
    """Convert 'John.html#John_vchap3-19' to [[John 3#^19|display]]."""
    m = _VERSE_HREF_PAT.match(href)
    if not m:
        return display
    book = _resolve_html_book(m.group(1))
    if not book:
        return display
    ch, v = int(m.group(2)), int(m.group(3))
    return f"[[{book} {ch}#v{v}|{display}]]"


def _elem_to_md(elem: Tag | NavigableString) -> str:
    """Recursively convert a BeautifulSoup element to Markdown."""
    if isinstance(elem, NavigableString):
        return str(elem).replace("\xa0", " ")
    # After the NavigableString check above, pyright knows elem is Tag

    # Skip footnote/marker tags (e.g. <sup>a</sup>)
    if elem.name == "sup" or elem.name == "small":
        text = elem.get_text().strip()
        if len(text) == 1 and text.isalpha():
            return ""

    if elem.name == "a":
        href_raw = elem.get("href", "")
        href = href_raw if isinstance(href_raw, str) else ""
        display = elem.get_text()
        return _verse_href_to_wikilink(href, display)
    if elem.name == "b":
        return f"**{elem.get_text()}**"
    if elem.name == "i":
        return f"*{elem.get_text()}*"
    if elem.name == "br":
        return "\n\n"

    # Handle poetic/indented paragraphs
    md = "".join(_elem_to_md(cast("Tag | NavigableString", c)) for c in elem.children)
    if elem.name == "p":
        cls = set(elem.get("class", []))
        if "rindent" in cls or "poetry" in cls:
            return f"\n> {md.strip()}\n"

    return md


def _footnote_to_md(note_div: Tag) -> str:
    """Convert a <div class='footnotedef'> to Markdown, skipping the verse-ref backlink."""
    parts = []
    found_backlink = False
    for child in note_div.children:
        if not found_backlink and isinstance(child, Tag) and child.name == "a":
            found_backlink = True
            continue
        parts.append(_elem_to_md(cast("Tag | NavigableString", child)))
    text = "".join(parts).strip()
    text = re.sub(r"^ {1,4}", "", text, flags=re.MULTILINE)
    text = re.sub(r"  +", " ", text)
    return text.strip()


def _article_to_md(gray_div: Tag) -> Optional[str]:
    """Convert an inline OSB study article (gray box) to an Obsidian callout."""
    title_text = ""
    body_parts: list[str] = []
    for p in gray_div.find_all("p", recursive=False):
        cls = set(p.get("class", []))
        if "ct" in cls:
            raw = p.get_text(separator="").strip()
            title_text = re.sub(
                r"\s+", " ", re.sub(r"(?<=[A-Z]) (?=[A-Z])", "", raw)
            ).strip()
        else:
            md = "".join(_elem_to_md(c) for c in p.children).strip()
            if md:
                body_parts.append(md)
    if not title_text and not body_parts:
        return None
    title_text = title_text or "Study Article"
    body_text = "\n\n".join(body_parts)
    callout_body = "\n".join(
        ("> " + line) if line.strip() else ">"
        for line in body_text.split("\n")
    )
    return f"> [!note] {title_text}\n{callout_body}"


# ── Source adapter ────────────────────────────────────────────────────────────

class OsbEpubSource(ScriptureSource):
    """Reads the OSB EPUB file and yields domain objects."""

    def __init__(self, epub_path: str, sample_only: bool = False,
                 sample_chapters: Optional[set[tuple[str, int]]] = None):
        self.epub_path = epub_path
        self.sample_only = sample_only
        self.sample_chapters = sample_chapters or set()

    # ── ScriptureSource interface ─────────────────────────────────────────────

    def read_text(self) -> Iterator[Book]:
        """Parse verse text from EPUB main HTML files and yield Book objects."""
        if not os.path.exists(self.epub_path):
            logger.error("EPUB not found: %s", self.epub_path)
            return

        raw: dict[str, dict[int, dict[int, str]]] = {}
        pericopes_raw: dict[str, dict[int, dict[int, str]]] = {}

        with zipfile.ZipFile(self.epub_path, "r") as z:
            spine, manifest, prefix_dir = self._read_spine(z)

            for item_id in spine:
                href = manifest.get(item_id)
                if not href or not href.endswith(".html"):
                    continue
                full_href = os.path.normpath(os.path.join(prefix_dir, href))
                if full_href not in z.namelist():
                    continue

                logger.info("Processing %s...", full_href)
                soup = BeautifulSoup(
                    z.read(full_href).decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_verses(soup, raw)
                self._collect_pericopes(soup, pericopes_raw)

        if self.sample_only and self.sample_chapters:
            raw = self._filter_sample(raw)

        yield from self._raw_to_books(raw, pericopes_raw)

    def read_intros(self) -> Iterator[tuple[str, str]]:
        """Yield (vault_book_name, markdown_content) for each book intro found."""
        if not os.path.exists(self.epub_path):
            logger.error("EPUB not found: %s", self.epub_path)
            return

        with zipfile.ZipFile(self.epub_path, "r") as z:
            spine, manifest, prefix_dir = self._read_spine(z)
            seen_books: set[str] = set()

            for item_id in spine:
                href = manifest.get(item_id)
                if not href or not href.endswith(".html"):
                    continue
                full_href = os.path.normpath(os.path.join(prefix_dir, href))
                if full_href not in z.namelist():
                    continue

                book_name = _resolve_html_book(os.path.basename(full_href))
                if book_name is None or book_name in seen_books:
                    continue

                html = z.read(full_href).decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                intro_div = soup.find("div", id="Intro")
                if intro_div is None:
                    continue

                md = self._intro_to_md(intro_div)
                if md:
                    seen_books.add(book_name)
                    yield book_name, md

    @staticmethod
    def _intro_to_md(intro_div: Tag) -> str:
        """Convert an OSB <div id="Intro"> to Markdown prose."""

        def _elem_text(elem: Tag, skip_class: str | None = None) -> str:
            out: list[str] = []
            for child in elem.children:
                if isinstance(child, NavigableString):
                    out.append(str(child))
                elif not isinstance(child, Tag):
                    continue
                elif child.name == "img":
                    continue
                elif skip_class and skip_class in (child.get("class") or []):
                    continue
                elif child.name == "i":
                    inner = child.get_text()
                    if inner.strip():
                        out.append(f"*{inner.strip()}*")
                else:
                    out.append(_elem_text(child, skip_class))
            return re.sub(r"\s+", " ", " ".join(out)).strip()

        roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
        alpha_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        parts: list[str] = []

        for elem in intro_div.children:
            if not isinstance(elem, Tag):
                continue
            classes = set(elem.get("class") or [])
            if elem.name == "h1" or "title" in classes:
                continue
            if "bookstarttxt" in classes:
                label_span = elem.find("span", class_="bookstart")
                label = label_span.get_text(strip=True) if label_span else ""
                content = _elem_text(elem, skip_class="bookstart")
                if label and content:
                    parts.append(f"**{label}** {content}")
                elif content:
                    parts.append(content)
            elif "bookstart" in classes:
                content = _elem_text(elem)
                if content:
                    parts.append(f"**{content}**")
            elif elem.name == "ol":
                for i, li in enumerate(elem.find_all("li", recursive=False)):
                    sub_ol = li.find("ol")
                    li_parts: list[str] = []
                    for child in li.children:
                        if isinstance(child, NavigableString):
                            li_parts.append(str(child))
                        elif isinstance(child, Tag) and child.name != "ol":
                            li_parts.append(child.get_text())
                    li_text = re.sub(r"\s+", " ", "".join(li_parts)).strip()
                    num = roman[i] if i < len(roman) else str(i + 1)
                    parts.append(f"{num}. {li_text}")
                    if sub_ol:
                        for j, sub_li in enumerate(sub_ol.find_all("li", recursive=False)):
                            sub_text = re.sub(r"\s+", " ", sub_li.get_text(" ", strip=True)).strip()
                            letter = alpha_str[j] if j < len(alpha_str) else str(j + 1)
                            parts.append(f"   {letter}. {sub_text}")

        return "\n\n".join(p for p in parts if p.strip())

    def read_notes(self) -> Iterator[ChapterNotes]:
        """Parse study articles and footnotes from the EPUB and yield ChapterNotes."""
        if not os.path.exists(self.epub_path):
            logger.error("EPUB not found: %s", self.epub_path)
            return

        chapter_content: dict[tuple[str, int], dict[str, Any]] = {}

        with zipfile.ZipFile(self.epub_path, "r") as z:
            spine, manifest, prefix_dir = self._read_spine(z)

            # Build fn→book overrides from main book HTML files.
            # Some files (e.g. Daniel.html) embed multiple canonical books
            # distinguished only by verse-anchor prefix.  Study-note backlinks
            # all point back to the same HTML file, so without this map
            # _collect_footnotes would misattribute Susanna/Bel notes to Daniel.
            fn_book_overrides: dict[str, str] = {}
            for item_id in spine:
                href = manifest.get(item_id)
                if not href or not href.endswith(".html"):
                    continue
                full_href = os.path.normpath(os.path.join(prefix_dir, href))
                if full_href not in z.namelist():
                    continue
                html_soup = BeautifulSoup(
                    z.read(full_href).decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                fn_book_overrides.update(self._build_fn_book_overrides(html_soup))

            # Pass A — inline gray study articles in main book HTML files
            for item_id in spine:
                href = manifest.get(item_id)
                if not href or not href.endswith(".html"):
                    continue
                full_href = os.path.normpath(os.path.join(prefix_dir, href))
                if full_href not in z.namelist():
                    continue
                soup = BeautifulSoup(
                    z.read(full_href).decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_articles(soup, chapter_content)

            # Pass B — per-verse footnotes from studyN.html files
            study_files = sorted(
                f for f in z.namelist()
                if re.match(r"OEBPS/study\d+\.html$", f)
            )
            for sf in study_files:
                logger.info("Processing %s...", sf)
                soup = BeautifulSoup(
                    z.read(sf).decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_footnotes(soup, chapter_content, "footnotes", fn_book_overrides)

            # Pass C — textual variants
            if "OEBPS/variant.html" in z.namelist():
                logger.info("Processing OEBPS/variant.html...")
                soup = BeautifulSoup(
                    z.read("OEBPS/variant.html").decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_footnotes(soup, chapter_content, "variants", fn_book_overrides)

            # Pass D — cross references
            if "OEBPS/crossReference.html" in z.namelist():
                logger.info("Processing OEBPS/crossReference.html...")
                soup = BeautifulSoup(
                    z.read("OEBPS/crossReference.html").decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_footnotes(soup, chapter_content, "cross_references", fn_book_overrides)

            # Pass E — lectionary notes
            if "OEBPS/x-liturgical.html" in z.namelist():
                logger.info("Processing OEBPS/x-liturgical.html...")
                soup = BeautifulSoup(
                    z.read("OEBPS/x-liturgical.html").decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_footnotes(soup, chapter_content, "liturgical", fn_book_overrides)

            # Pass F — patristic citations
            if "OEBPS/citation.html" in z.namelist():
                logger.info("Processing OEBPS/citation.html...")
                soup = BeautifulSoup(
                    z.read("OEBPS/citation.html").decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_footnotes(soup, chapter_content, "citations", fn_book_overrides)

            # Pass G — alternative readings ("Or spirit") → alternatives
            if "OEBPS/alternative.html" in z.namelist():
                logger.info("Processing OEBPS/alternative.html...")
                soup = BeautifulSoup(
                    z.read("OEBPS/alternative.html").decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_footnotes(soup, chapter_content, "alternatives", fn_book_overrides)

            # Pass H — background notes (geographic/historical context) → background_notes
            if "OEBPS/background.html" in z.namelist():
                logger.info("Processing OEBPS/background.html...")
                soup = BeautifulSoup(
                    z.read("OEBPS/background.html").decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_footnotes(soup, chapter_content, "background_notes", fn_book_overrides)

            # Pass I — translation notes ("Greek anathema") → translator_notes
            if "OEBPS/translation.html" in z.namelist():
                logger.info("Processing OEBPS/translation.html...")
                soup = BeautifulSoup(
                    z.read("OEBPS/translation.html").decode("utf-8", errors="ignore"),
                    "html.parser",
                )
                self._collect_footnotes(soup, chapter_content, "translator_notes", fn_book_overrides)

        if self.sample_only and self.sample_chapters:
            chapter_content = {
                k: v for k, v in chapter_content.items()
                if k in self.sample_chapters
            }

        yield from self._content_to_chapter_notes(chapter_content)

    # ── EPUB helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _read_spine(z: zipfile.ZipFile):
        opf_path = next((f for f in z.namelist() if f.endswith(".opf")), None)
        if not opf_path:
            raise RuntimeError("Could not find content.opf in EPUB")
        opf_soup = BeautifulSoup(
            z.read(opf_path).decode("utf-8", errors="ignore"), "xml"
        )
        manifest = {item["id"]: item["href"] for item in opf_soup.find_all("item")}
        spine = [item["idref"] for item in opf_soup.find_all("itemref")]
        prefix_dir = os.path.dirname(opf_path)
        return spine, manifest, prefix_dir

    def _collect_verses(
        self,
        soup: BeautifulSoup,
        raw: dict[str, dict[int, dict[int, str]]],
    ) -> None:
        """Collect verse text by walking all descendants in document order.

        Two layout patterns in the OSB EPUB:
          • Prose books: verse text in <p class="chapter1"> or <p class="rindent">
          • Poetic books (Psalms, Sirach): verse text in <ol class="olstyle"><li>…</li>
            with the first verse anchor on the <ol> itself and subsequent verse anchors
            in <sup> elements inside the list items.
        """
        current_book = current_chapter = current_verse = None
        current_anchor_tag = None
        last_was_drop_cap = False  # track so continuation strips its leading space

        for element in soup.descendants:
            if isinstance(element, Tag):
                id_attr = element.get("id")
                if isinstance(id_attr, str):
                    m = _VERSE_ANCHOR_PAT.match(id_attr)
                    if m:
                        prefix, chap_str, verse_str = m.groups()
                        current_book = PREFIX_TO_BOOK.get(str(prefix), str(prefix))
                        current_chapter = int(chap_str)
                        current_verse = int(verse_str)
                        current_anchor_tag = element
                        last_was_drop_cap = False
                        assert current_book is not None
                        raw.setdefault(current_book, {}).setdefault(
                            current_chapter, {}
                        ).setdefault(current_verse, "")

                if (
                    element.name == "sup"
                    and current_book is not None
                    and current_chapter is not None
                    and current_verse is not None
                ):
                    a_child = element.find("a", recursive=False)
                    if a_child is not None:
                        href_raw = a_child.get("href", "")
                        href = href_raw if isinstance(href_raw, str) else ""
                        marker = _footnote_marker_html(href, current_book, current_chapter, current_verse)
                        if marker:
                            raw[current_book][current_chapter][current_verse] = (
                                raw[current_book][current_chapter][current_verse] + marker
                            )

            elif isinstance(element, NavigableString):
                if not (current_book and current_chapter and current_verse):
                    continue

                p_parent = element.find_parent("p")
                in_verse_p = p_parent is not None and bool(
                    set(p_parent.get("class", [])) & _VERSE_P_CLASSES
                )
                ol_parent = element.find_parent("ol")
                in_verse_ol = (
                    ol_parent is not None
                    and "olstyle" in ol_parent.get("class", [])
                )
                if not in_verse_p and not in_verse_ol:
                    continue

                # Skip text inside inline anchors (e.g. <sup id="...">2</sup>
                # displays the verse number) but NOT block anchors like <ol id="...">
                # whose content IS the verse text.
                if (
                    current_anchor_tag
                    and current_anchor_tag.name not in ("ol", "div", "p")
                    and current_anchor_tag in element.parents
                ):
                    continue

                if element.find_parent(["a", "sup"]) is not None:
                    continue

                is_drop_cap = element.find_parent("span", class_="chbeg") is not None

                raw_text = str(element).replace("†", "").replace("ω", "")
                text = raw_text.strip()

                if text:
                    existing = raw[current_book][current_chapter][current_verse]
                    if not existing:
                        raw[current_book][current_chapter][current_verse] = text
                    elif is_drop_cap or last_was_drop_cap:
                        # drop-cap letter itself, or its continuation — join without space
                        raw[current_book][current_chapter][current_verse] = existing + text
                    else:
                        raw[current_book][current_chapter][current_verse] = existing + " " + text
                    last_was_drop_cap = is_drop_cap

    def _collect_articles(
        self,
        soup: BeautifulSoup,
        chapter_content: dict[tuple[str, int], dict[str, Any]],
    ) -> None:
        for gray_div in soup.find_all(
            "div", style=lambda s: s and "background-color: gray" in s  # type: ignore[arg-type]
        ):
            prev_p = None
            for sib in gray_div.previous_siblings:
                if isinstance(sib, Tag) and sib.name == "p":
                    if set(sib.get("class", [])) & _VERSE_P_CLASSES:
                        prev_p = sib
                    break
            if not prev_p:
                continue
            last_anchor = None
            for tag in prev_p.find_all(id=True):
                if _VERSE_ANCHOR_PAT.match(tag.get("id", "")):
                    last_anchor = tag
            if not last_anchor:
                continue
            m = _VERSE_ANCHOR_PAT.match(last_anchor["id"])
            if m is None:
                continue  # shouldn't happen: we already matched this id above
            prefix, chap_str, _ = m.groups()
            book = PREFIX_TO_BOOK.get(prefix, prefix)
            chapter = int(chap_str)

            md = _article_to_md(gray_div)
            if md:
                key = (book, chapter)
                chapter_content.setdefault(
                    key,
                    {"articles": [], "footnotes": [], "variants": [], "cross_references": [],
                     "liturgical": [], "citations": [],
                     "alternatives": [], "background_notes": [], "translator_notes": []}
                )
                chapter_content[key]["articles"].append(md)

    @staticmethod
    def _collect_pericopes(
        soup: BeautifulSoup,
        pericopes_raw: dict[str, dict[int, dict[int, str]]],
    ) -> None:
        """Collect pericope headings from <p class="sub1"> elements.

        Walks the document in order; when a <p class="sub1"> is found, its
        text becomes the pending title.  The next verse anchor encountered
        (id matching _VERSE_ANCHOR_PAT) claims that title.
        """
        pending_title: str | None = None
        for element in soup.descendants:
            if not isinstance(element, Tag):
                continue
            # Pericope heading
            if element.name == "p" and "sub1" in element.get("class", []):
                title = re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()
                if title:
                    pending_title = title
                continue
            # Verse anchor
            if pending_title is None:
                continue
            id_attr = element.get("id", "")
            if isinstance(id_attr, str):
                m = _VERSE_ANCHOR_PAT.match(id_attr)
                if m:
                    prefix, chap_str, verse_str = m.groups()
                    book = PREFIX_TO_BOOK.get(prefix, prefix)
                    chapter = int(chap_str)
                    verse_num = int(verse_str)
                    pericopes_raw.setdefault(book, {}).setdefault(chapter, {}).setdefault(
                        verse_num, pending_title
                    )
                    pending_title = None

    @staticmethod
    def _build_fn_book_overrides(soup: BeautifulSoup) -> dict[str, str]:
        """Walk an HTML file and map each fn anchor ID → correct book name.

        Needed for files like Daniel.html that embed multiple books (Daniel,
        Susanna, Bel and the Dragon) distinguished only by verse-anchor prefix
        (Dan_vchap, Sus_vchap, Bel_vchap).  Study-note backlinks all point to
        the same HTML file, so _resolve_html_book always returns "Daniel"
        without this override.
        """
        overrides: dict[str, str] = {}
        current_book: Optional[str] = None
        for tag in soup.find_all(True):
            id_val = tag.get("id", "")
            if not isinstance(id_val, str):
                continue
            m = _VERSE_ANCHOR_PAT.match(id_val)
            if m:
                prefix = m.group(1)
                resolved = PREFIX_TO_BOOK.get(prefix)
                if resolved:
                    current_book = resolved
            elif _FN_ANCHOR_PAT.match(id_val) and current_book:
                overrides[id_val] = current_book
        return overrides

    def _collect_footnotes(
        self,
        soup: BeautifulSoup,
        chapter_content: dict[tuple[str, int], dict[str, Any]],
        content_key: str = "footnotes",
        fn_book_overrides: Optional[dict[str, str]] = None,
    ) -> None:
        from vault_builder.domain.canon import BOOK_CHAPTER_COUNT
        _NOTE_CLASSES = {"footnotedef", "footnotedefpara", "footnotepara"}
        for note_div in soup.find_all("div", class_=lambda c: c in _NOTE_CLASSES):
            a_tag = note_div.find("a")
            if not a_tag or not a_tag.get("href"):
                continue
            href = a_tag["href"]
            href_file = href.split("#")[0]
            fn_fragment = href.split("#")[1] if "#" in href else ""
            book = _resolve_html_book(href_file)
            if not book:
                logger.debug("No book mapping for: %s", href_file)
                continue
            # Override book for embedded sub-books (e.g. Susanna/Bel in Daniel.html)
            if fn_book_overrides and fn_fragment in fn_book_overrides:
                book = fn_book_overrides[fn_fragment]
            b_tag = note_div.find("b")
            if not b_tag:
                continue
            ref_str = b_tag.get_text().strip()
            m_ref = _REF_STR_PAT.match(ref_str)
            if not m_ref:
                continue
            chapter = int(m_ref.group(1))
            verse_start = int(m_ref.group(2))
            verse_end_raw = int(m_ref.group(3)) if m_ref.group(3) else None
            # Skip notes whose chapter exceeds the canonical chapter count —
            # these are data errors in the EPUB (e.g. a cross-ref note
            # mislabelled as "Hebrews 22:44").
            max_ch = BOOK_CHAPTER_COUNT.get(book)
            if max_ch is not None and chapter > max_ch:
                logger.warning(
                    "Skipping out-of-range note: %s %d:%d (max chapters: %d)",
                    book, chapter, verse_start, max_ch,
                )
                continue
            if verse_end_raw is not None and verse_end_raw < verse_start:
                # Cross-chapter pericope (e.g. "1:24-3" spans into next chapter).
                # Keep original ref_str for display in the callout body; only
                # verse_end is cleared so anchoring uses the start verse only.
                verse_end = None
            else:
                verse_end = verse_end_raw

            md = _footnote_to_md(note_div)
            if not md:
                continue
            own_id = note_div.get("id", "")
            if not isinstance(own_id, str):
                own_id = ""
            key = (book, chapter)
            chapter_content.setdefault(
                key,
                {"articles": [], "footnotes": [], "variants": [], "cross_references": [],
                 "liturgical": [], "citations": [],
                 "alternatives": [], "background_notes": [], "translator_notes": []}
            )
            chapter_content[key][content_key].append((verse_start, verse_end, ref_str, md, own_id))

    # ── Domain object builders ────────────────────────────────────────────────

    def _filter_sample(
        self, raw: dict[str, dict[int, dict[int, str]]]
    ) -> dict[str, dict[int, dict[int, str]]]:
        return {
            book: {
                ch: vs
                for ch, vs in chaps.items()
                if (book, ch) in self.sample_chapters
            }
            for book, chaps in raw.items()
            if any((book, ch) in self.sample_chapters for ch in chaps)
        }

    @staticmethod
    def _raw_to_books(
        raw: dict[str, dict[int, dict[int, str]]],
        pericopes_raw: dict[str, dict[int, dict[int, str]]] | None = None,
    ) -> Iterator[Book]:
        for book_name, chapters in raw.items():
            book = Book(name=book_name)
            for ch_num, verses in chapters.items():
                ch_pericopes = (pericopes_raw or {}).get(book_name, {}).get(ch_num, {})
                chapter = Chapter(book=book_name, number=ch_num, pericopes=ch_pericopes)
                for v_num, v_text in verses.items():
                    chapter.verses[v_num] = Verse(number=v_num, text=v_text.strip())
                book.chapters[ch_num] = chapter
            yield book

    @staticmethod
    def _content_to_chapter_notes(
        chapter_content: dict[tuple[str, int], dict[str, Any]],
    ) -> Iterator[ChapterNotes]:
        def _dedup(tuples: list[tuple]) -> list[tuple]:
            seen = set()
            out = []
            for t in tuples:
                key = (t[0], t[1], t[3])  # (verse_start, verse_end, md)
                if key not in seen:
                    seen.add(key)
                    out.append(t)
            return out

        for (book, chapter), content in chapter_content.items():
            articles = [
                StudyArticle(title="", content=md)
                for md in content.get("articles", [])
            ]
            footnotes = [
                StudyNote(
                    verse_number=verse_start,
                    ref_str=ref_str,
                    content=md,
                    verse_end=verse_end,
                    anchor_id=own_id or None,
                )
                for verse_start, verse_end, ref_str, md, own_id in _dedup(content.get("footnotes", []))
            ]
            variants = [
                StudyNote(
                    verse_number=verse_start,
                    ref_str=ref_str,
                    content=md,
                    verse_end=verse_end,
                    anchor_id=own_id or None,
                )
                for verse_start, verse_end, ref_str, md, own_id in _dedup(content.get("variants", []))
            ]
            cross_references = [
                StudyNote(
                    verse_number=verse_start,
                    ref_str=ref_str,
                    content=md,
                    verse_end=verse_end,
                    anchor_id=own_id or None,
                )
                for verse_start, verse_end, ref_str, md, own_id in _dedup(content.get("cross_references", []))
            ]
            def _notes_list(key: str) -> list[StudyNote]:
                return [
                    StudyNote(
                        verse_number=vs, ref_str=ref, content=md, verse_end=ve, anchor_id=nid or None,
                    )
                    for vs, ve, ref, md, nid in _dedup(content.get(key, []))
                ]

            liturgical = _notes_list("liturgical")
            citations = _notes_list("citations")
            alternatives = _notes_list("alternatives")
            background_notes = _notes_list("background_notes")
            translator_notes = _notes_list("translator_notes")

            if (articles or footnotes or variants or cross_references or liturgical
                    or citations or alternatives or background_notes or translator_notes):
                yield ChapterNotes(
                    book=book,
                    chapter=chapter,
                    source="OSB",
                    articles=articles,
                    footnotes=footnotes,
                    variants=variants,
                    cross_references=cross_references,
                    liturgical=liturgical,
                    citations=citations,
                    alternatives=alternatives,
                    background_notes=background_notes,
                    translator_notes=translator_notes,
                )
