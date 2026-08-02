"""Route user queries before retrieval (Phase 4)."""

from __future__ import annotations

from core.router.citation import ensure_allowlisted, resolve_citation
from core.router.models import RouteDecision
from core.router.pii import scan_query_pii
from core.router.templates import render_template
from core.router.tier1 import Tier1Match, classify_tier1
from core.router.tier2 import (
    apply_asymmetric_threshold,
    classify_tier2,
    heuristic_tier2,
)
from core.settings import load_settings
from schemas.answer import AnswerRoute


def _router_settings() -> dict:
    return dict(load_settings().get("router") or {})


def _decision_from_match(
    match: Tier1Match,
    *,
    sanitized_query: str,
    query_for_citation: str,
    tier: int,
    last_source_id: str | None,
    pii_redacted: bool,
) -> RouteDecision:
    url, label, source_id = resolve_citation(query_for_citation, last_source_id=last_source_id)
    url = ensure_allowlisted(url)

    response_text: str | None = None
    if match.route != AnswerRoute.FACTUAL:
        response_text = render_template(
            match.intent,
            citation_url=url,
            citation_label=label,
        )

    return RouteDecision(
        intent=match.intent,
        route=match.route,
        confidence=match.confidence,
        tier=tier,
        sanitized_query=sanitized_query,
        response_text=response_text,
        citation_url=url,
        citation_label=label,
        source_id=source_id,
        pii_redacted=pii_redacted,
    )


def route_query(
    query: str,
    *,
    last_source_id: str | None = None,
) -> RouteDecision:
    """Classify intent and produce policy-backed response text for non-factual routes."""

    settings = _router_settings()
    max_chars = int(settings.get("max_query_chars", 500))
    min_factual = float(settings.get("tier2_min_factual_confidence", 0.75))

    raw = query if query is not None else ""
    if len(raw) > max_chars:
        raw = raw[:max_chars]

    pii = scan_query_pii(raw)
    sanitized = pii.sanitized_query

    if pii.must_refuse:
        match = Tier1Match("PII_BEARING", AnswerRoute.REFUSAL, 1.0, "pii")
        return _decision_from_match(
            match,
            sanitized_query=sanitized,
            query_for_citation=sanitized,
            tier=1,
            last_source_id=last_source_id,
            pii_redacted=True,
        )

    tier1 = classify_tier1(sanitized)
    if tier1 is not None:
        return _decision_from_match(
            tier1,
            sanitized_query=sanitized,
            query_for_citation=sanitized,
            tier=1,
            last_source_id=last_source_id,
            pii_redacted=False,
        )

    tier2 = classify_tier2(sanitized)
    if tier2 is None:
        tier2 = heuristic_tier2(sanitized)
        tier_num = 2
    else:
        tier_num = 2
        tier2 = apply_asymmetric_threshold(tier2, min_factual_confidence=min_factual)

    return _decision_from_match(
        tier2,
        sanitized_query=sanitized,
        query_for_citation=sanitized,
        tier=tier_num,
        last_source_id=last_source_id,
        pii_redacted=False,
    )


def classify_intent(query: str) -> str:
    """Return intent label string (compat shim)."""
    return route_query(query).intent
