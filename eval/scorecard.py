"""Run golden cases through ask() and build a scorecard."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable
from uuid import uuid4

from core.ask import ask
from eval.loader import load_all_goldens
from eval.metrics import COMPLIANCE_CRITICAL, compute_metrics, evaluate_gates, route_confusion
from eval.models import CaseResult, GoldenCase, Scorecard
from schemas.answer import AnswerEnvelope, AnswerRoute

AskFn = Callable[..., AnswerEnvelope]


def _digits_ok(case: GoldenCase, answer: str) -> bool:
    if not case.assert_no_digits and case.expected_route != AnswerRoute.PERFORMANCE_REDIRECT:
        return True
    return not any(ch.isdigit() for ch in answer)


def _evaluate_case(
    case: GoldenCase,
    envelope: AnswerEnvelope,
    *,
    latency_ms: int,
    retrieval_hit_at_5: bool | None,
) -> CaseResult:
    errors: list[str] = []
    if envelope.route != case.expected_route:
        errors.append(
            f"route {envelope.route.value} != expected {case.expected_route.value}"
        )
    if case.expected_source_id and envelope.citation.source_id != case.expected_source_id:
        if envelope.route == AnswerRoute.FACTUAL:
            errors.append(
                f"source_id {envelope.citation.source_id!r} != {case.expected_source_id!r}"
            )
    if case.expected_value_contains and case.expected_value_contains not in envelope.answer:
        if envelope.route == AnswerRoute.FACTUAL:
            errors.append(f"missing expected value {case.expected_value_contains!r}")
    if not _digits_ok(case, envelope.answer):
        errors.append("answer contains digits (performance must be numeral-free)")

    return CaseResult(
        case=case,
        actual_route=envelope.route,
        answer=envelope.answer,
        source_id=envelope.citation.source_id,
        citation_url=str(envelope.citation.url),
        footer=envelope.footer,
        sentence_count=envelope.sentence_count,
        validator_passed=envelope.validator_report.passed,
        latency_ms=latency_ms,
        errors=errors,
        retrieval_hit_at_5=retrieval_hit_at_5,
        cost_usd=0.0,
    )


def _retrieval_hit(case: GoldenCase) -> bool | None:
    if case.set_name != "factual" or not case.expected_source_id:
        return None
    try:
        from core.retrieve import retrieve
        from core.retrieval.models import RetrievalStatus
    except Exception:
        return None
    try:
        result = retrieve(case.query)
    except Exception:
        return None
    if result.status != RetrievalStatus.OK:
        return False
    top = [c.source_id for c in result.chunks[:5]]
    return case.expected_source_id in top


def run_case(
    case: GoldenCase,
    *,
    ask_fn: AskFn = ask,
    processed_root: Path | None = None,
    with_retrieval_metric: bool = False,
) -> CaseResult:
    t0 = time.perf_counter()
    try:
        envelope = ask_fn(
            case.query,
            query_id=uuid4(),
            processed_root=processed_root,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
    except Exception as exc:  # noqa: BLE001 — scorecard must continue
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return CaseResult(
            case=case,
            actual_route=None,
            answer="",
            source_id=None,
            citation_url=None,
            footer="",
            sentence_count=0,
            validator_passed=False,
            latency_ms=latency_ms,
            errors=[f"ask() failed: {exc}"],
            cost_usd=0.0,
        )

    hit = _retrieval_hit(case) if with_retrieval_metric else None
    return _evaluate_case(
        case,
        envelope,
        latency_ms=latency_ms,
        retrieval_hit_at_5=hit,
    )


def build_scorecard(
    results: list[CaseResult],
    *,
    strict_latency: bool = False,
    meta: dict | None = None,
) -> Scorecard:
    metrics = compute_metrics(results)
    gates = evaluate_gates(metrics, strict_latency=strict_latency)
    payload = dict(meta or {})
    payload["confusion"] = route_confusion(results)
    payload["compliance_critical"] = sorted(COMPLIANCE_CRITICAL)
    payload["failed_cases"] = [
        {"id": r.case.id, "set": r.case.set_name, "errors": r.errors}
        for r in results
        if r.errors
    ]
    return Scorecard(results=results, metrics=metrics, gates=gates, meta=payload)


def run_eval(
    *,
    sets: list[str] | None = None,
    processed_root: Path | None = None,
    ask_fn: AskFn = ask,
    with_retrieval_metric: bool = False,
    strict_latency: bool = False,
) -> Scorecard:
    cases = load_all_goldens(sets=sets)
    results = [
        run_case(
            case,
            ask_fn=ask_fn,
            processed_root=processed_root,
            with_retrieval_metric=with_retrieval_metric,
        )
        for case in cases
    ]
    return build_scorecard(
        results,
        strict_latency=strict_latency,
        meta={"sets": sets or "all", "n": len(results)},
    )
