"""CLI for Phase 9 corpus freshness."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from ingest.freshness.pipeline import DEFAULT_RAW, DEFAULT_REPORT, refresh_corpus


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.freshness",
        description="Phase 9: live re-fetch → validate → process → index (fail-closed).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    refresh = sub.add_parser("refresh", help="Run the full freshness pipeline")
    refresh.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    refresh.add_argument(
        "--headless",
        action="store_true",
        help="Use Playwright headless fetch immediately",
    )
    refresh.add_argument(
        "--no-headless-fallback",
        action="store_true",
        help="Do not retry with Playwright if HTTP fetch fails",
    )
    refresh.add_argument(
        "--skip-process",
        action="store_true",
        help="Fetch+validate only (no process/index)",
    )
    refresh.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help="Write refresh_report.json here",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )
    if args.command != "refresh":
        return 1

    report = refresh_corpus(
        raw_root=args.raw_root,
        headless=args.headless,
        headless_on_http_failure=not args.no_headless_fallback,
        run_process=not args.skip_process,
        run_index=not args.skip_process,
        report_path=args.report,
    )
    print(f"run_at: {report.run_at}")
    print(f"promotion_ready: {str(report.promotion_ready).lower()}")
    print(f"active_sources: {report.active_sources}/5")
    print(f"headless_used: {str(report.headless_used).lower()}")
    print(f"changed: {report.changed_count} unchanged: {report.unchanged_count}")
    print(
        f"process_ok: {str(report.process_ok).lower()} "
        f"index_ok: {str(report.index_ok).lower()}"
    )
    for item in report.sources:
        flag = "CHANGED" if item.changed else "same"
        print(f"- {item.source_id}: {flag}")
    for note in report.notes:
        print(f"note: {note}")
    print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — CLI fail-closed
        logging.getLogger(__name__).error("%s", exc)
        raise SystemExit(1) from exc
