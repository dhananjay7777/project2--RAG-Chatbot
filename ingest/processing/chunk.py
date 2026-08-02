"""Structure-aware chunker for Groww scheme pages."""

from __future__ import annotations

import re
from datetime import date

from ingest.processing.models import ParsedDocument, Section
from ingest.processing.normalize import normalize_for_index
from ingest.processing.pii import scrub_pii
from schemas.chunk import Chunk

TARGET_TOKENS = 300
MIN_TOKENS = 40
MAX_TOKENS = 450
OVERLAP_RATIO = 0.15

_FACT_TAG_HINTS = {
    "expense_ratio": [r"expense ratio", r"\bter\b"],
    "exit_load": [r"exit load"],
    "min_sip": [r"min(?:imum)?\.?\s*(?:for\s*)?sip", r"minimum sip"],
    "min_lumpsum": [r"1st investment", r"lumpsum", r"minimum lumpsum"],
    "risk_rating": [r"very high risk", r"risk rating", r"riskometer"],
    "benchmark": [r"fund benchmark", r"benchmark"],
    "aum": [r"\baum\b", r"fund size", r"assets under management"],
    "nav": [r"\bnav\b"],
    "stamp_duty": [r"stamp duty"],
    "tax_implication_text": [r"tax implication"],
    "investment_objective": [r"investment objective"],
    "fund_manager": [r"fund manager", r"fund management"],
    "launch_date": [r"launch date", r"made available to investors"],
    "category": [r"equity", r"hybrid", r"multi asset", r"mid cap", r"multi cap"],
}


def _token_count(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text)))


def _fact_tags(text: str, heading_path: list[str]) -> list[str]:
    blob = " ".join(heading_path + [text]).lower()
    tags: list[str] = []
    for key, patterns in _FACT_TAG_HINTS.items():
        if any(re.search(p, blob, re.I) for p in patterns):
            tags.append(key)
    return tags


def _split_keep_exit_load(text: str) -> list[str]:
    """Split on blank lines but keep exit-load rate+window together."""

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return [text] if text.strip() else []

    merged: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        # Never split a percentage from a redemption window clause
        if buf and re.search(r"\d+(?:\.\d+)?\s*%", buf) and re.search(
            r"within\s+\d+\s+(?:day|month|year)", para, re.I
        ):
            buf = candidate
            continue
        if _token_count(candidate) <= MAX_TOKENS:
            buf = candidate
        else:
            if buf:
                merged.append(buf)
            buf = para
    if buf:
        merged.append(buf)
    return merged


def _window_with_overlap(parts: list[str]) -> list[str]:
    if not parts:
        return []
    windows: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for part in parts:
        part_tokens = _token_count(part)
        if current and current_tokens + part_tokens > TARGET_TOKENS:
            windows.append("\n\n".join(current))
            # overlap: keep last part if small
            if current and _token_count(current[-1]) <= int(TARGET_TOKENS * OVERLAP_RATIO) + 20:
                current = [current[-1], part]
                current_tokens = _token_count("\n\n".join(current))
            else:
                current = [part]
                current_tokens = part_tokens
        else:
            current.append(part)
            current_tokens += part_tokens
    if current:
        windows.append("\n\n".join(current))
    return windows


def chunk_document(doc: ParsedDocument) -> list[Chunk]:
    chunks: list[Chunk] = []
    seq = 0
    for section in doc.sections:
        pieces = _split_keep_exit_load(section.text)
        windows = _window_with_overlap(pieces) or (
            [section.text] if section.text.strip() else []
        )
        for window in windows:
            normalized = normalize_for_index(window)
            pii = scrub_pii(normalized)
            # Indexable set requires clean or redacted; quarantine excluded later
            seq += 1
            chunk_id = f"{doc.source_id}#{seq:03d}"
            heading = section.heading_path or [section.heading]
            text_for_tags = pii.text
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    source_id=doc.source_id,
                    text=pii.text,
                    heading_path=heading,
                    page=None,
                    url_anchor=None,
                    fact_tags=_fact_tags(text_for_tags, heading),
                    contains_table="|" in window,
                    effective_date=doc.effective_date,
                    token_count=_token_count(pii.text),
                    pii_scan=pii.pii_scan,
                )
            )
    return chunks


def active_chunks(chunks: list[Chunk]) -> list[Chunk]:
    return [c for c in chunks if c.pii_scan != "quarantined"]
