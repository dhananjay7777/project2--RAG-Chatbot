"""Post-rerank confidence gate."""

from __future__ import annotations

from core.retrieval.models import RetrievalStatus, ScoredChunk


def apply_confidence_gate(
    ranked: list[ScoredChunk],
    *,
    tau: float,
    scheme_margin_epsilon: float,
    scheme_confident: bool,
    ambiguous_multi_asset: bool,
) -> tuple[RetrievalStatus, str | None]:
    if ambiguous_multi_asset and not scheme_confident:
        return RetrievalStatus.CLARIFY, "ambiguous_scheme"

    if not ranked:
        return RetrievalStatus.NO_ANSWER, "empty_candidates"

    top = ranked[0]
    if top.rerank_score is None or top.rerank_score < tau:
        return RetrievalStatus.NO_ANSWER, "low_rerank_score"

    if len(ranked) >= 2:
        second = ranked[1]
        if (
            top.source_id != second.source_id
            and top.rerank_score is not None
            and second.rerank_score is not None
        ):
            margin = top.rerank_score - second.rerank_score
            if margin < scheme_margin_epsilon:
                if ambiguous_multi_asset or not scheme_confident:
                    return RetrievalStatus.CLARIFY, "cross_scheme_margin"
                return RetrievalStatus.NO_ANSWER, "cross_scheme_margin"

    return RetrievalStatus.OK, None


def tie_break_reranked(chunks: list[ScoredChunk]) -> list[ScoredChunk]:
    def sort_key(item: ScoredChunk) -> tuple:
        eff = item.chunk.effective_date.isoformat() if item.chunk.effective_date else ""
        score = item.rerank_score if item.rerank_score is not None else -1.0
        return (score, eff)

    return sorted(chunks, key=sort_key, reverse=True)
