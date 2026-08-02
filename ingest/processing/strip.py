"""Strip forbidden Groww sections before chunking/indexing."""

from __future__ import annotations

import re

from ingest.processing.models import ParsedDocument, Section

_STRIP_HEADING_PATTERNS = (
    r"^return calculator$",
    r"^returns and rankings$",
    r"^holdings?\b",
    r"^also manages these schemes$",
    r"^compare funds$",
    r"^mutual funds screener$",
    r"^understand terms$",  # generic glossary; definitions not scheme facts
    r"^annualised returns$",
    r"^absolute returns$",
)

_STRIP_TEXT_MARKERS = (
    r"###\s+Return calculator",
    r"##\s+Holdings",
    r"Also manages these schemes",
    r"Compare Funds",
    r"###\s+Returns and rankings",
)


def _should_strip_heading(heading: str) -> bool:
    h = heading.strip().lower()
    return any(re.search(pat, h, re.I) for pat in _STRIP_HEADING_PATTERNS)


def strip_document(doc: ParsedDocument) -> ParsedDocument:
    """Remove returns/holdings/related-fund sections from parsed document."""

    kept: list[Section] = []
    for section in doc.sections:
        if _should_strip_heading(section.heading):
            continue
        # Drop related-fund farms inside fund management sections
        text = section.text
        text = re.split(r"(?i)Also manages these schemes", text, maxsplit=1)[0].strip()
        # Drop trailing Groww chrome / footer after Home>Mutual Funds
        text = re.split(r"(?i)Home\s*>\s*Mutual Funds", text, maxsplit=1)[0].strip()
        if not text and section.heading.lower() in {"preamble"}:
            # Keep trimmed preamble (hero metrics live here)
            text = section.text
            for marker in _STRIP_TEXT_MARKERS:
                text = re.split(marker, text, maxsplit=1, flags=re.I)[0].strip()
        if not text:
            continue
        kept.append(section.model_copy(update={"text": text}))

    # Also trim raw_text for fact heuristics that scan full document
    raw = doc.raw_text
    for marker in (
        r"###\s+Return calculator[\s\S]*?(?=###\s+Minimum investments|##\s+Holdings|###\s+Exit Load|$)",
        r"##\s+Holdings[\s\S]*?(?=###\s+Minimum investments|##\s+Understand terms|###\s+Exit Load|$)",
        r"###\s+Returns and rankings[\s\S]*?(?=##\s+Understand terms|###\s+Exit Load|$)",
        r"(?i)Also manages these schemes[\s\S]*?(?=###\s+About |###\s+Fund house|$)",
    ):
        raw = re.sub(marker, "\n", raw)

    return doc.model_copy(update={"sections": kept, "raw_text": raw})


def strip_audit_violations(chunks_text: str) -> list[str]:
    """Return forbidden markers still present in chunk corpus text."""

    violations: list[str] = []
    lowered = chunks_text.lower()
    checks = {
        "return calculator": "return calculator",
        "returns and rankings": "returns and rankings",
        "also manages these schemes": "also manages these schemes",
        "holdings table remnant": "| assets  |",
    }
    for name, needle in checks.items():
        if needle in lowered:
            violations.append(name)
    return violations
