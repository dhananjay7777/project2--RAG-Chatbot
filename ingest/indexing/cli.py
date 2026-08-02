"""Phase 3 indexing CLI."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from ingest.indexing.pipeline import build_index


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.indexing",
        description="Phase 3: build Chroma + BM25 indexes from processed chunks.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="Build or refresh the retrieval index")
    build.add_argument("--processed-root", type=Path, default=None)
    build.add_argument("--index-root", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )
    if args.command == "build":
        manifest = build_index(
            processed_root=args.processed_root,
            index_root=args.index_root,
        )
        print(f"chunks_indexed: {manifest.chunk_count}")
        print(f"embedding_model: {manifest.embedding_model}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
