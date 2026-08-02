"""P1-04, P1-05, P1-11: pipeline orchestration and fail-closed rules."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from ingest.acquisition.http import AcquisitionError
from ingest.acquisition.models import FetchPayload
from ingest.acquisition.pipeline import (
    CorpusIncompleteError,
    SnapshotDirectoryFetcher,
    acquire_corpus,
)
from ingest.acquisition.registry import validate_manifest
from ingest.acquisition.storage import RawArtifactStore
from ingest.acquisition.validation import ContentValidationError
from policy.loader import load_allowlist
from schemas.source import SourceStatus
from tests.phase1.helpers import MappingFetcher, html_page, markdown_page

ALLOWLIST = load_allowlist()
SCHEMES = {
    ALLOWLIST[0]: "Nippon India Value Fund Direct Growth",
    ALLOWLIST[1]: "Tata Multi Asset Allocation Fund Direct Growth",
    ALLOWLIST[2]: "Kotak Multi Asset Allocation Fund Direct Growth",
    ALLOWLIST[3]: "Franklin India Multi Cap Fund Direct Growth",
    ALLOWLIST[4]: "Samco Mid Cap Fund Direct Growth",
}


def _pages(mode: str = "http") -> dict[str, bytes]:
    return {
        url: html_page(name)
        for url, name in SCHEMES.items()
    }


class FailingFetcher:
    def __init__(self, fail_url: str):
        self.fail_url = fail_url
        self.inner = MappingFetcher(_pages())

    def fetch(self, url: str) -> FetchPayload:
        if url == self.fail_url:
            raise ContentValidationError("Sparse response (10 bytes); expected at least 1000")
        return self.inner.fetch(url)


def test_acquire_all_five_writes_manifest(tmp_path):
    store = RawArtifactStore(tmp_path)
    fixed = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
    tick = {"n": 0}

    def clock():
        tick["n"] += 1
        return fixed

    manifest = acquire_corpus(
        primary=MappingFetcher(_pages()),
        store=store,
        clock=clock,
    )
    assert manifest.active_count == 5
    assert manifest.promotion_ready is True
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "latest-live.json").exists()
    validate_manifest(manifest, tmp_path, require_live=True)
    for item in manifest.records:
        assert item.source.content_sha256
        assert item.source.effective_date
        assert item.source.artifact_path
        assert (tmp_path / item.source.artifact_path).is_file()


def test_partial_failure_raises_and_does_not_promote_latest(tmp_path):
    store = RawArtifactStore(tmp_path)
    fail_url = ALLOWLIST[0]
    with pytest.raises(CorpusIncompleteError) as exc:
        acquire_corpus(
            primary=FailingFetcher(fail_url),
            store=store,
            clock=lambda: datetime(2026, 7, 27, tzinfo=timezone.utc),
        )
    manifest = exc.value.manifest
    assert manifest.active_count == 4
    assert not (tmp_path / "latest.json").exists()
    failed = [r for r in manifest.records if r.source.status == SourceStatus.FETCH_FAILED]
    assert len(failed) == 1


def test_unchanged_re_fetch_marks_not_changed(tmp_path):
    store = RawArtifactStore(tmp_path)
    clock = lambda: datetime(2026, 7, 27, tzinfo=timezone.utc)
    pages = _pages()
    acquire_corpus(primary=MappingFetcher(pages), store=store, clock=clock)
    second = acquire_corpus(primary=MappingFetcher(pages), store=store, clock=clock)
    assert all(not r.changed for r in second.records)


def test_headless_fallback_used_on_sparse_primary(tmp_path):
    store = RawArtifactStore(tmp_path)
    sparse = MappingFetcher(
        {url: b"<h1>bad</h1>" for url in ALLOWLIST},
        mode="http",
    )
    good = MappingFetcher(_pages(), mode="headless")
    manifest = acquire_corpus(
        primary=sparse,
        fallback=good,
        store=store,
        clock=lambda: datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    assert manifest.active_count == 5
    assert all(r.source.fetch_mode == "headless" for r in manifest.records)


def test_bootstrap_from_snapshot_dir(tmp_path):
    snap = tmp_path / "snapshots"
    snap.mkdir()
    for url, name in SCHEMES.items():
        slug = url.rsplit("/", 1)[-1]
        (snap / f"{slug}-0.md").write_bytes(markdown_page(name))
    store = RawArtifactStore(tmp_path / "raw")
    manifest = acquire_corpus(
        primary=SnapshotDirectoryFetcher(snap),
        store=store,
        clock=lambda: datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    assert manifest.active_count == 5
    assert manifest.promotion_ready is False
    validate_manifest(manifest, store.root, require_live=False)


@pytest.mark.skipif(
    not Path("data/bootstrap/snapshots").is_dir()
    or len(list(Path("data/bootstrap/snapshots").glob("*.md"))) < 5,
    reason="Committed bootstrap snapshots not present",
)
def test_bootstrap_real_snapshots_integration(tmp_path):
    root = Path("data/bootstrap/snapshots")
    store = RawArtifactStore(tmp_path)
    manifest = acquire_corpus(
        primary=SnapshotDirectoryFetcher(root),
        store=store,
        clock=lambda: datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    assert manifest.active_count == 5
    validate_manifest(manifest, store.root)
