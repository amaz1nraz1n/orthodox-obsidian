"""
CLI entry point for Eastern/Greek Orthodox Bible (EOB) NT extraction.

Produces per-chapter text companion files (e.g. Matthew 1 — EOB.md)
alongside the existing OSB hub files.

Usage:
    python3 extract_eob.py                          # sample mode → output/Scripture/
    python3 extract_eob.py --full                   # full NT     → output/Scripture-full/
    python3 extract_eob.py --full --output-root=DIR
    python3 extract_eob.py --output-root=DIR

Validate after full run:
    python3 validate_output.py output/Scripture-full/ --full-osb
"""

import logging
import sys
import warnings

from bs4 import XMLParsedAsHTMLWarning

from vault_builder.bootstrap import bootstrap

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    full_run = "--full" in sys.argv
    output_root = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        "output/Scripture-full" if full_run else "output/Scripture",
    )
    logging.info(
        "%s → %s/",
        "Full run" if full_run else "Sample mode",
        output_root,
    )
    result = bootstrap("eob", output_dir=output_root, full_run=full_run).extract()
    logging.info(result.summary())


if __name__ == "__main__":
    main()
