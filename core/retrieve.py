"""Phase 3 hybrid retrieval entrypoint."""

from __future__ import annotations

from functools import lru_cache

from core.retrieval.hybrid import HybridRetriever
from core.retrieval.models import RetrievalResult


@lru_cache(maxsize=1)
def _default_retriever() -> HybridRetriever:
    return HybridRetriever.from_disk()


def retrieve(query: str) -> RetrievalResult:
    """Run hybrid retrieval (BM25 + dense + rerank + confidence gate)."""
    return _default_retriever().retrieve(query)
