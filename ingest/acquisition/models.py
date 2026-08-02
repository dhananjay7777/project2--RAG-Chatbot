"""Phase 1 acquisition contracts.

These models describe one fetch attempt and the immutable manifest produced by a
complete corpus run. They are separate from the policy registry: policy declares
what may be fetched; a manifest records what was actually fetched.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.source import SourceRecord


class FetchPayload(BaseModel):
    """Validated bytes returned by HTTP, headless browser, or snapshot input."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    content: bytes
    final_url: str
    mode: Literal["http", "headless", "snapshot"]
    content_type: str = "text/html"


class AcquisitionRecord(BaseModel):
    """Runtime state for one frozen source."""

    model_config = ConfigDict(extra="forbid")

    source: SourceRecord
    changed: bool = True
    previous_content_sha256: str | None = None


class AcquisitionManifest(BaseModel):
    """Atomic record of one five-source acquisition run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    generated_at: datetime
    promotion_ready: bool
    records: list[AcquisitionRecord] = Field(..., min_length=5, max_length=5)

    @property
    def active_count(self) -> int:
        return sum(record.source.status.value == "active" for record in self.records)
