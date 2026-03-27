"""
CLI entry point for OSB book introduction extraction.

Reads the OSB EPUB and writes per-book intro companion files:
  {BookFolder}/{BookPrefix} — OSB Intro.md

Usage:
    python3 extract_osb_intros.py [epub_path]
    python3 extract_osb_intros.py --output-root=DIR [epub_path]
"""

import logging
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.adapters.sources.osb_epub import OsbEpubSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_EPUB = (
    "./source_files/Full Bible/The Orthodox Study Bible "
    "(St. Athanasius Academy of Orthodox Theology.epub"
)


def main() -> None:
    output_root_flag = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        None,
    )
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    epub_path = args[0] if args else DEFAULT_EPUB
    output_root = output_root_flag or "output/Scripture"

    source = OsbEpubSource(epub_path=epub_path)
    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    count = 0
    errors = 0

    for book, intro_md in source.read_intros():
        try:
            content = renderer.render_book_intro(book, intro_md)
            path = writer.write_book_intro(book, content)
            count += 1
        except Exception as exc:
            logging.error("Failed %s: %s", book, exc)
            errors += 1

    logging.info("Done: %d intro files written (%d errors).", count, errors)


if __name__ == "__main__":
    main()
