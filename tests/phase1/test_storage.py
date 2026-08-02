"""P1-05, P1-06, P1-12: immutable content-addressed raw storage."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ingest.acquisition.models import AcquisitionManifest, AcquisitionRecord
from ingest.acquisition.storage import RawArtifactStore, StorageError
from schemas.source import SourceRecord, SourceStatus


def _record(
    source_id: str,
    artifact_path: str,
    digest: str,
    *,
    status: SourceStatus = SourceStatus.ACTIVE,
) -> AcquisitionRecord:
    source = SourceRecord(
        source_id=source_id,
        url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
        amc="Test AMC",
        scheme_names=["Nippon India Value Fund Direct Growth"],
        content_sha256=digest,
        effective_date=datetime(2026, 7, 24).date(),
        status=status,
        artifact_path=artifact_path,
        fetch_mode="snapshot",
    )
    return AcquisitionRecord(source=source, changed=True)


def test_write_artifact_is_immutable(tmp_path):
    store = RawArtifactStore(tmp_path)
    content = b"<html>" + b"x" * 1200 + b"</html>"
    d1, p1, created1 = store.write_artifact("groww-nippon-india-value-fund-direct-growth", content, suffix=".html")
    d2, p2, created2 = store.write_artifact("groww-nippon-india-value-fund-direct-growth", content, suffix=".html")
    assert d1 == d2
    assert p1 == p2
    assert created1 is True
    assert created2 is False
    assert (tmp_path / p1).read_bytes() == content


def test_refuses_empty_artifact(tmp_path):
    store = RawArtifactStore(tmp_path)
    with pytest.raises(StorageError, match="empty"):
        store.write_artifact("groww-nippon-india-value-fund-direct-growth", b"", suffix=".html")


def test_manifest_latest_only_when_five_active(tmp_path):
    store = RawArtifactStore(tmp_path)
    records = [
        _record(
            source_id,
            f"{source_id}/deadbeef.html",
            "abc",
            status=SourceStatus.ACTIVE if idx == 0 else SourceStatus.FETCH_FAILED,
        )
        for idx, source_id in enumerate(
            [
                "groww-nippon-india-value-fund-direct-growth",
                "groww-tata-multi-asset-allocation-fund-direct-growth",
                "groww-kotak-multi-asset-allocation-fund-direct-growth",
                "groww-franklin-india-multi-cap-fund-direct-growth",
                "groww-samco-mid-cap-fund-direct-growth",
            ]
        )
    ]
    incomplete = AcquisitionManifest(
        run_id="test-incomplete",
        generated_at=datetime.now(timezone.utc),
        promotion_ready=False,
        records=records,
    )
    store.write_manifest(incomplete)
    assert not (tmp_path / "latest.json").exists()
    assert (tmp_path / "runs" / "test-incomplete.json").exists()
