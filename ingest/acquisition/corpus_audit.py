"""Scan raw corpus artifacts for Groww "Advanced ratios" content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ingest.registry import validate_registry

# Visible UI labels (browser / readable export)
UI_BLOCK_MARKERS = (
    r"Advanced ratios",
    r"Top 5",
    r"Top 20",
    r"P/E Ratio",
    r"P/B Ratio",
)

# Embedded in initial HTML payload (static JSON — no extra API URL in Phase 1)
EMBEDDED_JSON_MARKERS = (
    r'"sharpe_ratio"\s*:',
    r'"sortino[^"]*"\s*:',
    r'"pe_ratio"\s*:',
    r'"pb_ratio"\s*:',
    r'"beta"\s*:',
    r'"alpha"\s*:',
)

_NAV_NOISE = re.compile(
    r"MF Knowledge Centre|Nifty Alpha \d+|Alpha \d+ Index Fund",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SourceAuditRow:
    source_id: str
    artifact_path: str
    ui_advanced_block: bool
    embedded_metrics_json: bool
    ui_markers: tuple[str, ...]
    json_markers: tuple[str, ...]

    @property
    def any_advanced_ratios_signal(self) -> bool:
        return self.ui_advanced_block or self.embedded_metrics_json


def _text_from_artifact(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


def _scan_markers(text: str, patterns: tuple[str, ...]) -> list[str]:
    cleaned = _NAV_NOISE.sub(" ", text)
    return [p for p in patterns if re.search(p, cleaned, re.IGNORECASE)]


def audit_raw_corpus(raw_root: Path) -> list[SourceAuditRow]:
    manifest = validate_registry(raw_root, require_live=False)
    rows: list[SourceAuditRow] = []
    for record in manifest.records:
        source = record.source
        artifact = raw_root / (source.artifact_path or "")
        text = _text_from_artifact(artifact)
        ui = _scan_markers(text, UI_BLOCK_MARKERS)
        js = _scan_markers(text, EMBEDDED_JSON_MARKERS)
        rows.append(
            SourceAuditRow(
                source_id=source.source_id,
                artifact_path=source.artifact_path or "",
                ui_advanced_block=bool(ui),
                embedded_metrics_json=bool(js),
                ui_markers=tuple(ui),
                json_markers=tuple(js),
            )
        )
    return rows


def summarize_advanced_ratios(rows: list[SourceAuditRow]) -> str:
    ui_count = sum(r.ui_advanced_block for r in rows)
    json_count = sum(r.embedded_metrics_json for r in rows)
    if ui_count == 0 and json_count == 0:
        return (
            "No Advanced ratios UI block or embedded metric JSON in stored artifacts "
            "(typical for markdown bootstrap snapshots)."
        )
    if ui_count and json_count:
        return (
            f"Advanced ratios signals in {ui_count} UI / {json_count} JSON artifact(s)."
        )
    if json_count:
        return (
            f"Embedded metric JSON in {json_count}/5 artifacts; UI labels may still "
            "require browser render. Re-fetch live HTML (make ingest) for Phase 2 parsing."
        )
    return f"UI Advanced ratios labels in {ui_count}/5 artifacts."
