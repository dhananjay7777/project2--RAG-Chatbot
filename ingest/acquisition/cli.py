"""Command-line interface for Phase 1 corpus acquisition."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from ingest.acquisition.corpus_audit import audit_raw_corpus, summarize_advanced_ratios
from ingest.fetch import bootstrap_snapshots, fetch_all
from ingest.registry import validate_registry

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = ROOT / "data" / "raw"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.acquisition",
        description="Acquire exactly five frozen Groww scheme pages.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch all five live URLs")
    fetch.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    fetch.add_argument(
        "--headless",
        action="store_true",
        help="Use optional Playwright fallback for sparse/static failures",
    )

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help="Bootstrap from five supplied HTML/Markdown snapshots (development only)",
    )
    bootstrap.add_argument("--snapshot-dir", type=Path, required=True)
    bootstrap.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)

    validate = subparsers.add_parser(
        "validate",
        help="Validate latest complete manifest and artifacts",
    )
    validate.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    validate.add_argument(
        "--live",
        action="store_true",
        help="Require latest-live manifest (snapshot runs are rejected)",
    )

    audit = subparsers.add_parser(
        "audit",
        help="Report optional corpus sections (e.g. advanced ratios) in latest raw artifacts",
    )
    audit.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    return parser


def _print_summary(manifest) -> None:
    print(f"run_id: {manifest.run_id}")
    print(f"active_sources: {manifest.active_count}/5")
    print(f"promotion_ready: {str(manifest.promotion_ready).lower()}")
    for record in manifest.records:
        source = record.source
        print(
            f"- {source.source_id}: {source.status.value}; "
            f"mode={source.fetch_mode}; date={source.effective_date}; "
            f"sha256={source.content_sha256}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.command == "fetch":
        manifest = fetch_all(
            args.raw_root,
            use_headless_fallback=args.headless,
        )
    elif args.command == "bootstrap":
        if not args.snapshot_dir.is_dir():
            raise SystemExit(
                f"Snapshot directory does not exist: {args.snapshot_dir}"
            )
        manifest = bootstrap_snapshots(args.snapshot_dir, args.raw_root)
    elif args.command == "audit":
        rows = audit_raw_corpus(args.raw_root)
        print("advanced_ratios audit (latest manifest):")
        for row in rows:
            print(
                f"- {row.source_id}: "
                f"ui_block={row.ui_advanced_block}, "
                f"embedded_json={row.embedded_metrics_json}"
            )
            if row.ui_markers:
                print(f"    ui: {', '.join(row.ui_markers)}")
            if row.json_markers:
                print(f"    json: {', '.join(row.json_markers[:4])}")
        print(f"summary: {summarize_advanced_ratios(rows)}")
        return 0
    else:
        manifest = validate_registry(args.raw_root, require_live=args.live)

    _print_summary(manifest)
    return 0
