"""Log-time PII redaction (second layer behind the input sanitizer)."""

from __future__ import annotations

import re
from typing import Any

from ingest.processing.pii import load_pii_patterns, scrub_pii

# Patterns that are safe to scan in structured JSON without context cues.
_LOG_AUDIT_NAMES = ("pan", "aadhaar", "email", "phone")


def redact_text(text: str) -> str:
    """Replace PII-like spans before any log write."""

    return scrub_pii(text).text


def _audit_patterns() -> list[re.Pattern[str]]:
    specs = load_pii_patterns().get("patterns") or {}
    out: list[re.Pattern[str]] = []
    for name in _LOG_AUDIT_NAMES:
        spec = specs.get(name)
        if not spec:
            continue
        flags = re.IGNORECASE if "IGNORECASE" in (spec.get("flags") or []) else 0
        out.append(re.compile(spec["regex"], flags))
    return out


def assert_no_raw_pii(payload: dict[str, Any]) -> None:
    """Raise if a structured log payload still contains raw high-confidence PII.

    `query_hash` is excluded — hex digests can accidentally match digit-run patterns.
    """

    scan: dict[str, Any] = {
        key: value
        for key, value in payload.items()
        if key not in {"query_hash", "query_id", "retrieval_scores", "timings_ms"}
    }
    blob = str(scan)
    for pattern in _audit_patterns():
        if pattern.search(blob):
            raise ValueError("structured log payload contains raw PII pattern")
