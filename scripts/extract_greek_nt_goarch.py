"""
CLI entry point for GOArch Greek NT extraction.

Produces per-chapter text companion files (e.g. Matthew 1 — Greek NT.md)
alongside the existing OSB hub files.

Text: 1904 Antoniades Patriarchal Text (canonical liturgical Greek NT of
Eastern Orthodoxy), fully polytonic Unicode.
Source: https://onlinechapel.goarch.org/biblegreek/ (fetched live; 27 requests)

Usage:
    python3 extract_greek_nt_goarch.py              # sample mode → output/Scripture/
    python3 extract_greek_nt_goarch.py --full       # full NT     → output/Scripture-full/
    python3 extract_greek_nt_goarch.py --full --output-root=DIR
"""

import logging
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.bootstrap import FATHERS_SAMPLE_CHAPTERS
from vault_builder.adapters.sources.goarch_greek_nt import GoArchGreekNtSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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

    if output_root_flag:
        output_root = output_root_flag
    elif full_run:
        output_root = "output/Scripture-full"
    else:
        output_root = "output/Scripture"

    if full_run:
        logging.info("Full run: extracting entire GOArch Greek NT → %s/", output_root)
    else:
        logging.info(
            "Sample mode: extracting %d chapters → %s/",
            len(SAMPLE_CHAPTERS),
            output_root,
        )

    source = GoArchGreekNtSource(
        sample_only=not full_run,
        sample_chapters=SAMPLE_CHAPTERS,
    )
    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    count = 0
    for chapter, _notes in source.read_documents():
        has_fathers = (chapter.book, chapter.number) in FATHERS_SAMPLE_CHAPTERS
        content = renderer.render_text_companion(
            chapter,
            "Greek NT",
            notes_suffix=None,
            has_fathers=has_fathers,
        )
        writer.write_text_companion(chapter, "Greek NT", content)
        count += 1
        logging.info("  %s %d", chapter.book, chapter.number)

    logging.info("Done: %d Greek NT text companions written.", count)


if __name__ == "__main__":
    main()
