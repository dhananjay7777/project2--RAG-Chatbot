"""Validation context passed through the validator chain."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from uuid import UUID

from schemas.answer import AnswerRoute


@dataclass
class ValidationContext:
    query_id: UUID
    route: AnswerRoute
    answer_body: str
    citation_url: str
    citation_label: str
    source_id: str
    chunk_id: Optional[str] = None
    footer: str = ""
    confidence: float = 0.9
    supporting_texts: list[str] = field(default_factory=list)
    effective_dates: list[date] = field(default_factory=list)
    fact_key: Optional[str] = None
    scheme_name: Optional[str] = None
    skip_groundedness: bool = False
    timings_ms: dict[str, int] = field(default_factory=dict)
