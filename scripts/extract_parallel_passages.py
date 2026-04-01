"""
CLI entry point: parallel passage companion files.

Reads data/parallel_passages.yaml and writes one Parallels companion file
per (book, chapter) pair that has known parallel pericopes.

Usage:
    python3 extract_parallel_passages.py
    python3 extract_parallel_passages.py --output-root=DIR
    python3 extract_parallel_passages.py --data=path/to/parallel_passages.yaml
"""

import logging
import sys
from pathlib import Path

from vault_builder.adapters.sources.parallel_passages import ParallelPassageSource
from vault_builder.bootstrap import bootstrap_parallels

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    output_root_flag = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        None,
    )
    data_flag = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--data=")),
        None,
    )
    output_root = output_root_flag or "./output/Scripture"

    kwargs = {}
    if data_flag:
        kwargs["data_path"] = Path(data_flag)

    parallel_source = ParallelPassageSource(**kwargs)
    svc = bootstrap_parallels(output_dir=output_root, parallel_source=parallel_source)
    result = svc.extract()
    logging.info(result.summary())


if __name__ == "__main__":
    main()
