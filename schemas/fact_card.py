"""FactCard — verified fact layer (LLM phrasing + deterministic fallback)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field


class FactCard(BaseModel):
    fact_key: str
    scheme_name: str
    value_text: Optional[str] = None
    value_structured: Optional[dict[str, Any]] = None
    source_id: str
    chunk_id: Optional[str] = None
    effective_date: Optional[date] = None
    extraction_method: str = "regex+llm_verified"
    verified_by_human: bool = False
