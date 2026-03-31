"""
CLI entry point for Orthodox Study Bible extraction.

Produces Scripture hub files and OSB Notes companions.

Usage:
    python3 extract_osb.py                          # sample mode → output/Scripture/
    python3 extract_osb.py --full                   # full Bible  → output/Scripture-full/
    python3 extract_osb.py --full --output-root=DIR
    python3 extract_osb.py --output-root=DIR

Validate after full run:
    python3 validate_output.py output/Scripture-full/ --full-osb
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
    result = bootstrap("osb", output_dir=output_root, full_run=full_run).extract()
    logging.info(result.summary())


if __name__ == "__main__":
    main()
