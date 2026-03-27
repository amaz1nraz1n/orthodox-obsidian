"""
CLI entry point for Rahlfs LXX Greek text extraction.

Produces per-chapter text companion files (e.g. Genesis 1 — LXX.md)
alongside the existing OSB hub files.

Text: Rahlfs 1935 LXX, polytonic Unicode (eliranwong/LXX-Rahlfs-1935-master).
Source: source_files/Greek/LXX-Rahlfs-1935-master/11_end-users_files/MyBible/Bibles/LXX_final_main.csv

Usage:
    python3 extract_greek_lxx.py              # sample mode → output/Scripture/
    python3 extract_greek_lxx.py --full       # full LXX     → output/Scripture-full/
    python3 extract_greek_lxx.py --full --output-root=DIR
"""

import logging
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.adapters.sources.greek_lxx_csv import GreekLxxCsvSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_CSV_PATH = (
    "./source_files/Greek/LXX-Rahlfs-1935-master/11_end-users_files/MyBible/Bibles/LXX_final_main.csv"
)

SAMPLE_CHAPTERS = {
    ("Genesis",           1),
    ("Psalms",           50),
    ("Psalms",          151),
    ("Isaiah",            7),
    ("Wisdom of Solomon", 1),
    ("I Maccabees",       1),
    ("Sirach",            1),
    ("Daniel",            3),
}


def main() -> None:
    full_run = "--full" in sys.argv
    output_root_flag = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        None,
    )
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    csv_path = args[0] if args else DEFAULT_CSV_PATH

    if output_root_flag:
        output_root = output_root_flag
    elif full_run:
        output_root = "output/Scripture-full"
    else:
        output_root = "output/Scripture"

    if full_run:
        logging.info("Full run: extracting entire Rahlfs LXX → %s/", output_root)
    else:
        logging.info(
            "Sample mode: extracting %d LXX chapters → %s/",
            len(SAMPLE_CHAPTERS),
            output_root,
        )

    source = GreekLxxCsvSource(
        csv_path=csv_path,
        sample_only=not full_run,
        sample_chapters=SAMPLE_CHAPTERS,
    )
    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    count = 0
    for book in source.read_text():
        for chapter in book.chapters.values():
            content = renderer.render_text_companion(chapter, "LXX", notes_suffix=None)
            writer.write_text_companion(chapter, "LXX", content)
            count += 1

    logging.info("Done: %d LXX text companions written.", count)


if __name__ == "__main__":
    main()
