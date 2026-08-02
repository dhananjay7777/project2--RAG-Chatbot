"""Structured JSON query telemetry (Phase 8)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from core.observability.redact import assert_no_raw_pii, redact_text
from schemas.answer import AnswerEnvelope

_LOGGER = logging.getLogger("mf_faq.telemetry")


def query_hash(query: str) -> str:
    """Stable SHA-256 of the raw query — never store the raw text."""

    return hashlib.sha256((query or "").encode("utf-8")).hexdigest()


def build_query_event(
    query: str,
    envelope: AnswerEnvelope,
    *,
    retrieval_scores: list[float] | None = None,
    token_cost_usd: float = 0.0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a privacy-safe structured log record (no raw query text)."""

    # Defense in depth: redact any accidental string fields in extras.
    safe_extra: dict[str, Any] = {}
    for key, value in (extra or {}).items():
        if isinstance(value, str):
            safe_extra[key] = redact_text(value)
        else:
            safe_extra[key] = value

    event: dict[str, Any] = {
        "event": "ask",
        "query_id": str(envelope.query_id),
        "query_hash": query_hash(query),
        "route": envelope.route.value,
        "retrieval_scores": list(retrieval_scores or []),
        "validator_report": {
            "passed": envelope.validator_report.passed,
            "repairs": envelope.validator_report.repairs,
            "checks": {
                name: {"passed": bool(info.get("passed"))}
                for name, info in (envelope.validator_report.checks or {}).items()
                if isinstance(info, dict)
            },
        },
        "timings_ms": dict(envelope.timings_ms or {}),
        "token_cost_usd": float(token_cost_usd),
        "confidence": envelope.confidence,
        "sentence_count": envelope.sentence_count,
        "citation_source_id": envelope.citation.source_id,
    }
    if safe_extra:
        event["extra"] = safe_extra
    assert_no_raw_pii(event)
    return event


def log_query_event(
    query: str,
    envelope: AnswerEnvelope,
    *,
    retrieval_scores: list[float] | None = None,
    token_cost_usd: float = 0.0,
    extra: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Emit one JSON log line per ask; returns the event for tests/audits."""

    event = build_query_event(
        query,
        envelope,
        retrieval_scores=retrieval_scores,
        token_cost_usd=token_cost_usd,
        extra=extra,
    )
    (logger or _LOGGER).info("%s", json.dumps(event, separators=(",", ":")))
    return event
