#!/usr/bin/env python3
"""Extract DBH NT EPUB → Obsidian companion notes."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vault_builder.bootstrap import bootstrap


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract DBH NT EPUB to Obsidian vault.")
    parser.add_argument("--full", action="store_true", help="Full run (all chapters).")
    parser.add_argument("--output", default="output/Scripture", help="Output root directory.")
    args = parser.parse_args()

    service = bootstrap("dbh", output_dir=args.output, full_run=args.full)
    result = service.extract()
    print(result.summary())


if __name__ == "__main__":
    main()
