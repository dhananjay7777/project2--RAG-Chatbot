"""AnswerEnvelope — single response type across all routes."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


class AnswerRoute(str, Enum):
    FACTUAL = "FACTUAL"
    REFUSAL = "REFUSAL"
    PERFORMANCE_REDIRECT = "PERFORMANCE_REDIRECT"
    NO_ANSWER = "NO_ANSWER"
    CLARIFY = "CLARIFY"


class Citation(BaseModel):
    url: HttpUrl
    source_id: str
    chunk_id: Optional[str] = None
    label: str


class ValidatorReport(BaseModel):
    passed: bool
    checks: dict[str, Any] = Field(default_factory=dict)
    repairs: int = Field(default=0, ge=0)


class AnswerEnvelope(BaseModel):
    query_id: UUID
    route: AnswerRoute
    answer: str
    sentence_count: int = Field(..., ge=0, le=3)
    citation: Citation
    footer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    validator_report: ValidatorReport
    timings_ms: dict[str, int] = Field(default_factory=dict)

    @field_validator("footer")
    @classmethod
    def footer_prefix(cls, v: str) -> str:
        if not v.startswith("Last updated from sources:"):
            raise ValueError(
                'footer must start with "Last updated from sources:"'
            )
        return v

    @field_validator("sentence_count")
    @classmethod
    def max_three_sentences(cls, v: int) -> int:
        if v > 3:
            raise ValueError("sentence_count must be <= 3")
        return v
