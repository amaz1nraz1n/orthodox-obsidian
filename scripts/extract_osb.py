"""
CLI entry point for Orthodox Study Bible extraction.

Wires together the OSB EPUB source adapter, Obsidian renderer, and
Obsidian writer to produce Scripture hub files and OSB Notes companions.

Usage:
    python3 extract_osb.py [epub_path]              # sample mode → output/Scripture/
    python3 extract_osb.py --full                   # full Bible  → output/Scripture-full/
    python3 extract_osb.py --full --output-root=DIR # full Bible  → DIR/
    python3 extract_osb.py --output-root=DIR        # sample mode → DIR/

Validate after full run:
    python3 validate_output.py output/Scripture-full/ --full-osb
"""

import logging
import sys

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.adapters.sources.osb_epub import OsbEpubSource
from vault_builder.domain.canon import book_file_prefix

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_EPUB = "./source_files/Full Bible/The Orthodox Study Bible.epub"

# Representative sample — covers all major genre/feature axes:
#
#   Torah:          Genesis 1 (creation narrative), Exodus 20 (Ten Commandments),
#                   Leviticus 1 (priestly formula)
#   Historical:     I Kingdoms 1 (narrative prose), I Maccabees 1 (deuterocanon)
#   Wisdom/Poetry:  Psalms 1 + 50 (olstyle list, superscription), Job 3 (speech poetry),
#                   Proverbs 8 (mixed), Song of Songs 1 (dialogue), Sirach 1 (deuterocanon)
#   Poetry/Acrostic: Lamentations 1
#   Prophecy:       Isaiah 53, Jeremiah 1, Ezekiel 1
#   NT Gospel:      John 1, Matthew 1 + 5 (Beatitudes)
#   NT Narrative:   Acts 15 (Council of Jerusalem)
#   NT Epistle:     Romans 8, I Corinthians 13, James 1
#   NT Apocalyptic: Revelation 1
#
# Isaiah 7, Matthew 1, James 1, Acts 15 added to anchor EOB/Lexham/NET companions.
SAMPLE_CHAPTERS = {
    # Torah
    ("Genesis",          1),
    ("Exodus",          20),
    ("Leviticus",        1),
    # Historical
    ("I Kingdoms",       1),
    ("I Maccabees",      1),
    # Wisdom / Poetry
    ("Psalms",           1),
    ("Psalms",          50),
    ("Job",              3),
    ("Proverbs",         8),
    ("Song of Solomon",  1),
    ("Sirach",           1),
    # Poetry / Acrostic
    ("Lamentations",     1),
    # Prophecy
    ("Isaiah",           7),
    ("Isaiah",          53),
    ("Jeremiah",         1),
    ("Ezekiel",          1),
    # NT Gospel
    ("John",             1),
    ("Matthew",          1),
    ("Matthew",          5),
    # NT Narrative
    ("Acts",            15),
    # NT Epistle
    ("Romans",           8),
    ("I Corinthians",   13),
    ("James",            1),
    # NT Apocalyptic
    ("Revelation",       1),
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
        logging.info("Full run: extracting entire Bible → %s/", output_root)
    else:
        logging.info(
            "Sample mode: extracting %d representative chapters → %s/ "
            "(pass --full to extract everything)",
            len(SAMPLE_CHAPTERS),
            output_root,
        )

    source = OsbEpubSource(
        epub_path=epub_path,
        sample_only=not full_run,
        sample_chapters=SAMPLE_CHAPTERS,
    )
    renderer = ObsidianRenderer()
    writer = ObsidianWriter(output_root=output_root)

    # Collect book intros first so chapter-1 hubs can link them via intro: frontmatter
    books_with_intros: set[str] = set()
    for book_name, md_content in source.read_intros():
        rendered = renderer.render_book_intro(book_name, md_content)
        writer.write_book_intro(book_name, rendered)
        books_with_intros.add(book_name)

    for book in source.read_text():
        max_ch = book.max_chapter()
        for chapter in book.chapters.values():
            intro_link = (
                f"[[{book_file_prefix(chapter.book)} — OSB Intro]]"
                if chapter.number == 1 and chapter.book in books_with_intros
                else None
            )
            content = renderer.render_hub(chapter, max_ch, intro_link=intro_link)
            writer.write_hub(chapter, content)

    for chapter_notes in source.read_notes():
        content = renderer.render_notes(chapter_notes)
        writer.write_notes(chapter_notes, content)


if __name__ == "__main__":
    main()
