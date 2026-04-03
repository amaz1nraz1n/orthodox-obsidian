"""
CLI entry point for NET Bible 2.1 EPUB extraction.

Produces per-chapter NET text companions (e.g. John 1 — NET.md) and
NET Notes companions (e.g. John 1 — NET Notes.md).

Usage:
    python3 extract_net.py [epub_path]             # sample mode → output/Scripture/
    python3 extract_net.py --full                  # full NT+OT  → output/Scripture-full/
    python3 extract_net.py --full --output-root=DIR
    python3 extract_net.py --output-root=DIR        # sample mode → DIR/
"""

import logging
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.bootstrap import FATHERS_SAMPLE_CHAPTERS
from vault_builder.adapters.sources.net_epub import NetEpubSource
from vault_builder.domain.canon import BOOK_CHAPTER_COUNT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_EPUB = (
    "./source_files/Full Bible/NET Bible 2_1.epub"
)

# Sample chapters aligned to the shared vault sample envelope.
# Tuples are (vault_canonical_book_name, LXX_chapter_number).
# NET does not contain Deuterocanonical books — only Protestant canon.
SAMPLE_CHAPTERS = {
    ("Genesis",          1),
    ("Exodus",          20),
    ("Leviticus",        1),
    ("I Kingdoms",       1),
    ("Psalms",           1),
    ("Psalms",          50),
    ("Job",              3),
    ("Proverbs",         8),
    ("Song of Solomon",  1),
    ("Lamentations",     1),
    ("Isaiah",           7),
    ("Isaiah",          53),
    ("Jeremiah",         1),
    ("Ezekiel",          1),
    ("Matthew",          1),
    ("Matthew",          5),
    ("Matthew",         18),
    ("John",             1),
    ("John",            14),
    ("Acts",            15),
    ("Romans",           8),
    ("I Corinthians",   13),
    ("Luke",             9),
    ("Luke",            18),
    ("James",            1),
    ("Revelation",       1),
}

# Full Protestant canon — all books NET covers, with their chapter counts.
_NET_BOOKS = [
    b for b in BOOK_CHAPTER_COUNT
    if b not in {
        # Deuterocanonical books not in NET
        "Tobit", "Judith", "I Maccabees", "II Maccabees", "III Maccabees",
        "IV Maccabees", "Wisdom of Solomon", "Sirach", "Baruch",
        "I Esdras", "Prayer of Manasseh", "Psalm 151",
    }
]


def main() -> None:
    full_run = "--full" in sys.argv
    output_root_flag = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        None,
    )
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    epub_path = args[0] if args else DEFAULT_EPUB

    if output_root_flag:
        output_root = output_root_flag
    elif full_run:
        output_root = "output/Scripture-full"
    else:
        output_root = "output/Scripture"

    chapters_to_run: set[tuple[str, int]]
    if full_run:
        logging.info("Full run: extracting entire NET Bible → %s/", output_root)
        chapters_to_run = {
            (book, ch)
            for book in _NET_BOOKS
            for ch in range(1, BOOK_CHAPTER_COUNT[book] + 1)
        }
    else:
        logging.info(
            "Sample mode: extracting %d chapters → %s/",
            len(SAMPLE_CHAPTERS),
            output_root,
        )
        chapters_to_run = SAMPLE_CHAPTERS

    source = NetEpubSource(epub_path=epub_path)
    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    text_count = 0
    notes_count = 0
    errors = 0

    for book, chapter in sorted(chapters_to_run):
        try:
            ch_obj = source.read_chapter(book, chapter)
            max_ch = BOOK_CHAPTER_COUNT.get(book, chapter)
            has_fathers = (book, chapter) in FATHERS_SAMPLE_CHAPTERS
            text_content = renderer.render_text_companion(
                ch_obj,
                source="NET",
                notes_suffix=None,
                has_fathers=has_fathers,
            )
            writer.write_text_companion(ch_obj, "NET", text_content)
            text_count += 1

            notes_obj = source.read_notes(book, chapter)
            notes_content = renderer.render_net_notes(
                notes_obj,
                pericopes=ch_obj.pericopes,
                has_fathers=has_fathers,
            )
            writer.write_notes(notes_obj, notes_content)
            notes_count += 1
        except Exception as exc:
            logging.error("Failed %s %s: %s", book, chapter, exc)
            errors += 1

    logging.info(
        "Done: %d text companions + %d notes companions written (%d errors).",
        text_count, notes_count, errors,
    )


if __name__ == "__main__":
    main()
