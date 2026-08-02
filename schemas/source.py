"""SourceRecord — one row per curated URL (provenance root + citation allowlist)."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class DocType(str, Enum):
    GROWW_SCHEME_PAGE = "GROWW_SCHEME_PAGE"


class SourceStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    FETCH_FAILED = "fetch_failed"


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(..., min_length=1)
    url: HttpUrl
    publisher: str = Field(default="Groww")
    amc: str
    authority_tier: int = Field(default=1, ge=1, le=1)
    doc_type: DocType = DocType.GROWW_SCHEME_PAGE
    scheme_names: list[str] = Field(..., min_length=1)
    isin: list[str] = Field(default_factory=list)
    effective_date: Optional[date] = None
    fetched_at: Optional[datetime] = None
    content_sha256: Optional[str] = None
    parser_version: str = "1.0.0"
    status: SourceStatus = SourceStatus.ACTIVE
    supersedes: Optional[str] = None
    artifact_path: Optional[str] = None
    fetch_mode: Optional[Literal["http", "headless", "snapshot"]] = None
    final_url: Optional[HttpUrl] = None
    last_error: Optional[str] = None

    @field_validator("doc_type")
    @classmethod
    def only_groww_scheme_page(cls, v: DocType) -> DocType:
        if v != DocType.GROWW_SCHEME_PAGE:
            raise ValueError("Only GROWW_SCHEME_PAGE is valid for this corpus")
        return v
