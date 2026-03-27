"""
CLI entry point for Lexham English Septuagint notes extraction.

Produces per-chapter Lexham Notes companion files (e.g. Genesis 1 — Lexham Notes.md)
alongside the existing hub and text companion files.

Usage:
    python3 extract_lexham_notes.py [epub_path]              # sample mode → output/Scripture/
    python3 extract_lexham_notes.py --full                   # full OT     → output/Scripture-full/
    python3 extract_lexham_notes.py --full --output-root=DIR
    python3 extract_lexham_notes.py --output-root=DIR        # sample mode → DIR/
"""

import logging
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.adapters.sources.lexham_epub import LexhamEpubSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_EPUB = (
    "./source_files/Old Testament /The Lexham English Septuagint.epub"
)

SAMPLE_CHAPTERS = {
    ("Genesis",          1),
    ("Exodus",          20),
    ("Leviticus",        1),
    ("Numbers",          6),
    ("Deuteronomy",      6),
    ("Joshua",           1),
    ("I Kingdoms",       1),
    ("Psalms",           1),
    ("Psalms",          50),
    ("Job",              3),
    ("Proverbs",         8),
    ("Song of Solomon",  1),
    ("Sirach",           1),
    ("Tobit",            1),
    ("Wisdom of Solomon", 1),
    ("I Maccabees",      1),
    ("Isaiah",           7),
    ("Isaiah",          53),
    ("Jeremiah",         1),
    ("Ezekiel",          1),
    ("Ezra",             1),
    ("Nehemiah",         1),
}


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

    if full_run:
        logging.info("Full run: extracting entire Lexham OT notes → %s/", output_root)
    else:
        logging.info(
            "Sample mode: extracting notes for %d chapters → %s/",
            len(SAMPLE_CHAPTERS),
            output_root,
        )

    source = LexhamEpubSource(
        epub_path=epub_path,
        sample_only=not full_run,
        sample_chapters=SAMPLE_CHAPTERS,
    )
    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    count = 0
    for chapter_notes in source.read_notes():
        content = renderer.render_net_notes(chapter_notes)
        writer.write_notes(chapter_notes, content)
        count += 1

    logging.info("Done: %d Lexham Notes companion files written.", count)


if __name__ == "__main__":
    main()
