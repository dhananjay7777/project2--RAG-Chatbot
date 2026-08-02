"""Phase 8: reproducible evaluation scorecard runner.

Usage:
  python -m eval.run_eval
  python -m eval.run_eval --sets refusal,performance,pii,oos,adversarial
  python eval/run_eval.py --json scorecard.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.metrics import COMPLIANCE_CRITICAL, TARGETS
from eval.scorecard import run_eval


def _default_as_of() -> str | None:
    """Prefer corpus capture date from processed facts when present."""

    facts = ROOT / "data" / "processed" / "facts.jsonl"
    if not facts.is_file():
        return None
    latest: date | None = None
    for line in facts.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            raw = row.get("effective_date")
            if not raw:
                continue
            d = date.fromisoformat(str(raw)[:10])
        except Exception:
            continue
        if latest is None or d > latest:
            latest = d
    return latest.isoformat() if latest else None


def _fmt(val: float) -> str:
    if isinstance(val, float) and math.isnan(val):
        return "n/a"
    if isinstance(val, float) and abs(val - round(val)) < 1e-9 and abs(val) >= 1:
        return str(int(round(val)))
    return f"{val:.4f}" if isinstance(val, float) else str(val)


def _print_scorecard(scorecard) -> None:
    print("=== Mutual Fund FAQ — Phase 8 Scorecard ===")
    print(f"cases: {int(scorecard.metrics.get('n_cases', 0))}")
    print()
    print("Metrics")
    for key in (
        "retrieval_recall_at_5",
        "exact_fact_accuracy",
        "citation_validity",
        "refusal_recall",
        "refusal_precision",
        "constraint_compliance",
        "hallucinated_number_rate",
        "p95_latency_ms",
        "cost_per_query_usd",
        "route_accuracy",
    ):
        target = TARGETS.get(key)
        suffix = f" (target {_fmt(target)})" if target is not None else ""
        critical = " [CI-blocking]" if key in COMPLIANCE_CRITICAL else ""
        print(f"  {key}: {_fmt(scorecard.metrics.get(key, float('nan')))}{suffix}{critical}")
    print()
    print("Gates")
    for name, ok in sorted(scorecard.gates.items()):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    failed = scorecard.meta.get("failed_cases") or []
    if failed:
        print()
        print(f"Failed cases ({len(failed)}):")
        for item in failed[:30]:
            print(f"  - {item['set']}/{item['id']}: {'; '.join(item['errors'])}")
        if len(failed) > 30:
            print(f"  … {len(failed) - 30} more")
    print()
    print(f"Overall: {'PASS' if scorecard.passed else 'FAIL'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 8 evaluation scorecard")
    parser.add_argument(
        "--sets",
        default="",
        help="Comma-separated golden sets (default: all)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write machine-readable scorecard JSON to this path",
    )
    parser.add_argument(
        "--with-retrieval",
        action="store_true",
        help="Also compute retrieval Recall@5 (requires local index)",
    )
    parser.add_argument(
        "--strict-latency",
        action="store_true",
        help="Fail the scorecard if p95 latency exceeds 3s",
    )
    parser.add_argument(
        "--compliance-only",
        action="store_true",
        help="Exit non-zero only when compliance-critical gates fail",
    )
    parser.add_argument(
        "--as-of",
        default="",
        help="Freeze freshness calendar day (YYYY-MM-DD). Default: max fact effective_date or MF_AS_OF_DATE",
    )
    args = parser.parse_args(argv)

    as_of = (args.as_of or os.getenv("MF_AS_OF_DATE") or _default_as_of() or "").strip()
    if as_of:
        os.environ["MF_AS_OF_DATE"] = as_of

    sets = [s.strip() for s in args.sets.split(",") if s.strip()] or None
    scorecard = run_eval(
        sets=sets,
        with_retrieval_metric=args.with_retrieval,
        strict_latency=args.strict_latency,
    )
    if as_of:
        print(f"as_of: {as_of}")
    _print_scorecard(scorecard)

    if args.json:
        metrics = {
            key: (None if isinstance(value, float) and value != value else value)
            for key, value in scorecard.metrics.items()
        }
        payload = {
            "metrics": metrics,
            "gates": scorecard.gates,
            "passed": scorecard.passed,
            "meta": scorecard.meta,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")

    if args.compliance_only:
        critical_ok = all(
            scorecard.gates.get(name, False) for name in COMPLIANCE_CRITICAL
        )
        return 0 if critical_ok else 1
    return 0 if scorecard.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
