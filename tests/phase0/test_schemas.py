"""Phase 0 — schema import and validation tests."""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from schemas import (
    AnswerEnvelope,
    AnswerRoute,
    Chunk,
    Citation,
    DocType,
    FactCard,
    SourceRecord,
    SourceStatus,
    ValidatorReport,
)


def test_schemas_importable():
    assert DocType.GROWW_SCHEME_PAGE.value == "GROWW_SCHEME_PAGE"
    assert AnswerRoute.FACTUAL.value == "FACTUAL"


def test_source_record_happy_path():
    rec = SourceRecord(
        source_id="groww-nippon-india-value-fund-direct-growth",
        url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
        amc="Nippon India Mutual Fund",
        scheme_names=["Nippon India Value Fund Direct Growth"],
        effective_date=date(2026, 7, 24),
        status=SourceStatus.ACTIVE,
    )
    assert rec.doc_type == DocType.GROWW_SCHEME_PAGE
    assert rec.authority_tier == 1


def test_source_record_rejects_non_groww_doc_type():
    with pytest.raises(ValidationError):
        SourceRecord(
            source_id="x",
            url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
            amc="X",
            scheme_names=["X"],
            doc_type="SID",  # type: ignore[arg-type]
        )


def test_chunk_pii_scan_enum():
    chunk = Chunk(
        chunk_id="a#1",
        source_id="a",
        text="Exit load of 1%.",
        pii_scan="clean",
    )
    assert chunk.pii_scan == "clean"
    with pytest.raises(ValidationError):
        Chunk(chunk_id="a#1", source_id="a", text="x", pii_scan="dirty")


def test_fact_card_allows_null_value():
    card = FactCard(
        fact_key="benchmark",
        scheme_name="Tata Multi Asset Allocation Fund Direct Growth",
        value_text=None,
        source_id="groww-tata-multi-asset-allocation-fund-direct-growth",
        verified_by_human=True,
    )
    assert card.value_text is None


def test_answer_envelope_happy_path():
    env = AnswerEnvelope(
        query_id=uuid4(),
        route=AnswerRoute.FACTUAL,
        answer="The expense ratio is 1.27%.",
        sentence_count=1,
        citation=Citation(
            url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
            source_id="groww-nippon-india-value-fund-direct-growth",
            label="Nippon India Value Fund Direct Growth — Groww",
        ),
        footer="Last updated from sources: 24 Jul 2026",
        confidence=0.9,
        validator_report=ValidatorReport(passed=True),
    )
    assert env.route == AnswerRoute.FACTUAL


def test_answer_envelope_rejects_bad_footer():
    with pytest.raises(ValidationError):
        AnswerEnvelope(
            query_id=uuid4(),
            route=AnswerRoute.NO_ANSWER,
            answer="Unknown.",
            sentence_count=1,
            citation=Citation(
                url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
                source_id="groww-nippon-india-value-fund-direct-growth",
                label="x",
            ),
            footer="Updated yesterday",
            confidence=0.1,
            validator_report=ValidatorReport(passed=False),
        )


def test_answer_envelope_rejects_unknown_route():
    with pytest.raises(ValidationError):
        AnswerEnvelope(
            query_id=uuid4(),
            route="ADVICE",  # type: ignore[arg-type]
            answer="x",
            sentence_count=1,
            citation=Citation(
                url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
                source_id="groww-nippon-india-value-fund-direct-growth",
                label="x",
            ),
            footer="Last updated from sources: 24 Jul 2026",
            confidence=0.1,
            validator_report=ValidatorReport(passed=False),
        )


def test_answer_envelope_rejects_sentence_count_over_three():
    with pytest.raises(ValidationError):
        AnswerEnvelope(
            query_id=uuid4(),
            route=AnswerRoute.FACTUAL,
            answer="a. b. c. d.",
            sentence_count=4,
            citation=Citation(
                url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
                source_id="groww-nippon-india-value-fund-direct-growth",
                label="x",
            ),
            footer="Last updated from sources: 24 Jul 2026",
            confidence=0.5,
            validator_report=ValidatorReport(passed=True),
        )
