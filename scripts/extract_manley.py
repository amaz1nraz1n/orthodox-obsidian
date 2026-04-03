"""
CLI entry point for Manley Fathers companion extraction.
"""

import logging
import sys

from vault_builder.bootstrap import bootstrap

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    full_run = "--full" in sys.argv
    output_root = next(
        (arg.split("=", 1)[1] for arg in sys.argv[1:] if arg.startswith("--output-root=")),
        None,
    ) or ("./output/Scripture-full" if full_run else "./output/Scripture")

    result = bootstrap("manley", output_dir=output_root, full_run=full_run).extract()
    logging.info(result.summary())


if __name__ == "__main__":
    main()
