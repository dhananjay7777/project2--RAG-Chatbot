"""PII detection for routing (refuse + redact)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ingest.processing.pii import load_pii_patterns, scrub_pii


@dataclass(frozen=True)
class RouterPiiScan:
    must_refuse: bool
    sanitized_query: str
    hits: list[str]


_REFUSE_KINDS = frozenset({"pan", "aadhaar", "account_number", "otp", "email", "phone"})


def scan_query_pii(query: str) -> RouterPiiScan:
    patterns = load_pii_patterns()
    result = scrub_pii(query, patterns)
    must_refuse = bool(result.hits) and any(h in _REFUSE_KINDS for h in result.hits)
    # Also refuse if PAN-like token remains after scrub in identity context
    if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", query, re.I):
        must_refuse = True
    return RouterPiiScan(
        must_refuse=must_refuse,
        sanitized_query=result.text,
        hits=list(result.hits),
    )
