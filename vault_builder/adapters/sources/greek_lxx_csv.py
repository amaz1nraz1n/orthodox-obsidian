"""
Adapter: GreekLxxCsvSource

Reads the Rahlfs 1935 LXX from a single TSV file (MyBible format) and yields
domain Book objects containing per-verse Greek text for the vault's LXX canon.

Source: LXX-Rahlfs-1935-master (eliranwong), MyBible format
File: 11_end-users_files/MyBible/Bibles/LXX_final_main.csv

Format: tab-separated, NO header row. Columns: book_id, chapter, verse, tagged_text.

Tags stripped before storing:
  <S>digits</S>  — Strong's numbers
  <m>code</m>    — morphology codes

Verse 0 is skipped (used for section headers in Odes, not canonical verse text).

Books not in vault canon are silently skipped:
  232 (Psalms of Solomon), 467 (IV Maccabees), 800 (Odes)

License: CC BY-NC-SA 4.0 (personal study use only)
"""

import logging
import re
from typing import Iterator, Optional

from vault_builder.domain.models import Book, Chapter, Verse

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r'<S>\d+</S>|<m>[^<]+</m>')

_BOOK_ID_TO_NAME: dict[int, str] = {
    10:  "Genesis",
    20:  "Exodus",
    30:  "Leviticus",
    40:  "Numbers",
    50:  "Deuteronomy",
    60:  "Joshua",
    70:  "Judges",
    80:  "Ruth",
    90:  "I Kingdoms",
    100: "II Kingdoms",
    110: "III Kingdoms",
    120: "IV Kingdoms",
    130: "I Chronicles",
    140: "II Chronicles",
    150: "Ezra",
    160: "Nehemiah",
    165: "I Esdras",
    170: "Tobit",
    180: "Judith",
    190: "Esther",
    220: "Job",
    230: "Psalms",
    240: "Proverbs",
    250: "Ecclesiastes",
    260: "Song of Solomon",
    270: "Wisdom of Solomon",
    280: "Sirach",
    290: "Isaiah",
    300: "Jeremiah",
    310: "Lamentations",
    315: "Epistle of Jeremiah",
    320: "Baruch",
    325: "Susanna",
    330: "Ezekiel",
    340: "Daniel",
    345: "Bel and the Dragon",
    350: "Hosea",
    360: "Joel",
    370: "Amos",
    380: "Obadiah",
    390: "Jonah",
    400: "Micah",
    410: "Nahum",
    420: "Habakkuk",
    430: "Zephaniah",
    440: "Haggai",
    450: "Zechariah",
    460: "Malachi",
    462: "I Maccabees",
    464: "II Maccabees",
    466: "III Maccabees",
}


def _strip_tags(text: str) -> str:
    cleaned = _TAG_RE.sub('', text)
    return ' '.join(cleaned.split())


class GreekLxxCsvSource:
    """
    Reads the Rahlfs 1935 LXX TSV and yields Book domain objects.

    In sample_only mode, only chapters listed in sample_chapters are yielded.
    In full mode (sample_only=False), all canonical LXX books are yielded.
    """

    def __init__(
        self,
        csv_path: str,
        sample_only: bool = False,
        sample_chapters: Optional[set[tuple[str, int]]] = None,
    ) -> None:
        self.csv_path = csv_path
        self.sample_only = sample_only
        self.sample_chapters = sample_chapters or set()

    def read_text(self) -> Iterator[Book]:
        """Parse the TSV file and yield one Book per canonical LXX book, in mapping order."""
        raw: dict[int, dict[int, dict[int, str]]] = {}

        with open(self.csv_path, newline="", encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4:
                    continue
                try:
                    book_id = int(parts[0])
                    ch_num = int(parts[1])
                    v_num = int(parts[2])
                except ValueError:
                    continue

                if book_id not in _BOOK_ID_TO_NAME:
                    continue
                if v_num == 0:
                    continue

                book_name = _BOOK_ID_TO_NAME[book_id]

                if self.sample_only and (book_name, ch_num) not in self.sample_chapters:
                    continue

                text = _strip_tags(parts[3])
                if not text:
                    continue

                raw.setdefault(book_id, {}).setdefault(ch_num, {})[v_num] = text

        for book_id, book_name in _BOOK_ID_TO_NAME.items():
            if book_id not in raw:
                continue

            book = Book(name=book_name)
            for ch_num in sorted(raw[book_id]):
                chapter = Chapter(book=book_name, number=ch_num)
                for v_num in sorted(raw[book_id][ch_num]):
                    text = raw[book_id][ch_num][v_num]
                    chapter.verses[v_num] = Verse(number=v_num, text=text)
                if chapter.verses:
                    book.chapters[ch_num] = chapter

            if book.chapters:
                yield book
