"""Structured telemetry must never persist raw PII or raw queries."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

import pytest

from core.observability.redact import assert_no_raw_pii, redact_text
from core.observability.telemetry import build_query_event, log_query_event, query_hash
from schemas.answer import AnswerEnvelope, AnswerRoute, Citation, ValidatorReport

ALLOWLISTED = "https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth"


def _envelope(route: AnswerRoute = AnswerRoute.REFUSAL) -> AnswerEnvelope:
    return AnswerEnvelope(
        query_id=uuid4(),
        route=route,
        answer="I do not collect personal identifiers.",
        sentence_count=1,
        citation=Citation(
            url=ALLOWLISTED,
            source_id="groww-nippon-india-value-fund-direct-growth",
            label="Nippon India Value Fund Direct Growth — Groww",
        ),
        footer="Last updated from sources: 24 Jul 2026",
        confidence=1.0,
        validator_report=ValidatorReport(passed=True),
        timings_ms={"total_ms": 12},
    )


def test_query_hash_is_stable_and_not_raw_text():
    q = "My PAN is ABCDE1234F, what is the exit load?"
    digest = query_hash(q)
    assert digest == query_hash(q)
    assert digest != q
    assert "ABCDE1234F" not in digest
    assert len(digest) == 64


def test_build_query_event_omits_raw_query():
    q = "My PAN is ABCDE1234F and Aadhaar 2345 6789 0123"
    event = build_query_event(q, _envelope())
    blob = json.dumps(event)
    assert "ABCDE1234F" not in blob
    assert "2345 6789 0123" not in blob
    assert q not in blob
    assert event["query_hash"] == query_hash(q)
    assert_no_raw_pii(event)


def test_redact_text_scrubs_pan():
    assert "ABCDE1234F" not in redact_text("PAN ABCDE1234F please")


def test_log_query_event_writes_json_line(caplog: pytest.LogCaptureFixture):
    logger = logging.getLogger("test.telemetry")
    with caplog.at_level(logging.INFO, logger="test.telemetry"):
        event = log_query_event(
            "Should I invest in Tata Multi Asset?",
            _envelope(),
            logger=logger,
        )
    assert event["route"] == "REFUSAL"
    assert any("query_hash" in r.message for r in caplog.records)


def test_assert_no_raw_pii_catches_embedded_pan():
    with pytest.raises(ValueError, match="PII"):
        assert_no_raw_pii({"note": "user pan ABCDE1234F leaked"})
