"""
CLI entry point for NOAB RSV PDF extraction.

Produces per-chapter RSV text companions (e.g. Genesis 1 — NOAB RSV.md).

Usage:
    python3 extract_noab.py [pdf_path]             # sample mode → output/Scripture/
    python3 extract_noab.py --full                 # full Bible   → output/Scripture-full/
    python3 extract_noab.py --output-root=DIR [pdf_path]
"""

import logging
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.adapters.sources.noab_pdf import NoabPdfSource
from vault_builder.domain.canon import BOOK_CHAPTER_COUNT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_PDF = (
    "./source_files/Full Bible/"
    "New Oxford Annotated Bible with Apocrypha RSV.pdf"
)

SAMPLE_CHAPTERS = {
    ("Genesis",          1),
    ("Genesis",          2),
    ("Exodus",          20),
    # Psalms skipped: multi-psalm-per-page layout causes verse contamination
    ("Isaiah",           7),
    ("Isaiah",          53),
    ("Matthew",          1),
    ("Matthew",          5),
    ("John",             1),
    ("Romans",           8),
    ("I Corinthians",   13),
    ("Revelation",       1),
}


def main() -> None:
    full_run = "--full" in sys.argv
    output_root_flag = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        None,
    )
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pdf_path = args[0] if args else DEFAULT_PDF

    if output_root_flag:
        output_root = output_root_flag
    elif full_run:
        output_root = "output/Scripture-full"
    else:
        output_root = "output/Scripture"

    if full_run:
        chapters_to_run = {
            (book, ch)
            for book, total in BOOK_CHAPTER_COUNT.items()
            for ch in range(1, total + 1)
        }
        logging.info("Full run: extracting entire NOAB RSV → %s/", output_root)
    else:
        chapters_to_run = SAMPLE_CHAPTERS
        logging.info(
            "Sample mode: extracting %d chapters → %s/",
            len(chapters_to_run),
            output_root,
        )

    logging.info("Building chapter index (scanning PDF — this takes ~10 min)…")
    source = NoabPdfSource(pdf_path)
    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    count = 0
    errors = 0

    for book, chapter in sorted(chapters_to_run):
        try:
            ch_obj = source.read_chapter(book, chapter)
            if not ch_obj.verses:
                logging.warning("No verses found: %s %d (skipping)", book, chapter)
                continue
            content = renderer.render_text_companion(ch_obj, source="NOAB RSV", notes_suffix=None)
            writer.write_text_companion(ch_obj, "NOAB RSV", content)
            count += 1
        except Exception as exc:
            logging.error("Failed %s %d: %s", book, chapter, exc)
            errors += 1

    logging.info("Done: %d companions written (%d errors).", count, errors)


if __name__ == "__main__":
    main()
