"""Chunk — retrieval unit."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Chunk(BaseModel):
    chunk_id: str
    source_id: str
    text: str = Field(..., min_length=1)
    heading_path: list[str] = Field(default_factory=list)
    page: Optional[int] = None
    url_anchor: Optional[str] = None
    fact_tags: list[str] = Field(default_factory=list)
    contains_table: bool = False
    effective_date: Optional[date] = None
    token_count: int = Field(default=0, ge=0)
    pii_scan: str = "clean"

    @field_validator("pii_scan")
    @classmethod
    def pii_scan_values(cls, v: str) -> str:
        allowed = {"clean", "redacted", "quarantined"}
        if v not in allowed:
            raise ValueError(f"pii_scan must be one of {allowed}")
        return v
