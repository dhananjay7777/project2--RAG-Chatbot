"""Validation result types."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class FailAction(str, Enum):
    PASS = "pass"
    REPAIR = "repair"
    HARD_FAIL = "hard_fail"


class CheckResult(BaseModel):
    validator: str
    passed: bool
    action: FailAction = FailAction.PASS
    reason: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class ChainResult(BaseModel):
    passed: bool
    checks: list[CheckResult] = Field(default_factory=list)
    repairs_applied: int = 0
    used_canned: bool = False
    hard_fail_reason: Optional[str] = None
