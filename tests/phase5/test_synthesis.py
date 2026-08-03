"""Phase 5 synthesis tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core.retrieval.models import ScoredChunk
from core.synthesis.models import INSUFFICIENT_CONTEXT, SynthesisPath
from core.synthesis.orchestrator import answer_query
from core.synthesis.pipeline import synthesize_fact_card, synthesize_generative
from core.synthesis.prompt import SYSTEM_PROMPT, build_user_prompt
from schemas.answer import AnswerRoute
from schemas.chunk import Chunk
from schemas.fact_card import FactCard

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


class MockCompleter:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict] = []

    def complete(self, *, system: str, user: str, temperature: float) -> str:
        self.calls.append({"system": system, "user": user, "temperature": temperature})
        assert temperature == 0
        return self.response


def test_fact_card_synthesis_no_llm():
    fact = FactCard(
        fact_key="expense_ratio",
        scheme_name="Nippon India Value Fund Direct Growth",
        value_text="1.27%",
        source_id="groww-nippon-india-value-fund-direct-growth",
        chunk_id="groww-nippon-india-value-fund-direct-growth#002",
        effective_date=date(2026, 7, 24),
        verified_by_human=True,
    )
    result = synthesize_fact_card(fact, "expense ratio?")
    assert result.path == SynthesisPath.FACT_CARD
    assert result.used_llm is False
    assert "1.27%" in result.answer_text
    assert result.sentence_count <= 3


def test_generative_default_uses_groq_completer(monkeypatch):
    from core.synthesis import pipeline as synth_pipeline

    called = {"ok": False}

    class _FakeGroq:
        def complete(self, *, system: str, user: str, temperature: float) -> str:
            called["ok"] = True
            return "INSUFFICIENT_CONTEXT"

    monkeypatch.setattr(synth_pipeline, "_default_completer", lambda: _FakeGroq())
    chunk = Chunk(
        chunk_id="c1",
        source_id="groww-nippon-india-value-fund-direct-growth",
        text="Expense ratio 1.27%",
    )
    scored = ScoredChunk(chunk=chunk, source_id=chunk.source_id)
    synth_pipeline.synthesize_generative("expense ratio?", [scored], completer=None)
    assert called["ok"]


def test_default_completer_requires_groq_provider(monkeypatch):
    from core.synthesis.pipeline import _default_completer

    monkeypatch.setattr(
        "core.synthesis.pipeline.llm_provider",
        lambda: "openai",
    )
    try:
        _default_completer()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "groq" in str(exc).lower()


def test_generative_insufficient_sentinel():
    chunk = Chunk(
        chunk_id="c1",
        source_id="groww-nippon-india-value-fund-direct-growth",
        text="Expense ratio 1.27%",
    )
    scored = ScoredChunk(
        chunk=chunk,
        source_id=chunk.source_id,
        scheme_name="Nippon India Value Fund Direct Growth",
    )
    completer = MockCompleter(INSUFFICIENT_CONTEXT)
    result = synthesize_generative("What is the alpha?", [scored], completer=completer)
    assert result.insufficient_context is True
    assert result.route == AnswerRoute.NO_ANSWER
    assert completer.calls[0]["system"] == SYSTEM_PROMPT


def test_generative_rejects_sentinel_with_trailing_text():
    chunk = Chunk(
        chunk_id="c1",
        source_id="groww-nippon-india-value-fund-direct-growth",
        text="text",
    )
    scored = ScoredChunk(chunk=chunk, source_id=chunk.source_id)
    completer = MockCompleter(f"{INSUFFICIENT_CONTEXT} because missing")
    result = synthesize_generative("q", [scored], completer=completer)
    assert result.insufficient_context is True


def test_prompt_includes_chunk_metadata():
    chunk = Chunk(
        chunk_id="groww-nippon#001",
        source_id="groww-nippon-india-value-fund-direct-growth",
        text="Min. for SIP INR 100",
        effective_date=date(2026, 7, 24),
    )
    scored = ScoredChunk(chunk=chunk, source_id=chunk.source_id)
    user = build_user_prompt("minimum SIP?", [scored])
    assert "groww-nippon#001" in user
    assert "Min. for SIP INR 100" in user


@pytest.mark.skipif(not PROCESSED.is_dir(), reason="processed corpus missing")
def test_answer_query_rag_calls_llm():
    completer = MockCompleter(
        "The expense ratio of Nippon India Value Fund Direct Growth is 1.27%."
    )
    result = answer_query(
        "What is the expense ratio of Nippon India Value Fund Direct Growth?",
        processed_root=PROCESSED,
        completer=completer,
    )
    assert result.path in {SynthesisPath.GENERATIVE, SynthesisPath.FACT_CARD}
    assert result.route == AnswerRoute.FACTUAL
    assert result.used_llm is True
    assert "1.27%" in result.answer_text
    assert completer.calls
    assert "CONTEXT" in completer.calls[0]["user"] or "expense" in completer.calls[0]["user"].lower()


def test_fact_card_llm_falls_back_when_value_dropped():
    from core.synthesis.pipeline import synthesize_fact_card_with_llm

    fact = FactCard(
        fact_key="expense_ratio",
        scheme_name="Nippon India Value Fund Direct Growth",
        value_text="1.27%",
        source_id="groww-nippon-india-value-fund-direct-growth",
        chunk_id="groww-nippon-india-value-fund-direct-growth#002",
        effective_date=date(2026, 7, 24),
        verified_by_human=True,
    )
    completer = MockCompleter("The expense ratio is low.")
    result = synthesize_fact_card_with_llm(fact, "expense ratio?", completer=completer)
    assert result.used_llm is False
    assert "1.27%" in result.answer_text


def test_fact_card_llm_falls_back_when_nav_as_of_dropped():
    from core.synthesis.pipeline import synthesize_fact_card_with_llm

    fact = FactCard(
        fact_key="nav",
        scheme_name="Nippon India Value Fund Direct Growth",
        value_text="₹250.01 (as of 31 Jul 2026)",
        source_id="groww-nippon-india-value-fund-direct-growth",
        chunk_id="groww-nippon-india-value-fund-direct-growth#001",
        effective_date=date(2026, 7, 31),
        verified_by_human=True,
    )
    completer = MockCompleter(
        "The NAV of Nippon India Value Fund Direct Growth is ₹250.01."
    )
    result = synthesize_fact_card_with_llm(fact, "NAV?", completer=completer)
    assert result.used_llm is False
    assert "₹250.01 (as of 31 Jul 2026)" in result.answer_text


def test_answer_query_refusal_skips_llm():
    completer = MockCompleter("nope")
    result = answer_query(
        "Should I invest in Nippon India Value Fund?",
        completer=completer,
    )
    assert result.path == SynthesisPath.ROUTER
    assert result.route == AnswerRoute.REFUSAL
    assert not completer.calls
