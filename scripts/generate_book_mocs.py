"""
Generate per-book MOC (Map of Content) files for every book in the Orthodox canon.

Each book MOC is the target of `up: "[[BookName]]"` breadcrumb links in chapter hubs.
Without these files, Obsidian's breadcrumb navigation lands at a missing note.

Output: one `{BookName}.md` per book, written to the book's folder alongside intros.

Usage:
    python3 generate_book_mocs.py                      # → output/Scripture/
    python3 generate_book_mocs.py --output-root=DIR
"""

import logging
import os
import sys

from vault_builder.domain.canon import (
    BOOK_ABBREVIATIONS,
    BOOK_CHAPTER_COUNT,
    BOOK_FOLDER,
    BOOK_GENRE,
    BOOK_TESTAMENT,
    book_file_prefix,
    book_folder_path,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _render_book_moc(book: str, intro_exists: bool) -> str:
    abbr = BOOK_ABBREVIATIONS.get(book, book[:3])
    testament = BOOK_TESTAMENT.get(book, "OT")
    genre = BOOK_GENRE.get(book, "")
    chapter_count = BOOK_CHAPTER_COUNT.get(book, 1)
    pfx = book_file_prefix(book)

    chapter_links = " · ".join(f"[[{pfx} {ch}]]" for ch in range(1, chapter_count + 1))
    intro_line = f'\nintro: "[[{pfx} — OSB Intro]]"' if intro_exists else ""

    return (
        f"---\n"
        f'testament: "{testament}"\n'
        f'genre: "{genre}"\n'
        f'book_id: "{abbr}"\n'
        f'cssclasses: [book-moc]{intro_line}\n'
        f"---\n\n"
        f"## {book}\n\n"
        f"{chapter_links}\n"
    )


def generate_book_mocs(output_root: str) -> int:
    written = 0
    for book in BOOK_FOLDER:
        book_dir = os.path.join(output_root, book_folder_path(book))
        os.makedirs(book_dir, exist_ok=True)

        intro_path = os.path.join(book_dir, f"{book_file_prefix(book)} \u2014 OSB Intro.md")
        intro_exists = os.path.exists(intro_path)

        content = _render_book_moc(book, intro_exists)
        moc_path = os.path.join(book_dir, f"{book}.md")
        with open(moc_path, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info("Generated: %s", moc_path)
        written += 1

    return written


def main() -> None:
    output_root = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        "output/Scripture",
    )
    logging.info("Writing Book MOCs → %s/", output_root)
    n = generate_book_mocs(output_root)
    logging.info("Done — %d book MOC files written.", n)


if __name__ == "__main__":
    main()
