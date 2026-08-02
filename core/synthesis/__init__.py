"""Phase 5 constrained synthesis."""

from core.synthesis.models import INSUFFICIENT_CONTEXT, SynthesisResult
from core.synthesis.orchestrator import answer_query
from core.synthesis.pipeline import synthesize_fact_card, synthesize_generative

__all__ = [
    "INSUFFICIENT_CONTEXT",
    "SynthesisResult",
    "answer_query",
    "synthesize_fact_card",
    "synthesize_generative",
]
