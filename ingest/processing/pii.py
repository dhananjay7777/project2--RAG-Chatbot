"""PII scrub using policy/pii_patterns.yaml."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from policy import POLICY_DIR


@dataclass
class PiiResult:
    text: str
    pii_scan: str  # clean | redacted | quarantined
    hits: list[str]


def load_pii_patterns(path: Path | None = None) -> dict[str, Any]:
    path = path or (POLICY_DIR / "pii_patterns.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def scrub_pii(text: str, patterns: dict[str, Any] | None = None) -> PiiResult:
    patterns = patterns or load_pii_patterns()
    hits: list[str] = []
    out = text

    # Order: identity-bearing first
    for name in ("pan", "aadhaar", "email", "phone", "account_number", "otp"):
        spec = patterns.get("patterns", {}).get(name)
        if not spec:
            continue
        flags = re.IGNORECASE if "IGNORECASE" in (spec.get("flags") or []) else 0
        regex = re.compile(spec["regex"], flags)
        ctx_keys = [k.lower() for k in (spec.get("requires_context_keywords") or [])]

        def _repl(match: re.Match[str], *, kind: str = name) -> str:
            if ctx_keys:
                window = out[max(0, match.start() - 40) : match.end() + 40].lower()
                if not any(k in window for k in ctx_keys):
                    return match.group(0)
            hits.append(kind)
            return f"[REDACTED:{kind.upper()}]"

        out, n = regex.subn(_repl, out)
        if n and name not in hits:
            hits.append(name)

    if not hits:
        return PiiResult(text=out, pii_scan="clean", hits=[])
    # Quarantine only if unretracted identity tokens remain (should not happen)
    if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", out, re.I):
        return PiiResult(text=out, pii_scan="quarantined", hits=hits)
    return PiiResult(text=out, pii_scan="redacted", hits=hits)
