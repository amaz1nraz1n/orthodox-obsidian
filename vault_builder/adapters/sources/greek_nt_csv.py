"""
Adapter: GreekNtCsvSource

Reads the Byzantine Majority Text NT (Robinson-Pierpont 2018) from CSV files
and yields domain Book objects containing per-verse Greek text for all 27 NT books.

CSV format: one file per book, header row `chapter,verse,text`, one row per verse.
Paragraph marker `¶` is stripped from the start of verse text before storing.

Source directory: source_files/Greek/byzantine-majority-text/csv-unicode/ccat/no-variants/
File naming: MAT.csv, MAR.csv, LUK.csv, JOH.csv, etc.

License: Public Domain
"""

import csv
import logging
import os
from typing import Iterator, Optional

from vault_builder.domain.models import Book, Chapter, Verse

logger = logging.getLogger(__name__)

_CSV_CODE_TO_BOOK: dict[str, str] = {
    "MAT": "Matthew",
    "MAR": "Mark",
    "LUK": "Luke",
    "JOH": "John",
    "ACT": "Acts",
    "ROM": "Romans",
    "1CO": "I Corinthians",
    "2CO": "II Corinthians",
    "GAL": "Galatians",
    "EPH": "Ephesians",
    "PHP": "Philippians",
    "COL": "Colossians",
    "1TH": "I Thessalonians",
    "2TH": "II Thessalonians",
    "1TI": "I Timothy",
    "2TI": "II Timothy",
    "TIT": "Titus",
    "PHM": "Philemon",
    "HEB": "Hebrews",
    "JAM": "James",
    "1PE": "I Peter",
    "2PE": "II Peter",
    "1JO": "I John",
    "2JO": "II John",
    "3JO": "III John",
    "JUD": "Jude",
    "REV": "Revelation",
}

_NT_BOOK_ORDER = list(_CSV_CODE_TO_BOOK.values())


class GreekNtCsvSource:
    """
    Reads Byzantine Majority Text NT CSV files and yields Book domain objects.

    In sample_only mode, only chapters listed in sample_chapters are yielded.
    In full mode (sample_only=False), all 27 NT books are yielded.
    """

    def __init__(
        self,
        csv_dir: str,
        sample_only: bool = False,
        sample_chapters: Optional[set[tuple[str, int]]] = None,
    ) -> None:
        self.csv_dir = csv_dir
        self.sample_only = sample_only
        self.sample_chapters = sample_chapters or set()

    def read_text(self) -> Iterator[Book]:
        """Parse CSV files and yield one Book per NT book, in canonical order."""
        for code, book_name in _CSV_CODE_TO_BOOK.items():
            csv_path = os.path.join(self.csv_dir, f"{code}.csv")
            if not os.path.exists(csv_path):
                logger.warning("CSV file not found, skipping: %s", csv_path)
                continue

            raw: dict[int, dict[int, str]] = {}
            self._parse_csv(csv_path, book_name, raw)

            if not raw:
                continue

            book = Book(name=book_name)
            for ch_num in sorted(raw):
                chapter = Chapter(book=book_name, number=ch_num)
                for v_num in sorted(raw[ch_num]):
                    text = raw[ch_num][v_num].strip()
                    if text:
                        chapter.verses[v_num] = Verse(number=v_num, text=text)
                if chapter.verses:
                    book.chapters[ch_num] = chapter

            if book.chapters:
                yield book

    def _parse_csv(
        self,
        csv_path: str,
        book_name: str,
        raw: dict[int, dict[int, str]],
    ) -> None:
        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            next(reader)
            for row in reader:
                if len(row) < 3:
                    continue
                ch_num = int(row[0])
                v_num = int(row[1])
                text = row[2].lstrip("¶").strip()
                if not text:
                    continue
                if self.sample_only and (book_name, ch_num) not in self.sample_chapters:
                    continue
                raw.setdefault(ch_num, {})[v_num] = text
