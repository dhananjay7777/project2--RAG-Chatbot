"""Phase 5: Constrained synthesis (Groq for generative answers)."""

from core.synthesis.models import INSUFFICIENT_CONTEXT, SynthesisResult
from core.synthesis.orchestrator import answer_query
from core.synthesis.pipeline import (
    fact_as_scored_chunk,
    synthesize_fact_card,
    synthesize_fact_card_with_llm,
    synthesize_generative,
)
from core.retrieval.models import ScoredChunk

__all__ = [
    "INSUFFICIENT_CONTEXT",
    "SynthesisResult",
    "answer_query",
    "synthesize",
    "fact_as_scored_chunk",
    "synthesize_fact_card",
    "synthesize_fact_card_with_llm",
    "synthesize_generative",
]


def synthesize(query: str, chunks: list[ScoredChunk]) -> SynthesisResult:
    """Generative RAG synthesis via Groq (retrieve → LLM)."""
    return synthesize_generative(query, chunks)
