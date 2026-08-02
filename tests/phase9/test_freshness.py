"""Phase 9 — freshness scheduler contracts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ingest.acquisition.models import AcquisitionManifest, AcquisitionRecord
from schemas.source import SourceRecord, SourceStatus

ROOT = Path(__file__).resolve().parents[2]


def _record(source_id: str, digest: str) -> AcquisitionRecord:
    return AcquisitionRecord(
        source=SourceRecord(
            source_id=source_id,
            url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
            amc="Test AMC",
            scheme_names=["Nippon India Value Fund Direct Growth"],
            content_sha256=digest,
            effective_date=datetime(2026, 7, 24).date(),
            status=SourceStatus.ACTIVE,
            fetch_mode="http",
        )
    )


def test_corpus_refresh_workflow_exists_and_schedules_daily_ist():
    path = ROOT / ".github" / "workflows" / "corpus-refresh.yml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    # Daily 10:00 AM IST = 04:30 UTC
    assert 'cron: "30 4 * * *"' in text or "cron: '30 4 * * *'" in text
    assert "workflow_dispatch" in text
    assert "concurrency:" in text
    assert "corpus-refresh" in text
    assert "python -m ingest.freshness refresh" in text
    assert "contents: write" in text


def test_makefile_refresh_uses_freshness_module():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "python -m ingest.freshness refresh" in makefile
    assert "\nrefresh:" in makefile


def test_freshness_sla_days_match_architecture():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    sla = cfg["freshness_sla_days"]
    assert sla["nav"] == 7
    assert sla["expense_ratio"] == 7
    assert sla["aum"] == 7
    assert sla["exit_load"] == 30
    assert sla["min_sip"] == 30
    assert sla["benchmark"] == 30
    assert sla["fund_manager"] == 90
    assert sla["investment_objective"] == 90
    assert sla["category"] == 90


def test_registry_cardinality_is_five():
    from ingest.acquisition.registry import load_source_definitions

    defs = load_source_definitions()
    assert len(defs) == 5


def test_diff_sources_detects_sha_changes():
    from datetime import timezone

    from ingest.freshness.pipeline import _diff_sources

    after = AcquisitionManifest(
        run_id="run-test",
        generated_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        promotion_ready=True,
        records=[
            _record("a", "sha-new"),
            _record("b", "sha-same"),
            _record("c", "sha-c"),
            _record("d", "sha-d"),
            _record("e", "sha-e"),
        ],
    )
    before = {"a": "sha-old", "b": "sha-same"}
    changes = {c.source_id: c for c in _diff_sources(before, after)}
    assert changes["a"].changed is True
    assert changes["b"].changed is False
    assert changes["c"].changed is True


def test_refresh_refuses_incomplete_live_corpus(tmp_path: Path):
    from ingest.freshness.pipeline import refresh_corpus

    fake_live = MagicMock()
    fake_live.promotion_ready = False
    fake_live.active_count = 4

    with (
        patch("ingest.freshness.pipeline.fetch_all", return_value=MagicMock()),
        patch(
            "ingest.freshness.pipeline.validate_registry",
            return_value=fake_live,
        ),
        patch("ingest.freshness.pipeline.RawArtifactStore") as store_cls,
    ):
        store_cls.return_value.load_latest.return_value = None
        with pytest.raises(RuntimeError, match="refuse to promote"):
            refresh_corpus(
                raw_root=tmp_path,
                headless_on_http_failure=False,
                run_process=False,
                run_index=False,
                report_path=tmp_path / "refresh_report.json",
            )


def test_refresh_writes_report_on_success(tmp_path: Path):
    from datetime import timezone

    from ingest.freshness.pipeline import refresh_corpus

    live = AcquisitionManifest(
        run_id="run-ok",
        generated_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        promotion_ready=True,
        records=[_record(f"src-{i}", f"sha-{i}") for i in range(5)],
    )

    with (
        patch("ingest.freshness.pipeline.fetch_all", return_value=live),
        patch(
            "ingest.freshness.pipeline.validate_registry",
            return_value=live,
        ),
        patch("ingest.freshness.pipeline.RawArtifactStore") as store_cls,
        patch("ingest.freshness.pipeline._run_step") as run_step,
    ):
        store_cls.return_value.load_latest.return_value = None
        report_path = tmp_path / "refresh_report.json"
        report = refresh_corpus(
            raw_root=tmp_path,
            headless_on_http_failure=False,
            run_process=True,
            run_index=True,
            report_path=report_path,
        )
        assert report.promotion_ready is True
        assert report.active_sources == 5
        assert report.changed_count == 5
        assert report.process_ok is True
        assert report.index_ok is True
        assert report_path.is_file()
        assert run_step.call_count == 2


def test_validate_live_flag_exists_for_snapshot_rejection():
    """P9-08: live validation must be available to reject snapshot manifests."""
    from ingest.acquisition.cli import _parser

    parser = _parser()
    args = parser.parse_args(["validate", "--live"])
    assert args.live is True
