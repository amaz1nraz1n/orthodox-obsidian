"""
CLI entry point: Apostolic Fathers patristic catena companions.

Reads the AF EPUB, maps Scripture citations from footnotes to the cited
Scripture chapters, and writes one Fathers companion file per cited chapter
under output/Scripture/.

Usage:
    python3 extract_apostolic_fathers_companions.py
    python3 extract_apostolic_fathers_companions.py --full
    python3 extract_apostolic_fathers_companions.py --output-root=DIR
"""

import logging
import sys

from vault_builder.adapters.sources.apostolic_fathers_epub import (
    ApostolicFathersEpubSource,
)
from vault_builder.bootstrap import bootstrap_fathers

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_EPUB = (
    "./source_files/Commentary/Apostolic Fathers/The Apostolic Fathers.epub"
)


def main() -> None:
    full_run = "--full" in sys.argv
    output_root_flag = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        None,
    )
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    epub_path = args[0] if args else DEFAULT_EPUB
    output_root = output_root_flag or (
        "./output/Scripture-full" if full_run else "./output/Scripture"
    )

    patristic_source = ApostolicFathersEpubSource(
        epub_path=epub_path,
        sample_only=False,
    )

    svc = bootstrap_fathers(
        "apostolic_fathers",
        output_dir=output_root,
        patristic_source=patristic_source,
    )
    result = svc.extract()
    logging.info(result.summary())


if __name__ == "__main__":
    main()
