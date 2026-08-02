"""Phase 3 retrieval result types."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from schemas.chunk import Chunk


class RetrievalStatus(str, Enum):
    OK = "OK"
    NO_ANSWER = "NO_ANSWER"
    CLARIFY = "CLARIFY"


class ScoredChunk(BaseModel):
    chunk: Chunk
    bm25_rank: Optional[int] = None
    dense_rank: Optional[int] = None
    rrf_score: float = 0.0
    rerank_score: Optional[float] = None
    source_id: str
    scheme_name: str = ""


class RetrievalResult(BaseModel):
    status: RetrievalStatus
    query: str
    chunks: list[ScoredChunk] = Field(default_factory=list)
    reason: Optional[str] = None
    inferred_source_id: Optional[str] = None
    inferred_fact_tags: list[str] = Field(default_factory=list)
