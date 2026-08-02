"""Tier-2 LLM intent classifier (optional, Groq)."""

from __future__ import annotations

import json
import re
from typing import Optional

from schemas.answer import AnswerRoute

from core.llm.client import is_groq_configured, tier2_chat_complete
from core.router.tier1 import Tier1Match
from policy.taxonomy import intent_classes

_LABELS = (
    "FACTUAL_ATTRIBUTE",
    "FACTUAL_PROCESS",
    "ADVISORY",
    "RANKING_COMPARATIVE",
    "PERFORMANCE_RETURNS",
    "SPECULATIVE_FORECAST",
    "PII_BEARING",
    "OUT_OF_SCOPE",
    "AMBIGUOUS",
)


def _route_for_intent(intent: str) -> AnswerRoute:
    route_name = intent_classes()[intent]["route"]
    return AnswerRoute(route_name)


def classify_tier2(query: str) -> Optional[Tier1Match]:
    """Return intent from Groq when GROQ_API_KEY is configured; else None."""

    if not is_groq_configured():
        return None

    system = (
        "Classify the user message into exactly one mutual-fund FAQ intent label. "
        "Labels: "
        + ", ".join(_LABELS)
        + ". "
        "This assistant only covers five Groww Direct Growth mutual-fund scheme pages. "
        "Use OUT_OF_SCOPE for commodity prices (gold, silver, oil), crypto, stocks, "
        "indexes, weather, sports, politics, or any non-scheme topic. "
        "Return JSON only: {\"label\": \"...\", \"confidence\": 0.0-1.0}. "
        "Prefer REFUSAL-related labels (ADVISORY, RANKING_COMPARATIVE, SPECULATIVE_FORECAST) "
        "or OUT_OF_SCOPE when unsure — never invent FACTUAL_ATTRIBUTE for off-corpus topics."
    )
    try:
        body = tier2_chat_complete(system=system, user=query[:2000])
        data = json.loads(body)
    except Exception:
        return None

    label = str(data.get("label", "")).strip().upper()
    if label not in _LABELS:
        return None
    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))
    route = _route_for_intent(label)
    return Tier1Match(label, route, confidence, "tier2_llm")


def apply_asymmetric_threshold(match: Tier1Match, *, min_factual_confidence: float) -> Tier1Match:
    """On low confidence, prefer refusal/clarify over factual."""

    if match.route == AnswerRoute.FACTUAL and match.confidence < min_factual_confidence:
        return Tier1Match(
            "ADVISORY",
            AnswerRoute.REFUSAL,
            match.confidence,
            "asymmetric_low_confidence",
        )
    if match.confidence < 0.5 and match.route == AnswerRoute.FACTUAL:
        return Tier1Match("AMBIGUOUS", AnswerRoute.CLARIFY, match.confidence, "low_confidence")
    return match


def heuristic_tier2(query: str) -> Tier1Match:
    """Conservative fallback when Tier-1 and LLM are inconclusive."""

    q = query.lower()
    if re.search(
        r"\b(gold|silver|crude|oil|bitcoin|crypto|commodity|sensex|stock\s+price)\b",
        q,
    ):
        return Tier1Match("OUT_OF_SCOPE", AnswerRoute.NO_ANSWER, 0.7, "heuristic_oos")
    if re.search(r"\b(should|recommend|advise|best|better|vs\.?)\b", q):
        return Tier1Match("ADVISORY", AnswerRoute.REFUSAL, 0.6, "heuristic_advisory")
    if re.search(r"\b(return|performance)\b", q):
        return Tier1Match(
            "PERFORMANCE_RETURNS",
            AnswerRoute.PERFORMANCE_REDIRECT,
            0.6,
            "heuristic_performance",
        )
    return Tier1Match("AMBIGUOUS", AnswerRoute.CLARIFY, 0.55, "heuristic_clarify")
