"""CLI for Phase 2 document processing."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from ingest.processing.pipeline import DEFAULT_PROCESSED_ROOT, DEFAULT_RAW_ROOT, process_corpus
from ingest.processing.strip import strip_audit_violations
from ingest.processing.writer import load_chunks, load_facts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.processing",
        description="Phase 2: parse, strip, chunk, and extract Fact Cards.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    process = sub.add_parser("process", help="Process latest raw corpus into data/processed")
    process.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    process.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED_ROOT)
    process.add_argument(
        "--allow-unverified",
        action="store_true",
        help="Do not fail when required Fact Cards are unverified",
    )

    audit = sub.add_parser("audit", help="Audit processed chunks/facts strip + verification")
    audit.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.command == "process":
        chunks, facts, results = process_corpus(
            raw_root=args.raw_root,
            processed_root=args.processed_root,
            require_verified=not args.allow_unverified,
        )
        print(f"chunks: {len(chunks)}")
        print(f"facts: {len(facts)}")
        for row in results:
            print(
                f"- {row.source_id}: chunks={row.chunk_count}, "
                f"verified={row.verified_facts}/{row.fact_count}, "
                f"null={row.null_facts}, quarantined={row.quarantined_chunks}"
            )
        return 0

    chunks = load_chunks(args.processed_root)
    facts = load_facts(args.processed_root)
    violations = strip_audit_violations("\n".join(c.text for c in chunks))
    critical = [v for v in violations if v != "holdings table remnant"]
    print(f"chunks: {len(chunks)}")
    print(f"facts: {len(facts)}")
    print(f"verified: {sum(1 for f in facts if f.verified_by_human)}")
    print(f"strip_violations: {critical or 'none'}")
    return 1 if critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
