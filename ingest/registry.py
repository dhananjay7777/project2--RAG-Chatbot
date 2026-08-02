"""Phase 1 public registry API."""

from __future__ import annotations

from pathlib import Path

from ingest.acquisition.models import AcquisitionManifest
from ingest.acquisition.registry import (
    load_source_definitions,
    validate_manifest,
)
from ingest.acquisition.storage import RawArtifactStore

DEFAULT_RAW_ROOT = Path(__file__).resolve().parents[1] / "data" / "raw"


def validate_registry(
    raw_root: Path = DEFAULT_RAW_ROOT,
    *,
    require_live: bool = False,
) -> AcquisitionManifest:
    """Load and validate the latest complete runtime manifest."""

    # Always validate policy definitions too (duplicates / exact allowlist match).
    load_source_definitions()
    store = RawArtifactStore(raw_root)
    manifest = store.load_latest(live_only=require_live)
    if manifest is None:
        mode = "live " if require_live else ""
        raise FileNotFoundError(
            f"No latest {mode}acquisition manifest under {raw_root}"
        )
    validate_manifest(manifest, raw_root, require_live=require_live)
    return manifest
