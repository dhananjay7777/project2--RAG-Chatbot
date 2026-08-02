"""Phase 3 index build models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ChunkIndexRecord(BaseModel):
    chunk_id: str
    source_id: str
    scheme_name: str
    status: str = "active"
    doc_type: str = "GROWW_SCHEME_PAGE"
    text: str
    index_text: str
    fact_tags: list[str] = Field(default_factory=list)
    effective_date: Optional[str] = None
    content_hash: str


class IndexManifest(BaseModel):
    embedding_model: str
    chunk_count: int
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    records: dict[str, str] = Field(default_factory=dict)  # chunk_id -> content_hash
