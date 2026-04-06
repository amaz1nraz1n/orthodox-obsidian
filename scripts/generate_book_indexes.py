"""
Generate per-book index files, section indexes, and a Scripture home page.

Produces:
  output/Scripture/Scripture.md                         — top-level home
  output/Scripture/01 - Old Testament/01 - Old Testament.md  — OT section
  output/Scripture/02 - New Testament/02 - New Testament.md  — NT section
  output/Scripture/{section}/{order} - {Book}/{Book}.md — per-book chapter list

These files satisfy the `up:` breadcrumb links in every chapter hub and
book index, which otherwise point to non-existent files.

Usage:
    python3 generate_book_indexes.py              # → output/Scripture/
    python3 generate_book_indexes.py --full       # → output/Scripture-full/
    python3 generate_book_indexes.py --output-root=DIR
"""

import logging
import os
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.domain.canon import (
    BOOK_CHAPTER_COUNT,
    BOOK_FOLDER,
    BOOK_GENRE,
    BOOK_TESTAMENT,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Genre groupings for section indexes (in display order)
_OT_GENRE_ORDER = ["Torah", "Historical", "Wisdom", "Prophetic"]
_NT_GENRE_ORDER = ["Gospel", "Acts", "Epistle", "Apocalypse"]


def _books_by_section() -> tuple[list[str], list[str], list[str]]:
    """Return (ot_books, deuterocanon_books, nt_books) in canonical order."""
    ot, deutero, nt = [], [], []
    for book in BOOK_CHAPTER_COUNT:
        t = BOOK_TESTAMENT.get(book, "OT")
        if t == "NT":
            nt.append(book)
        elif t == "Deuterocanon":
            deutero.append(book)
        else:
            ot.append(book)
    return ot, deutero, nt


def _group_by_genre(books: list[str], genre_order: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {g: [] for g in genre_order}
    for book in books:
        genre = BOOK_GENRE.get(book, genre_order[0])
        groups.setdefault(genre, []).append(book)
    return groups


def _render_section_index(section_name: str, ot_books: list[str],
                           deutero_books: list[str], genre_order: list[str],
                           up: str) -> str:
    lines = [
        "---",
        "cssclasses: [section-index]",
        f'up: "[[{up}]]"',
        "---",
        "",
        f"# {section_name}",
        "",
    ]
    groups = _group_by_genre(ot_books, genre_order)
    for genre in genre_order:
        books = groups.get(genre, [])
        if not books:
            continue
        lines.append(f"## {genre}")
        lines.append("")
        for book in books:
            lines.append(f"- [[{book}]]")
        lines.append("")

    if deutero_books:
        lines.append("## Deuterocanon")
        lines.append("")
        for book in deutero_books:
            lines.append(f"- [[{book}]]")
        lines.append("")

    return "\n".join(lines)


def _render_nt_section_index(nt_books: list[str], up: str) -> str:
    lines = [
        "---",
        "cssclasses: [section-index]",
        f'up: "[[{up}]]"',
        "---",
        "",
        "# New Testament",
        "",
    ]
    groups = _group_by_genre(nt_books, _NT_GENRE_ORDER)
    for genre in _NT_GENRE_ORDER:
        books = groups.get(genre, [])
        if not books:
            continue
        lines.append(f"## {genre}")
        lines.append("")
        for book in books:
            lines.append(f"- [[{book}]]")
        lines.append("")
    return "\n".join(lines)


def _render_scripture_home() -> str:
    return "\n".join([
        "---",
        "cssclasses: [scripture-home]",
        "---",
        "",
        "# Holy Scripture",
        "",
        "- [[01 - Old Testament]]",
        "- [[02 - New Testament]]",
        "",
    ])


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info("Generated: %s", path)


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
    ot_books, deutero_books, nt_books = _books_by_section()

    # 1. Per-book chapter indexes
    count = 0
    for book in BOOK_CHAPTER_COUNT:
        content = renderer.render_book_index(book)
        writer.write_book_index(book, content)
        count += 1

    # 2. OT section index
    ot_content = _render_section_index(
        "Old Testament", ot_books, deutero_books, _OT_GENRE_ORDER, "Scripture"
    )
    _write(os.path.join(output_root, "01 - Old Testament", "01 - Old Testament.md"), ot_content)

    # 3. NT section index
    nt_content = _render_nt_section_index(nt_books, "Scripture")
    _write(os.path.join(output_root, "02 - New Testament", "02 - New Testament.md"), nt_content)

    # 4. Scripture home
    _write(os.path.join(output_root, "Scripture.md"), _render_scripture_home())

    logging.info(
        "Done: %d book indexes + 2 section indexes + home → %s/",
        count, output_root,
    )


if __name__ == "__main__":
    main()
