"""
Adapter: ApostolicFathersEpubSource

Reads Holmes, *The Apostolic Fathers* (3rd ed., Baker Academic, 2007) EPUB
and yields (Chapter, ChapterNotes) pairs for each document chapter.

EPUB structure
--------------
- Chapter marker : <p class="noindent1"> containing <span class="dropcap">N</span>
- Verse marker   : <span class="sup">N</span> inline within chapter paragraph
- Footnote (multi-verse) : <p class="noindenta"> — text like
    "4.1–6 Gen. 4:3–8.  4.8 Cf. Gen. 27:41–28:5.  4.9 Cf. Gen. 37."
- Footnote (single-verse): <p class="noindent1"> without dropcap, starting with
    "N.M word note_text" — inline footnote for one verse
- Section heading: <p class="centera"> — skipped

Scripture cross-references in footnotes are converted to vault wikilinks:
  "Cf. Gen. 4:3–8"  →  "Cf. [[Genesis 4#v3|Gen. 4:3–8]]"
  "Acts 20:35"      →  "[[Acts 20#v35|Acts 20:35]]"
  "Gen. 37"         →  "[[Genesis 37|Gen. 37]]"

Psalm numbers: the Apostolic Fathers cite the LXX Psalter, which matches the
vault's primary (LXX) Psalm numbering — no offset adjustment needed.

Phase 1 documents (14): 1 Clement, 2 Clement, all 7 Ignatius letters,
Polycarp to the Philippians, Martyrdom of Polycarp, Didache, Epistle of
Barnabas, Epistle to Diognetus.

Deferred: Shepherd of Hermas (three-book structure in one file) and Papias
Fragments (brief excerpts, no chapter/verse structure).
"""

import re
import warnings
import zipfile
from typing import Iterator, Optional

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from vault_builder.domain.canon import book_file_prefix
from vault_builder.domain.models import Chapter, ChapterNotes, NoteType, StudyNote, Verse

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ---------------------------------------------------------------------------
# Document manifest: (html_file, canonical_name, chapter_count)
# ---------------------------------------------------------------------------

_AF_DOCUMENTS: list[tuple[str, str, int]] = [
    ("text/part0008.html", "1 Clement",                         65),
    ("text/part0010.html", "2 Clement",                         20),
    ("text/part0012.html", "Ignatius to the Ephesians",         21),
    ("text/part0013.html", "Ignatius to the Magnesians",        15),
    ("text/part0014.html", "Ignatius to the Trallians",         13),
    ("text/part0015.html", "Ignatius to the Romans",            10),
    ("text/part0016.html", "Ignatius to the Philippians",       11),
    ("text/part0017.html", "Ignatius to the Smyrnaeans",        13),
    ("text/part0018.html", "Ignatius to Polycarp",               8),
    ("text/part0020.html", "Polycarp to the Philippians",       14),
    ("text/part0022.html", "Martyrdom of Polycarp",             22),
    ("text/part0024.html", "Didache",                           16),
    ("text/part0026.html", "Epistle of Barnabas",               21),
    ("text/part0030.html", "Epistle to Diognetus",              12),
]

# ---------------------------------------------------------------------------
# Scripture abbreviation → vault canonical book name
# ---------------------------------------------------------------------------

_ABBR_TO_BOOK: dict[str, str] = {
    # OT
    "Gen.":     "Genesis",
    "Exod.":    "Exodus",
    "Lev.":     "Leviticus",
    "Num.":     "Numbers",
    "Deut.":    "Deuteronomy",
    "Josh.":    "Joshua",
    "Judg.":    "Judges",
    "Ruth":     "Ruth",
    "1 Sam.":   "I Kingdoms",
    "2 Sam.":   "II Kingdoms",
    "1 Kgs.":   "III Kingdoms",
    "2 Kgs.":   "IV Kingdoms",
    "1 Chr.":   "I Chronicles",
    "2 Chr.":   "II Chronicles",
    "Ezra":     "Ezra",
    "Neh.":     "Nehemiah",
    "Esth.":    "Esther",
    "Job":      "Job",
    "Ps.":      "Psalms",
    "Prov.":    "Proverbs",
    "Eccl.":    "Ecclesiastes",
    "Song":     "Song of Solomon",
    "Isa.":     "Isaiah",
    "Jer.":     "Jeremiah",
    "Lam.":     "Lamentations",
    "Ezek.":    "Ezekiel",
    "Dan.":     "Daniel",
    "Hos.":     "Hosea",
    "Joel":     "Joel",
    "Amos":     "Amos",
    "Obad.":    "Obadiah",
    "Jon.":     "Jonah",
    "Mic.":     "Micah",
    "Nah.":     "Nahum",
    "Hab.":     "Habakkuk",
    "Zeph.":    "Zephaniah",
    "Hag.":     "Haggai",
    "Zech.":    "Zechariah",
    "Mal.":     "Malachi",
    # NT
    "Matt.":    "Matthew",
    "Mark":     "Mark",
    "Luke":     "Luke",
    "John":     "John",
    "Acts":     "Acts",
    "Rom.":     "Romans",
    "1 Cor.":   "I Corinthians",
    "2 Cor.":   "II Corinthians",
    "Gal.":     "Galatians",
    "Eph.":     "Ephesians",
    "Phil.":    "Philippians",
    "Col.":     "Colossians",
    "1 Thess.": "I Thessalonians",
    "2 Thess.": "II Thessalonians",
    "1 Tim.":   "I Timothy",
    "2 Tim.":   "II Timothy",
    "Titus":    "Titus",
    "Phlm.":    "Philemon",
    "Heb.":     "Hebrews",
    "Jas.":     "James",
    "1 Pet.":   "I Peter",
    "2 Pet.":   "II Peter",
    "1 John":   "I John",
    "2 John":   "II John",
    "3 John":   "III John",
    "Jude":     "Jude",
    "Rev.":     "Revelation",
}

# Build regex from abbreviations (longest first to prevent partial matches)
_ABBR_PATTERN = "|".join(
    re.escape(k) for k in sorted(_ABBR_TO_BOOK, key=len, reverse=True)
)
# Matches a Scripture reference like "Gen. 4:3–8" or "Acts 20:35" or "Gen. 37"
# Groups: (1) book abbr, (2) chapter, (3) optional verse, (4) optional range suffix
_SCRIPTURE_REF_RE = re.compile(
    r"(" + _ABBR_PATTERN + r")"
    r"\s+(\d+)"
    r"(?::(\d+))?"
    r"((?:–\d+(?::\d+)?)?)"
)

# Detects a footnote paragraph: starts with "N.M" or "N.M–N" pattern
_NOTE_PARA_START_RE = re.compile(r"^\s*\d+\.\d+")


def _linkify_scripture(text: str) -> str:
    """Replace Scripture abbreviation references in *text* with vault wikilinks."""
    def _replace(m: re.Match) -> str:
        abbr    = m.group(1)
        chapter = m.group(2)
        verse   = m.group(3)
        suffix  = m.group(4)   # e.g. "–8" or "–28:5" or ""
        book    = _ABBR_TO_BOOK[abbr]
        pfx     = book_file_prefix(book)
        label   = m.group(0)   # original text becomes the link label
        if verse:
            return f"[[{pfx} {chapter}#v{verse}|{label}]]"
        else:
            return f"[[{pfx} {chapter}|{label}]]"
    return _SCRIPTURE_REF_RE.sub(_replace, text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_verse_text(p_tag) -> dict[int, str]:
    """
    Parse verse text from a chapter <p> tag.

    The dropcap span is stripped.  Verse 1 is the text before the first
    <span class="sup">.  Each subsequent sup marks a new verse number.
    Returns {verse_num: text}.
    """
    # Remove dropcap — its text is the chapter number, not verse content
    dropcap = p_tag.find("span", class_="dropcap")
    if dropcap:
        dropcap.decompose()

    verses: dict[int, list[str]] = {}
    current_verse = 1
    buf: list[str] = []

    for child in p_tag.children:
        if hasattr(child, "name") and child.name == "span":
            cls = child.get("class", [])
            if "sup" in cls:
                # Flush current verse buffer
                text = " ".join(buf).strip()
                text = re.sub(r"\s+", " ", text)
                if text:
                    verses.setdefault(current_verse, []).append(text)
                current_verse = int(child.get_text(strip=True))
                buf = []
                continue
            # Other spans (italic, bold, etc.) — include their text
            buf.append(child.get_text())
        elif hasattr(child, "get_text"):
            buf.append(child.get_text())
        else:
            buf.append(str(child))

    # Flush last verse
    text = " ".join(buf).strip()
    text = re.sub(r"\s+", " ", text)
    if text:
        verses.setdefault(current_verse, []).append(text)

    return {v: " ".join(parts).strip() for v, parts in verses.items()}


def _parse_footnote_para(raw_text: str, chapter: int) -> dict[int, list[str]]:
    """
    Split a footnote paragraph into per-verse note fragments.

    Format: "4.1–6 Gen. 4:3–8.  4.8 Cf. Gen. 27:41–28:5.  4.9 Cf. Gen. 37."

    Returns {verse_num: [note_text, ...]} where note texts have Scripture
    refs already converted to wikilinks.
    """
    # Pattern: chapter.verse or chapter.verse-verse at start of a segment
    seg_re = re.compile(rf"\b{chapter}\.(\d+)(?:–\d+)?\s+")

    result: dict[int, list[str]] = {}
    last_verse: Optional[int] = None
    last_end = 0

    for m in seg_re.finditer(raw_text):
        if last_verse is not None:
            frag = raw_text[last_end:m.start()].strip().rstrip(".")
            frag = re.sub(r"\s+", " ", frag)
            if frag:
                note_frag = _linkify_scripture(frag)
                result.setdefault(last_verse, []).append(note_frag)
        last_verse = int(m.group(1))
        last_end   = m.end()

    # Flush last fragment
    if last_verse is not None:
        frag = raw_text[last_end:].strip().rstrip(".")
        frag = re.sub(r"\s+", " ", frag)
        if frag:
            note_frag = _linkify_scripture(frag)
            result.setdefault(last_verse, []).append(note_frag)

    return result


# ---------------------------------------------------------------------------
# Public adapter
# ---------------------------------------------------------------------------

class ApostolicFathersEpubSource:
    """
    Yields (Chapter, ChapterNotes) for each document chapter.

    In sample_only mode, only chapters in sample_chapters are yielded.
    sample_chapters: set of (document_name, chapter_num) tuples.
    """

    def __init__(
        self,
        epub_path: str,
        sample_only: bool = True,
        sample_chapters: Optional[set[tuple[str, int]]] = None,
    ) -> None:
        self.epub_path     = epub_path
        self.sample_only   = sample_only
        self.sample_chapters = sample_chapters or set()

    def read_documents(self) -> Iterator[tuple[Chapter, ChapterNotes]]:
        """Yield (Chapter, ChapterNotes) pairs in document/chapter order."""
        with zipfile.ZipFile(self.epub_path) as zf:
            for html_file, doc_name, _chapter_count in _AF_DOCUMENTS:
                yield from self._parse_file(zf, html_file, doc_name)

    def _in_scope(self, doc_name: str, chapter: int) -> bool:
        if not self.sample_only:
            return True
        return (doc_name, chapter) in self.sample_chapters

    def _parse_file(
        self,
        zf: zipfile.ZipFile,
        html_file: str,
        doc_name: str,
    ) -> Iterator[tuple[Chapter, ChapterNotes]]:
        html = zf.read(html_file).decode("utf-8")
        soup = BeautifulSoup(html, "lxml")

        # Collect all <p> elements in document order
        paragraphs = soup.find_all("p")

        current_chapter: Optional[int]         = None
        current_verses:  dict[int, Verse]      = {}
        pending_notes:   dict[int, list[str]]  = {}   # verse → [note_text]

        def _flush() -> Optional[tuple[Chapter, ChapterNotes]]:
            if current_chapter is None or not current_verses:
                return None
            ch_obj = Chapter(book=doc_name, number=current_chapter, verses=current_verses)
            notes_obj = ChapterNotes(book=doc_name, chapter=current_chapter, source="AF")
            for verse_num, frags in pending_notes.items():
                for frag in frags:
                    notes_obj.add_note(
                        NoteType.FOOTNOTE,
                        StudyNote(
                            verse_number=verse_num,
                            ref_str=f"{current_chapter}.{verse_num}",
                            content=frag,
                        ),
                    )
            return ch_obj, notes_obj

        for p in paragraphs:
            cls = p.get("class", [])
            dropcap = p.find("span", class_="dropcap")

            # ── Chapter boundary ────────────────────────────────────────────
            if dropcap and "noindent1" in cls:
                ch_num_text = dropcap.get_text(strip=True)
                if not ch_num_text.isdigit():
                    continue
                ch_num = int(ch_num_text)

                # Flush previous chapter
                result = _flush()
                if result is not None:
                    if self._in_scope(doc_name, result[0].number):
                        yield result

                # Start new chapter
                current_chapter = ch_num
                current_verses  = {}
                pending_notes   = {}

                verse_map = _extract_verse_text(p)
                for v_num, v_text in verse_map.items():
                    if v_text:
                        current_verses[v_num] = Verse(number=v_num, text=v_text)
                continue

            if current_chapter is None:
                continue

            raw_text = p.get_text(separator=" ").strip()
            raw_text = re.sub(r"\s+", " ", raw_text)

            # ── Standard footnote paragraph ─────────────────────────────────
            if "noindenta" in cls:
                frags = _parse_footnote_para(raw_text, current_chapter)
                for v, notes in frags.items():
                    pending_notes.setdefault(v, []).extend(notes)
                continue

            # ── Inline footnote in noindent1 without dropcap ────────────────
            if "noindent1" in cls and not dropcap:
                if _NOTE_PARA_START_RE.match(raw_text):
                    frags = _parse_footnote_para(raw_text, current_chapter)
                    for v, notes in frags.items():
                        pending_notes.setdefault(v, []).extend(notes)
                    continue
                # Otherwise it's a continuation paragraph for this chapter
                # (rare — most chapters fit in one <p>)
                verse_map = _extract_verse_text(p)
                for v_num, v_text in verse_map.items():
                    if v_text and v_num not in current_verses:
                        current_verses[v_num] = Verse(number=v_num, text=v_text)
                continue

            # ── noindent (address / salutation, before chapter 1) ───────────
            if "noindent" in cls and not dropcap:
                # Treat as pre-chapter prose; attach notes to verse 0 if any
                continue

            # ── centera (section heading) ────────────────────────────────────
            # Skip — section headings carry no verse content

        # Flush final chapter
        result = _flush()
        if result is not None and self._in_scope(doc_name, result[0].number):
            yield result
