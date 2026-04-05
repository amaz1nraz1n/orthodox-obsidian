#!/usr/bin/env python3
"""Extract Robert Alter Hebrew Bible — text + notes companions."""
import argparse
import logging
from vault_builder.bootstrap import bootstrap

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

parser = argparse.ArgumentParser()
parser.add_argument("--full", action="store_true", help="Full run (all MT books)")
args = parser.parse_args()

output = "output/Scripture-full" if args.full else "output/Scripture"
result = bootstrap("alter", output_dir=output, full_run=args.full).extract()
print(result.summary())
