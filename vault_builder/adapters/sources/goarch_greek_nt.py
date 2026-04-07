"""
Adapter: GoArchGreekNtSource

Fetches the 1904 Antoniades Patriarchal Text (canonical Greek NT of Eastern Orthodoxy)
from the GOArch Online Chapel at https://onlinechapel.goarch.org/biblegreek/

Replaces GreekNtCsvSource (Robinson-Pierpont Byzantine Majority Text CSV).
Output label and file names are unchanged ("Greek NT") so vault links remain valid.

See docs/goarch-greek-nt-source-structure.md for full HTML structure audit.
"""

import os
import re
import time
import warnings
from typing import Iterator, Optional

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from vault_builder.domain.models import Chapter, ChapterNotes, Verse

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_BASE_URL = "https://onlinechapel.goarch.org/biblegreek/"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class GoArchGreekNtSource:
    """
    Yields (Chapter, ChapterNotes) for each NT book chapter.

    In sample_only mode, only chapters in sample_chapters are yielded.
    sample_chapters: set of (book_canonical_name, chapter_num) tuples.
    """

    # (id, goarch_param, vault_canonical_name, chapter_count)
    BOOKS: list[tuple[int, str, str, int]] = [
        (0,  "Matt",   "Matthew",          28),
        (1,  "Mark",   "Mark",             16),
        (2,  "Luke",   "Luke",             24),
        (3,  "John",   "John",             21),
        (4,  "Acts",   "Acts",             28),
        (5,  "Rom",    "Romans",           16),
        (6,  "1Cor",   "I Corinthians",    16),
        (7,  "2Cor",   "II Corinthians",   13),
        (8,  "Gal",    "Galatians",         6),
        (9,  "Eph",    "Ephesians",         6),
        (10, "Phil",   "Philippians",       4),
        (11, "Col",    "Colossians",        4),
        (12, "1Thess", "I Thessalonians",   5),
        (13, "2Thess", "II Thessalonians",  3),
        (14, "1Tim",   "I Timothy",         6),
        (15, "2Tim",   "II Timothy",        4),
        (16, "Titus",  "Titus",             3),
        (17, "Phlm",   "Philemon",          1),
        (18, "Heb",    "Hebrews",          13),
        (19, "Jas",    "James",             5),
        (20, "1Pet",   "I Peter",           5),
        (21, "2Pet",   "II Peter",          3),
        (22, "1John",  "I John",            5),
        (23, "2John",  "II John",           1),
        (24, "3John",  "III John",          1),
        (25, "Jude",   "Jude",              1),
        (26, "Rev",    "Revelation",       22),
    ]

    def __init__(
        self,
        sample_only: bool = True,
        sample_chapters: Optional[set[tuple[str, int]]] = None,
        rate_limit: float = 1.5,
        cache_dir: str = "source_files/goarch_greek_nt",
    ) -> None:
        self.sample_only = sample_only
        self.sample_chapters = sample_chapters or set()
        self.rate_limit = rate_limit
        self.cache_dir = cache_dir

    def _fetch_book_html(self, book_id: int, book_param: str) -> str:
        """Return HTML for a book, reading from cache or fetching and caching."""
        import urllib.request

        os.makedirs(self.cache_dir, exist_ok=True)
        cache_path = os.path.join(self.cache_dir, f"{book_param}.html")

        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                return f.read()

        url = f"{_BASE_URL}?id={book_id}&book={book_param}&chapter=full"
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8")

        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html)

        return html

    def read_documents(self) -> Iterator[tuple[Chapter, ChapterNotes]]:
        """Fetch each NT book and yield (Chapter, ChapterNotes) pairs."""
        first = True
        for book_id, book_param, book_name, _ch_count in self.BOOKS:
            if self.sample_only and not any(
                b == book_name for b, _ in self.sample_chapters
            ):
                continue

            cached = os.path.exists(os.path.join(self.cache_dir, f"{book_param}.html"))
            if not first and not cached:
                time.sleep(self.rate_limit)
            first = False

            html = self._fetch_book_html(book_id, book_param)
            yield from self._parse_book_html(html, book_name)

    def _parse_book_html(
        self, html: str, book_name: str
    ) -> Iterator[tuple[Chapter, ChapterNotes]]:
        """Parse all chapters from a full-book HTML page."""
        soup = BeautifulSoup(html, "lxml")

        for chapter_div in soup.find_all("div", attrs={"type": "chapter"}):
            osisid = chapter_div.get("osisid", chapter_div.get("osisID", ""))
            # osisID format: "John.1", "Matt.3", etc.
            try:
                ch_num = int(osisid.split(".")[-1])
            except (ValueError, IndexError):
                continue

            if self.sample_only and (book_name, ch_num) not in self.sample_chapters:
                continue

            verse_map = self._parse_chapter(chapter_div)
            if not verse_map:
                continue

            ch = Chapter(book=book_name, number=ch_num)
            for vnum, text in verse_map.items():
                ch.verses[vnum] = Verse(number=vnum, text=text)

            notes = ChapterNotes(book=book_name, chapter=ch_num, source="Greek NT")
            yield ch, notes

    def _parse_chapter(self, chapter_div) -> dict[int, str]:
        """
        Extract {verse_num: text} from a chapter div.

        Handles two patterns (see docs/goarch-greek-nt-source-structure.md):
          A) Linegroup: <p><span class="verse">[N]</span></p> + sibling <div class='linegroup'>
          B) Inline:    <p><span class="verse">[N]</span>text<span...>...</p>
        """
        verses: dict[int, list[str]] = {}
        last_verse: Optional[int] = None

        for child in chapter_div.children:
            if not hasattr(child, "name") or child.name is None:
                continue

            if child.name == "p":
                verse_spans = child.find_all("span", class_="verse")
                if not verse_spans:
                    continue

                current_v: Optional[int] = None
                buf: list[str] = []

                for node in child.children:
                    if (
                        hasattr(node, "name")
                        and node.name == "span"
                        and "verse" in (node.get("class") or [])
                    ):
                        # Flush buffer to current verse before starting next
                        if current_v is not None:
                            text = re.sub(r"\s+", " ", " ".join(buf)).strip()
                            if text:
                                verses.setdefault(current_v, []).append(text)
                        buf = []
                        m = re.match(r"\[(\d+)\]", node.get_text())
                        if m:
                            current_v = int(m.group(1))
                            last_verse = current_v
                    else:
                        t = (
                            node.get_text()
                            if hasattr(node, "get_text")
                            else str(node)
                        )
                        t = t.strip()
                        if t:
                            buf.append(t)

                # Flush remaining buffer
                if current_v is not None:
                    text = re.sub(r"\s+", " ", " ".join(buf)).strip()
                    if text:
                        verses.setdefault(current_v, []).append(text)

            elif child.name == "div" and "linegroup" in (child.get("class") or []):
                if last_verse is not None:
                    for li in child.find_all("div", class_="lineitem"):
                        t = li.get_text(strip=True)
                        if t:
                            verses.setdefault(last_verse, []).append(t)

        return {
            v: re.sub(r"\s+", " ", " ".join(parts)).strip()
            for v, parts in verses.items()
        }
