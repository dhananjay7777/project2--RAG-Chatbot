"""Router decision models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from schemas.answer import AnswerRoute


class RouteDecision(BaseModel):
    intent: str
    route: AnswerRoute
    confidence: float = Field(..., ge=0.0, le=1.0)
    tier: int = Field(..., ge=1, le=2)
    sanitized_query: str
    response_text: Optional[str] = None
    citation_url: str
    citation_label: str
    source_id: str
    pii_redacted: bool = False
