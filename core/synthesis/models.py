"""Synthesis output models."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from schemas.answer import AnswerRoute
from schemas.fact_card import FactCard


class SynthesisPath(str, Enum):
    ROUTER = "router"
    FACT_CARD = "fact_card"
    GENERATIVE = "generative"
    RETRIEVAL_MISS = "retrieval_miss"


INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class SynthesisResult(BaseModel):
    path: SynthesisPath
    route: AnswerRoute
    answer_text: str = ""
    insufficient_context: bool = False
    citation_url: str
    citation_label: str
    source_id: str
    scheme_name: Optional[str] = None
    fact_key: Optional[str] = None
    fact_card: Optional[FactCard] = None
    supporting_chunk_ids: list[str] = Field(default_factory=list)
    effective_dates: list[date] = Field(default_factory=list)
    sentence_count: int = Field(default=0, ge=0)
    used_llm: bool = False
    timings_ms: dict[str, int] = Field(default_factory=dict)
