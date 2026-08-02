"""Build AnswerEnvelope and run validation."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from core.settings import load_settings
from core.synthesis.models import SynthesisResult
from core.validate.chain import run_validation_chain, to_validator_report
from core.validate.context import ValidationContext
from core.validate.sentences import sentence_count
from core.validate.validators import format_footer
from ingest.processing.writer import load_chunks
from schemas.answer import AnswerEnvelope, AnswerRoute, Citation, ValidatorReport

_SOURCE_LINE = re.compile(r"^\s*Source:\s*.+$", re.I | re.M)
_URL_RE = re.compile(r"https?://[^\s)]+", re.I)


def _processed_root(path: Path | None) -> Path:
    if path is not None:
        return path
    return Path(load_settings().get("paths", {}).get("data_processed", "data/processed"))


def _load_supporting_texts(chunk_ids: list[str], processed_root: Path) -> list[str]:
    if not chunk_ids:
        return []
    by_id = {c.chunk_id: c.text for c in load_chunks(processed_root)}
    return [by_id[cid] for cid in chunk_ids if cid in by_id]


def _strip_router_citation_from_body(text: str) -> str:
    body = _SOURCE_LINE.sub("", text).strip()
    body = _URL_RE.sub("", body).strip()
    return body


def _no_answer_body() -> str:
    return (
        "I couldn't find a verified answer in the listed Groww scheme pages for that question. "
        "Try naming one of the five Direct Growth schemes and a specific fact such as expense ratio or exit load."
    )


def synthesis_to_draft(result: SynthesisResult, *, query_id: UUID | None = None) -> ValidationContext:
    qid = query_id or uuid4()
    body = result.answer_text.strip()
    if result.insufficient_context or result.route == AnswerRoute.NO_ANSWER:
        body = _no_answer_body() if not body else body
    elif result.path.value == "router":
        body = _strip_router_citation_from_body(body)

    chunk_id = None
    if result.fact_card and result.fact_card.chunk_id:
        chunk_id = result.fact_card.chunk_id
    elif result.supporting_chunk_ids:
        chunk_id = result.supporting_chunk_ids[0]

    supporting: list[str] = []
    if result.fact_card and result.fact_card.value_text:
        supporting.append(result.fact_card.value_text)
    if result.scheme_name:
        supporting.append(result.scheme_name)
    processed = _processed_root(None)
    supporting.extend(_load_supporting_texts(result.supporting_chunk_ids, processed))

    skip_groundedness = (
        result.route != AnswerRoute.FACTUAL
        or result.insufficient_context
        or result.path.value == "router"
    )

    max_date = max(result.effective_dates) if result.effective_dates else None
    footer = format_footer(max_date)

    confidence = 0.95 if result.path.value == "fact_card" else 0.85
    if result.insufficient_context:
        confidence = 0.0

    return ValidationContext(
        query_id=qid,
        route=result.route,
        answer_body=body,
        citation_url=result.citation_url,
        citation_label=result.citation_label,
        source_id=result.source_id,
        chunk_id=chunk_id,
        footer=footer,
        confidence=confidence,
        supporting_texts=supporting,
        effective_dates=list(result.effective_dates),
        fact_key=result.fact_key,
        scheme_name=result.scheme_name,
        skip_groundedness=skip_groundedness,
        timings_ms=dict(result.timings_ms),
    )


def compose_answer(
    result: SynthesisResult,
    *,
    query_id: UUID | None = None,
    processed_root: Path | None = None,
) -> AnswerEnvelope:
    """Build and validate an AnswerEnvelope from synthesis output."""

    draft = synthesis_to_draft(result, query_id=query_id)
    if processed_root is not None and result.supporting_chunk_ids:
        extra = _load_supporting_texts(result.supporting_chunk_ids, processed_root)
        draft.supporting_texts = list(dict.fromkeys(draft.supporting_texts + extra))

    ctx, chain = run_validation_chain(draft)
    report = to_validator_report(chain)
    passed = chain.passed and not chain.used_canned

    count = min(sentence_count(ctx.answer_body), 3)
    return AnswerEnvelope(
        query_id=ctx.query_id,
        route=ctx.route,
        answer=ctx.answer_body,
        sentence_count=count,
        citation=Citation(
            url=ctx.citation_url,
            source_id=ctx.source_id,
            chunk_id=ctx.chunk_id,
            label=ctx.citation_label,
        ),
        footer=ctx.footer,
        confidence=ctx.confidence if passed else 0.0,
        validator_report=ValidatorReport(
            passed=passed,
            checks=report.checks,
            repairs=report.repairs,
        ),
        timings_ms=ctx.timings_ms,
    )


def run_validators(ctx: ValidationContext):
    """Run validator chain on a prepared context (testing helper)."""

    return run_validation_chain(ctx)
