"""Scorecard metrics and CI-blocking compliance gates."""

from __future__ import annotations

from eval.metrics import COMPLIANCE_CRITICAL, compute_metrics, evaluate_gates
from eval.models import CaseResult, GoldenCase
from eval.scorecard import build_scorecard
from schemas.answer import AnswerRoute


def _case(
    *,
    set_name: str,
    route: AnswerRoute,
    case_id: str = "c1",
    source_id: str | None = None,
    value: str | None = None,
    no_digits: bool = False,
) -> GoldenCase:
    return GoldenCase(
        id=case_id,
        set_name=set_name,
        query="q",
        expected_route=route,
        expected_source_id=source_id,
        expected_value_contains=value,
        assert_no_digits=no_digits,
    )


def _result(
    case: GoldenCase,
    *,
    actual: AnswerRoute | None = None,
    answer: str = "ok",
    source_id: str | None = None,
    citation_url: str | None = "https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
    footer: str = "Last updated from sources: 24 Jul 2026",
    sentence_count: int = 1,
    validator_passed: bool = True,
    latency_ms: int = 100,
) -> CaseResult:
    return CaseResult(
        case=case,
        actual_route=actual if actual is not None else case.expected_route,
        answer=answer,
        source_id=source_id or case.expected_source_id,
        citation_url=citation_url,
        footer=footer,
        sentence_count=sentence_count,
        validator_passed=validator_passed,
        latency_ms=latency_ms,
    )


def test_compliance_gates_fail_when_performance_has_digits():
    case = _case(
        set_name="performance",
        route=AnswerRoute.PERFORMANCE_REDIRECT,
        no_digits=True,
    )
    results = [
        _result(case, answer="Returns were 12 percent last year"),
    ]
    metrics = compute_metrics(results)
    assert metrics["hallucinated_number_rate"] == 1.0
    gates = evaluate_gates(metrics)
    assert gates["hallucinated_number_rate"] is False


def test_compliance_gates_pass_on_clean_bundle():
    results = [
        _result(
            _case(
                set_name="factual",
                route=AnswerRoute.FACTUAL,
                source_id="groww-nippon-india-value-fund-direct-growth",
                value="1.27%",
            ),
            answer="The expense ratio is 1.27%.",
            source_id="groww-nippon-india-value-fund-direct-growth",
        ),
        _result(
            _case(set_name="refusal", route=AnswerRoute.REFUSAL, case_id="r1"),
            answer="I cannot give investment advice.",
        ),
        _result(
            _case(
                set_name="performance",
                route=AnswerRoute.PERFORMANCE_REDIRECT,
                case_id="p1",
                no_digits=True,
            ),
            answer="I do not provide returns or performance figures.",
        ),
    ]
    scorecard = build_scorecard(results)
    for name in COMPLIANCE_CRITICAL:
        assert scorecard.gates[name] is True, name
    assert scorecard.passed


def test_refusal_recall_and_precision():
    results = [
        _result(_case(set_name="refusal", route=AnswerRoute.REFUSAL, case_id="a")),
        _result(_case(set_name="refusal", route=AnswerRoute.REFUSAL, case_id="b")),
        _result(
            _case(
                set_name="factual",
                route=AnswerRoute.FACTUAL,
                case_id="f",
                source_id="groww-nippon-india-value-fund-direct-growth",
                value="1.27%",
            ),
            answer="Expense ratio is 1.27%.",
            source_id="groww-nippon-india-value-fund-direct-growth",
        ),
    ]
    metrics = compute_metrics(results)
    assert metrics["refusal_recall"] == 1.0
    assert metrics["refusal_precision"] == 1.0
