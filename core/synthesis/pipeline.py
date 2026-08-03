"""Generative and Fact Card synthesis paths."""

from __future__ import annotations

import time

from core.retrieval.models import ScoredChunk
from core.router.citation import resolve_citation
from core.synthesis.deterministic import count_sentences, format_fact_answer
from core.synthesis.llm import ChatCompleter, GroqChatCompleter
from core.llm.config import llm_provider
from core.synthesis.models import INSUFFICIENT_CONTEXT, SynthesisPath, SynthesisResult
from core.synthesis.prompt import SYSTEM_PROMPT, build_user_prompt
from core.settings import load_settings
from schemas.answer import AnswerRoute
from schemas.chunk import Chunk
from schemas.fact_card import FactCard


def _generation_settings() -> dict:
    return dict(load_settings().get("generation") or {})


def _default_completer() -> GroqChatCompleter:
    if llm_provider() != "groq":
        raise RuntimeError(
            f"Generative synthesis requires llm.provider=groq, got {llm_provider()!r}"
        )
    return GroqChatCompleter()


def fact_as_scored_chunk(fact: FactCard) -> ScoredChunk:
    """Wrap a verified Fact Card as RAG context for constrained LLM phrasing."""

    value = " ".join((fact.value_text or "").split()).strip()
    text = (
        f"{fact.scheme_name}: {fact.fact_key.replace('_', ' ')} is {value}."
        if value
        else f"{fact.scheme_name}: {fact.fact_key.replace('_', ' ')}."
    )
    chunk = Chunk(
        chunk_id=fact.chunk_id or f"{fact.source_id}#fact-{fact.fact_key}",
        source_id=fact.source_id,
        text=text,
        fact_tags=[fact.fact_key],
        effective_date=fact.effective_date,
        token_count=max(1, len(text.split())),
    )
    return ScoredChunk(
        chunk=chunk,
        source_id=fact.source_id,
        scheme_name=fact.scheme_name,
        rerank_score=1.0,
        rrf_score=1.0,
    )


def synthesize_fact_card(
    fact: FactCard,
    query: str,
    *,
    max_sentences: int | None = None,
) -> SynthesisResult:
    """Deterministic Fact Card phrasing (no LLM) — used as offline / failure fallback."""

    max_sentences = max_sentences or int(_generation_settings().get("max_sentences", 3))
    answer = format_fact_answer(fact, max_sentences=max_sentences)
    url, label, _sid = resolve_citation(query)
    dates = [fact.effective_date] if fact.effective_date else []
    chunk_ids = [fact.chunk_id] if fact.chunk_id else []
    return SynthesisResult(
        path=SynthesisPath.FACT_CARD,
        route=AnswerRoute.FACTUAL,
        answer_text=answer,
        citation_url=url,
        citation_label=label,
        source_id=fact.source_id,
        scheme_name=fact.scheme_name,
        fact_key=fact.fact_key,
        fact_card=fact,
        supporting_chunk_ids=[c for c in chunk_ids if c],
        effective_dates=[d for d in dates if d],
        sentence_count=count_sentences(answer),
        used_llm=False,
    )


def synthesize_fact_card_with_llm(
    fact: FactCard,
    query: str,
    *,
    completer: ChatCompleter | None = None,
) -> SynthesisResult:
    """Phrase a Fact Card answer via Groq, grounded only on the verified fact.

    Falls back to deterministic ``synthesize_fact_card`` if the LLM is unavailable,
    returns insufficient context, or drops the verified value.
    """

    scored = fact_as_scored_chunk(fact)
    try:
        result = synthesize_generative(query, [scored], completer=completer)
    except Exception:
        return synthesize_fact_card(fact, query)

    # Require the full verified value (including NAV "as of …" dates). Checking only
    # the part before "(" let the LLM drop the as-of clause for some schemes.
    needle = " ".join((fact.value_text or "").split()).strip()
    answer_norm = " ".join((result.answer_text or "").split())
    if (
        result.insufficient_context
        or result.route != AnswerRoute.FACTUAL
        or not answer_norm
        or (needle and needle not in answer_norm)
    ):
        return synthesize_fact_card(fact, query)

    url, label, _sid = resolve_citation(query)
    return SynthesisResult(
        path=SynthesisPath.FACT_CARD,
        route=AnswerRoute.FACTUAL,
        answer_text=result.answer_text,
        citation_url=url,
        citation_label=label,
        source_id=fact.source_id,
        scheme_name=fact.scheme_name,
        fact_key=fact.fact_key,
        fact_card=fact,
        supporting_chunk_ids=[scored.chunk.chunk_id],
        effective_dates=[d for d in [fact.effective_date] if d],
        sentence_count=count_sentences(result.answer_text),
        used_llm=True,
        timings_ms=dict(result.timings_ms or {}),
    )


def _parse_generative_output(raw: str) -> tuple[str, bool]:
    text = raw.strip()
    if text == INSUFFICIENT_CONTEXT:
        return "", True
    # Reject sentinel plus commentary (P5-17)
    if text.startswith(INSUFFICIENT_CONTEXT):
        return "", True
    return text, False


def synthesize_generative(
    query: str,
    chunks: list[ScoredChunk],
    *,
    completer: ChatCompleter | None = None,
) -> SynthesisResult:
    if not chunks:
        url, label, sid = resolve_citation(query)
        return SynthesisResult(
            path=SynthesisPath.RETRIEVAL_MISS,
            route=AnswerRoute.NO_ANSWER,
            insufficient_context=True,
            citation_url=url,
            citation_label=label,
            source_id=sid,
            used_llm=False,
        )

    completer = completer or _default_completer()
    settings = _generation_settings()
    temperature = float(settings.get("temperature", 0))
    if temperature != 0:
        raise ValueError("generation.temperature must be 0 for constrained synthesis")

    user_prompt = build_user_prompt(query, chunks)
    t0 = time.perf_counter()
    try:
        raw = completer.complete(system=SYSTEM_PROMPT, user=user_prompt, temperature=0)
    except Exception:
        url, label, sid = resolve_citation(query)
        return SynthesisResult(
            path=SynthesisPath.RETRIEVAL_MISS,
            route=AnswerRoute.NO_ANSWER,
            insufficient_context=True,
            citation_url=url,
            citation_label=label,
            source_id=sid,
            used_llm=True,
            timings_ms={"generation_ms": int((time.perf_counter() - t0) * 1000)},
        )
    elapsed = int((time.perf_counter() - t0) * 1000)

    answer, insufficient = _parse_generative_output(raw)
    top = chunks[0]
    url, label, sid = resolve_citation(query)
    # Citation source follows top retrieved chunk (Phase 6 groundedness refines support).
    from policy.taxonomy import registry_by_source_id

    row = registry_by_source_id().get(top.source_id, {})
    if row:
        url = str(row["url"])
        label = str(row.get("default_citation_label", label))
        sid = top.source_id

    if insufficient:
        return SynthesisResult(
            path=SynthesisPath.GENERATIVE,
            route=AnswerRoute.NO_ANSWER,
            insufficient_context=True,
            citation_url=url,
            citation_label=label,
            source_id=sid,
            scheme_name=top.scheme_name or None,
            supporting_chunk_ids=[c.chunk.chunk_id for c in chunks],
            effective_dates=[
                c.chunk.effective_date for c in chunks if c.chunk.effective_date
            ],
            used_llm=True,
            timings_ms={"generation_ms": elapsed},
        )

    return SynthesisResult(
        path=SynthesisPath.GENERATIVE,
        route=AnswerRoute.FACTUAL,
        answer_text=answer,
        citation_url=url,
        citation_label=label,
        source_id=sid,
        scheme_name=top.scheme_name or None,
        supporting_chunk_ids=[c.chunk.chunk_id for c in chunks],
        effective_dates=[c.chunk.effective_date for c in chunks if c.chunk.effective_date],
        sentence_count=count_sentences(answer),
        used_llm=True,
        timings_ms={"generation_ms": elapsed},
    )
