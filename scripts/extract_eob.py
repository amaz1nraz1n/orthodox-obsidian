"""
CLI entry point for Eastern/Greek Orthodox Bible (EOB) NT extraction.

Produces per-chapter text companion files (e.g. Matthew 1 — EOB.md)
alongside the existing OSB hub files.

Usage:
    python3 extract_eob.py [epub_path]              # sample mode → output/Scripture/
    python3 extract_eob.py --full                   # full NT     → output/Scripture-full/
    python3 extract_eob.py --full --output-root=DIR  # full NT     → DIR/
    python3 extract_eob.py --output-root=DIR         # sample mode → DIR/
"""

import logging
import sys
import warnings

from bs4 import XMLParsedAsHTMLWarning

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.adapters.sources.eob_epub import EobEpubSource

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_EPUB = "./source_files/New Testament/EOB NT.epub"

SAMPLE_CHAPTERS = {
    ("Matthew",        1),
    ("Matthew",        5),
    ("John",           1),
    ("Acts",          15),
    ("Romans",         8),
    ("I Corinthians", 13),
    ("James",          1),
    ("Revelation",     1),
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
        logging.info("Full run: extracting entire EOB NT → %s/", output_root)
    else:
        logging.info(
            "Sample mode: extracting %d chapters → %s/",
            len(SAMPLE_CHAPTERS),
            output_root,
        )

    source = EobEpubSource(
        epub_path=epub_path,
        sample_only=not full_run,
        sample_chapters=SAMPLE_CHAPTERS,
    )
    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    count = 0
    for book in source.read_text():
        for chapter in book.chapters.values():
            content = renderer.render_text_companion(chapter, "EOB")
            writer.write_text_companion(chapter, "EOB", content)
            count += 1

    notes_count = 0
    for chapter_notes in source.read_notes():
        content = renderer.render_notes(chapter_notes)
        writer.write_notes(chapter_notes, content)
        notes_count += 1

    logging.info("Done: %d EOB text companions, %d EOB Notes companions written.", count, notes_count)


if __name__ == "__main__":
    main()
