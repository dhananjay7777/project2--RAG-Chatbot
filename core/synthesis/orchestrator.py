"""End-to-end factual pipeline: router → retrieve → Groq RAG synthesis."""

from __future__ import annotations

import time
from pathlib import Path

from core.retrieval.models import RetrievalStatus, ScoredChunk
from core.retrieval.query_inference import infer_fact_tags
from core.retrieve import retrieve
from core.router.models import RouteDecision
from core.router.pipeline import route_query
from core.synthesis.fact_lookup import lookup_fact_card
from core.synthesis.llm import ChatCompleter
from core.synthesis.deterministic import count_sentences
from core.synthesis.models import SynthesisPath, SynthesisResult
from core.synthesis.pipeline import fact_as_scored_chunk, synthesize_generative
from schemas.answer import AnswerRoute
from schemas.fact_card import FactCard


def _from_router(decision: RouteDecision) -> SynthesisResult:
    text = decision.response_text or ""
    return SynthesisResult(
        path=SynthesisPath.ROUTER,
        route=decision.route,
        answer_text=text,
        citation_url=decision.citation_url,
        citation_label=decision.citation_label,
        source_id=decision.source_id,
        sentence_count=count_sentences(text) if text else 0,
        used_llm=False,
    )


def _attach_fact_metadata(result: SynthesisResult, fact: FactCard | None) -> SynthesisResult:
    if fact is None:
        return result
    result.fact_card = fact
    result.fact_key = fact.fact_key
    result.scheme_name = result.scheme_name or fact.scheme_name
    if fact.source_id:
        result.source_id = fact.source_id
    if fact.effective_date:
        dates = [
            fact.effective_date,
            *[d for d in result.effective_dates if d != fact.effective_date],
        ]
        result.effective_dates = dates
    return result


def _merge_fact_into_chunks(
    chunks: list[ScoredChunk],
    fact: FactCard | None,
) -> list[ScoredChunk]:
    if fact is None:
        return chunks
    lead = fact_as_scored_chunk(fact)
    rest = [c for c in chunks if c.chunk.chunk_id != lead.chunk.chunk_id]
    return [lead, *rest]


def _lookup_fact(query: str, processed_root: Path | None) -> FactCard | None:
    fact = lookup_fact_card(
        query,
        processed_root=processed_root,
        require_verified=True,
    )
    if fact is not None:
        return fact
    return lookup_fact_card(
        query,
        processed_root=processed_root,
        require_verified=False,
    )


def answer_query(
    query: str,
    *,
    last_source_id: str | None = None,
    processed_root: Path | None = None,
    completer: ChatCompleter | None = None,
) -> SynthesisResult:
    """Route; for factual questions always RAG via Groq (never dump scraped text).

    Prefer Fact Card → Groq when a matching card exists (still LLM). Otherwise
    hybrid retrieve → Groq. Refusals / redirects skip Groq.
    """
    t0 = time.perf_counter()
    decision = route_query(query, last_source_id=last_source_id)
    if decision.route != AnswerRoute.FACTUAL:
        result = _from_router(decision)
        result.timings_ms["total_ms"] = int((time.perf_counter() - t0) * 1000)
        return result

    sanitized = decision.sanitized_query
    fact = _lookup_fact(sanitized, processed_root)
    tags = infer_fact_tags(sanitized)

    # Fast RAG path: known attribute Fact Card as sole CONTEXT → Groq.
    if fact is not None and (not tags or fact.fact_key in tags):
        result = synthesize_generative(
            sanitized,
            [fact_as_scored_chunk(fact)],
            completer=completer,
        )
        result = _attach_fact_metadata(result, fact)
        result.timings_ms["total_ms"] = int((time.perf_counter() - t0) * 1000)
        return result

    chunks: list[ScoredChunk] = []
    try:
        retrieval = retrieve(sanitized)
    except Exception:
        retrieval = None
    if (
        retrieval is not None
        and retrieval.status == RetrievalStatus.OK
        and retrieval.chunks
    ):
        chunks = list(retrieval.chunks)

    chunks = _merge_fact_into_chunks(chunks, fact)
    if not chunks:
        return SynthesisResult(
            path=SynthesisPath.RETRIEVAL_MISS,
            route=AnswerRoute.NO_ANSWER,
            insufficient_context=True,
            citation_url=decision.citation_url,
            citation_label=decision.citation_label,
            source_id=decision.source_id,
            used_llm=False,
            timings_ms={"total_ms": int((time.perf_counter() - t0) * 1000)},
        )

    result = synthesize_generative(sanitized, chunks, completer=completer)
    result = _attach_fact_metadata(result, fact)
    result.timings_ms["total_ms"] = int((time.perf_counter() - t0) * 1000)
    return result
