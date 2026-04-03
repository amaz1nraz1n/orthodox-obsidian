"""
CLI entry point for Apostolic Fathers extraction.

Produces per-chapter files under output/Holy-Fathers-full/Apostolic Fathers/,
one file per chapter with verse anchors and inline Scripture-linked footnotes.

Usage:
    python3 extract_apostolic_fathers.py [epub_path]   # sample mode
    python3 extract_apostolic_fathers.py --full        # all 14 documents
    python3 extract_apostolic_fathers.py --full --output-root=DIR
"""

import logging
import os
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.sources.apostolic_fathers_epub import (
    ApostolicFathersEpubSource,
    _AF_DOCUMENTS,
    _HERMAS_BOOK_BOUNDARIES,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_EPUB = (
    "./source_files/Commentary/Apostolic Fathers/The Apostolic Fathers.epub"
)

# Sample: a cross-section of documents and chapters
SAMPLE_CHAPTERS: set[tuple[str, int]] = {
    ("1 Clement",                           4),
    ("1 Clement",                           5),
    ("2 Clement",                           1),
    ("Ignatius to the Ephesians",           1),
    ("Ignatius to the Ephesians",           7),
    ("Ignatius to the Romans",              4),
    ("Polycarp to the Philippians",         2),
    ("Martyrdom of Polycarp",               1),
    ("Didache",                             1),
    ("Didache",                             9),
    ("Epistle of Barnabas",                 1),
    ("Epistle to Diognetus",                5),
    ("Shepherd of Hermas — Visions",        1),
    ("Shepherd of Hermas — Commandments",   1),
    ("Shepherd of Hermas — Parables",       1),
}

# Chapter counts per document (needed for prev/next links)
_CHAPTER_COUNT: dict[str, int] = {
    name: count for _, name, count in _AF_DOCUMENTS
} | {
    name: last - first + 1
    for first, last, name in _HERMAS_BOOK_BOUNDARIES
}


def _sanitize(name: str) -> str:
    """Replace characters illegal in macOS/Windows filenames."""
    return name.replace(":", "").replace("/", "-")


def _doc_folder(root: str, doc_name: str) -> str:
    return os.path.join(root, "Apostolic Fathers", _sanitize(doc_name))


def _write_document_index(doc_folder: str, doc_name: str, max_chapter: int) -> None:
    """Write a stub index file for the document."""
    path = os.path.join(doc_folder, f"{_sanitize(doc_name)}.md")
    if os.path.exists(path):
        return
    chapter_links = " · ".join(
        f"[[{doc_name} {ch}]]" for ch in range(1, max_chapter + 1)
    )
    content = (
        f"---\n"
        f"cssclasses: [patristic-index]\n"
        f'document: "{doc_name}"\n'
        f"---\n\n"
        f"# {doc_name}\n\n"
        f"{chapter_links}\n"
    )
    os.makedirs(doc_folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main() -> None:
    full_run = "--full" in sys.argv
    output_root_flag = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        None,
    )
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    epub_path  = args[0] if args else DEFAULT_EPUB
    output_root = output_root_flag or (
        "./output/Holy-Fathers-full" if full_run else "./output/Holy-Fathers"
    )

    renderer = ObsidianRenderer()
    source   = ApostolicFathersEpubSource(
        epub_path=epub_path,
        sample_only=not full_run,
        sample_chapters=None if full_run else SAMPLE_CHAPTERS,
    )

    count       = 0
    index_done: set[str] = set()

    for chapter, notes in source.read_documents():
        doc_name    = chapter.book
        ch_num      = chapter.number
        max_chapter = _CHAPTER_COUNT.get(doc_name, ch_num)

        folder = _doc_folder(output_root, doc_name)
        os.makedirs(folder, exist_ok=True)

        # Write document index stub once per document
        if doc_name not in index_done:
            _write_document_index(folder, doc_name, max_chapter)
            index_done.add(doc_name)

        content  = renderer.render_patristic_chapter(chapter, notes, max_chapter)
        filename = f"{_sanitize(doc_name)} {ch_num}.md"
        filepath = os.path.join(folder, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logging.info("Generated: %s", filepath)
        count += 1

    logging.info("Done: %d Apostolic Fathers chapter files written.", count)


if __name__ == "__main__":
    main()
