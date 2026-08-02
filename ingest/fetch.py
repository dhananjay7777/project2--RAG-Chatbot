"""Phase 1 public acquisition API.

Implementation modules live under :mod:`ingest.acquisition` so later ingestion
phases remain isolated from HTTP/storage concerns.
"""

from __future__ import annotations

from pathlib import Path

from ingest.acquisition.headless import PlaywrightFetcher
from ingest.acquisition.http import StrictHttpFetcher
from ingest.acquisition.models import AcquisitionManifest
from ingest.acquisition.pipeline import (
    SnapshotDirectoryFetcher,
    acquire_corpus,
)
from ingest.acquisition.storage import RawArtifactStore

DEFAULT_RAW_ROOT = Path(__file__).resolve().parents[1] / "data" / "raw"


def fetch_all(
    raw_root: Path = DEFAULT_RAW_ROOT,
    *,
    use_headless_fallback: bool = False,
) -> AcquisitionManifest:
    """Fetch the frozen five URLs and fail closed on any source failure."""

    primary = StrictHttpFetcher()
    fallback = (
        PlaywrightFetcher(robots=primary.robots)
        if use_headless_fallback
        else None
    )
    return acquire_corpus(
        primary=primary,
        fallback=fallback,
        store=RawArtifactStore(raw_root),
    )


def bootstrap_snapshots(
    snapshot_dir: Path,
    raw_root: Path = DEFAULT_RAW_ROOT,
) -> AcquisitionManifest:
    """Create a development manifest from five supplied page snapshots."""

    return acquire_corpus(
        primary=SnapshotDirectoryFetcher(snapshot_dir),
        store=RawArtifactStore(raw_root),
    )
