"""
CLI entry point for NETS (A New English Translation of the Septuagint) extraction.

Produces per-chapter text companion files (e.g. Genesis 1 — NETS.md)
alongside NETS Notes companions (e.g. Genesis 1 — NETS Notes.md).
Book introductions are written to 100-References/NETS/.

Usage:
    python3 extract_nets.py                          # sample mode → output/Scripture/
    python3 extract_nets.py --full                   # full OT     → output/Scripture-full/
    python3 extract_nets.py --full --output-root=DIR
    python3 extract_nets.py --output-root=DIR
"""

import logging
import sys

from vault_builder.bootstrap import bootstrap

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
    result = bootstrap("nets", output_dir=output_root, full_run=full_run).extract()
    logging.info(result.summary())


if __name__ == "__main__":
    main()
