"""
CLI entry point for Byzantine Greek NT extraction.

Produces per-chapter text companion files (e.g. Matthew 1 — Greek NT.md)
alongside the existing OSB hub files.

Text: Byzantine Majority Text (Robinson-Pierpont 2018), polytonic Unicode.
Source: source_files/Greek/byzantine-majority-text/csv-unicode/ccat/no-variants/

Usage:
    python3 extract_greek_nt.py              # sample mode → output/Scripture/
    python3 extract_greek_nt.py --full       # full NT     → output/Scripture-full/
    python3 extract_greek_nt.py --full --output-root=DIR
"""

import logging
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.bootstrap import FATHERS_SAMPLE_CHAPTERS
from vault_builder.adapters.sources.greek_nt_csv import GreekNtCsvSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_CSV_DIR = (
    "./source_files/Greek/byzantine-majority-text/csv-unicode/ccat/no-variants"
)

SAMPLE_CHAPTERS = {
    ("Matthew",        1),
    ("Matthew",        5),
    ("Matthew",       18),
    ("John",           1),
    ("John",          14),
    ("Acts",          15),
    ("Romans",         8),
    ("I Corinthians", 13),
    ("Luke",           9),
    ("Luke",          18),
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
    csv_dir = args[0] if args else DEFAULT_CSV_DIR

    if output_root_flag:
        output_root = output_root_flag
    elif full_run:
        output_root = "output/Scripture-full"
    else:
        output_root = "output/Scripture"

    if full_run:
        logging.info("Full run: extracting entire Byzantine Greek NT → %s/", output_root)
    else:
        logging.info(
            "Sample mode: extracting %d chapters → %s/",
            len(SAMPLE_CHAPTERS),
            output_root,
        )

    source = GreekNtCsvSource(
        csv_dir=csv_dir,
        sample_only=not full_run,
        sample_chapters=SAMPLE_CHAPTERS,
    )
    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    count = 0
    for book in source.read_text():
        for chapter in book.chapters.values():
            has_fathers = (chapter.book, chapter.number) in FATHERS_SAMPLE_CHAPTERS
            content = renderer.render_text_companion(
                chapter,
                "Greek NT",
                notes_suffix=None,
                has_fathers=has_fathers,
            )
            writer.write_text_companion(chapter, "Greek NT", content)
            count += 1

    logging.info("Done: %d Greek NT text companions written.", count)


if __name__ == "__main__":
    main()
