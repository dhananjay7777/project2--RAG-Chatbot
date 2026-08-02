"""Phase 9 freshness orchestration (fail-closed live refresh)."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ingest.acquisition.models import AcquisitionManifest
from ingest.acquisition.storage import RawArtifactStore
from ingest.fetch import fetch_all
from ingest.registry import validate_registry

LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = ROOT / "data" / "raw"
DEFAULT_REPORT = ROOT / "data" / "raw" / "refresh_report.json"


@dataclass
class SourceChange:
    source_id: str
    previous_sha256: str | None
    new_sha256: str | None
    changed: bool


@dataclass
class RefreshReport:
    run_at: str
    promotion_ready: bool
    active_sources: int
    headless_used: bool
    sources: list[SourceChange] = field(default_factory=list)
    changed_count: int = 0
    unchanged_count: int = 0
    process_ok: bool = False
    index_ok: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        return payload


def _sha_map(manifest: AcquisitionManifest | None) -> dict[str, str]:
    if manifest is None:
        return {}
    out: dict[str, str] = {}
    for record in manifest.records:
        src = record.source
        if src.content_sha256:
            out[src.source_id] = src.content_sha256
    return out


def _diff_sources(
    before: dict[str, str],
    after: AcquisitionManifest,
) -> list[SourceChange]:
    changes: list[SourceChange] = []
    after_map = _sha_map(after)
    source_ids = sorted(set(before) | set(after_map))
    for sid in source_ids:
        prev = before.get(sid)
        new = after_map.get(sid)
        changes.append(
            SourceChange(
                source_id=sid,
                previous_sha256=prev,
                new_sha256=new,
                changed=prev != new,
            )
        )
    return changes


def _run_step(label: str, argv: list[str]) -> None:
    LOGGER.info("Freshness step: %s (%s)", label, " ".join(argv))
    completed = subprocess.run(
        argv,
        cwd=str(ROOT),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Freshness step failed: {label} (exit {completed.returncode})")


def refresh_corpus(
    *,
    raw_root: Path = DEFAULT_RAW,
    headless: bool = False,
    headless_on_http_failure: bool = True,
    run_process: bool = True,
    run_index: bool = True,
    report_path: Path = DEFAULT_REPORT,
) -> RefreshReport:
    """Live fetch → validate --live → process → index (fail-closed).

    Ask-time serving never calls this. Partial corpora are not promoted.
    """

    store = RawArtifactStore(raw_root)
    before = _sha_map(store.load_latest(live_only=True))
    headless_used = False
    notes: list[str] = []

    try:
        fetch_all(raw_root, use_headless_fallback=headless)
        if headless:
            headless_used = True
    except Exception as http_exc:
        if not headless_on_http_failure or headless:
            raise
        notes.append(
            f"HTTP fetch failed ({http_exc}); retrying with headless Chromium"
        )
        LOGGER.warning("%s", notes[-1])
        fetch_all(raw_root, use_headless_fallback=True)
        headless_used = True

    live = validate_registry(raw_root, require_live=True)
    if not live.promotion_ready or live.active_count != 5:
        raise RuntimeError(
            "Freshness refuse to promote: live corpus incomplete "
            f"(active={live.active_count}, promotion_ready={live.promotion_ready})"
        )

    sources = _diff_sources(before, live)
    changed = sum(1 for s in sources if s.changed)
    unchanged = len(sources) - changed

    report = RefreshReport(
        run_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        promotion_ready=True,
        active_sources=live.active_count,
        headless_used=headless_used,
        sources=sources,
        changed_count=changed,
        unchanged_count=unchanged,
        notes=notes,
    )

    if run_process:
        _run_step("process", [sys.executable, "-m", "ingest.processing", "process"])
        report.process_ok = True
    if run_index:
        _run_step("index", [sys.executable, "-m", "ingest.indexing", "build"])
        report.index_ok = True

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    LOGGER.info(
        "Freshness complete: changed=%s unchanged=%s headless=%s report=%s",
        changed,
        unchanged,
        headless_used,
        report_path,
    )
    return report
