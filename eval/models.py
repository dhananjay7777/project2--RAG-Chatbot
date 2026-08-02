"""Golden-case and scorecard models for Phase 8."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from schemas.answer import AnswerRoute


@dataclass(frozen=True)
class GoldenCase:
    id: str
    set_name: str
    query: str
    expected_route: AnswerRoute
    expected_source_id: str | None = None
    expected_value_contains: str | None = None
    fact_key: str | None = None
    assert_no_digits: bool = False
    expected_citation_url: str | None = None


@dataclass
class CaseResult:
    case: GoldenCase
    actual_route: AnswerRoute | None
    answer: str
    source_id: str | None
    citation_url: str | None
    footer: str
    sentence_count: int
    validator_passed: bool
    latency_ms: int
    errors: list[str] = field(default_factory=list)
    retrieval_hit_at_5: bool | None = None
    cost_usd: float = 0.0

    @property
    def route_ok(self) -> bool:
        return self.actual_route == self.case.expected_route and not self.errors


@dataclass
class Scorecard:
    results: list[CaseResult]
    metrics: dict[str, float]
    gates: dict[str, bool]
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(self.gates.values())
