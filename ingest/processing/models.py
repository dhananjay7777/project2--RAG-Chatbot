"""Phase 2 processing models."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    heading_path: list[str] = Field(default_factory=list)
    text: str
    level: int = 2


class ParsedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    scheme_name: str
    effective_date: Optional[date] = None
    raw_text: str
    sections: list[Section] = Field(default_factory=list)
    hero_metrics: dict[str, str] = Field(default_factory=dict)
    embedded_json: dict[str, Any] = Field(default_factory=dict)
    content_format: str = "markdown"  # markdown | html


class ProcessingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    scheme_name: str
    chunk_count: int
    fact_count: int
    quarantined_chunks: int
    verified_facts: int
    null_facts: int
