"""
Generate per-book index files for every book in the Orthodox canon.

Produces one {BookName}.md per book inside the book's Scripture folder,
e.g. output/Scripture/02 - New Testament/04 - John/John.md

These files satisfy the `up: [[John]]` / `up: [[Genesis]]` frontmatter
links in every chapter hub, which otherwise point to non-existent files.

Usage:
    python3 generate_book_indexes.py              # → output/Scripture/
    python3 generate_book_indexes.py --full       # → output/Scripture-full/
    python3 generate_book_indexes.py --output-root=DIR
"""

import logging
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.domain.canon import BOOK_CHAPTER_COUNT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


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

    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    count = 0
    for book in BOOK_CHAPTER_COUNT:
        content = renderer.render_book_index(book)
        writer.write_book_index(book, content)
        count += 1

    logging.info("Done: %d book index files written → %s/", count, output_root)


if __name__ == "__main__":
    main()
