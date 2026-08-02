"""Registry loading and manifest validation (Phase 1)."""

from datetime import datetime, timezone

import pytest

from ingest.acquisition.registry import RegistryValidationError, load_source_definitions, validate_manifest
from ingest.acquisition.storage import RawArtifactStore
from ingest.acquisition.pipeline import acquire_corpus
from tests.phase1.helpers import MappingFetcher, html_page
from policy.loader import load_allowlist

SCHEMES = [
    "Nippon India Value Fund Direct Growth",
    "Tata Multi Asset Allocation Fund Direct Growth",
    "Kotak Multi Asset Allocation Fund Direct Growth",
    "Franklin India Multi Cap Fund Direct Growth",
    "Samco Mid Cap Fund Direct Growth",
]


def test_load_source_definitions_cardinality_and_allowlist_match():
    records = load_source_definitions()
    assert len(records) == 5
    assert len({r.source_id for r in records}) == 5
    urls = {str(r.url) for r in records}
    assert urls == set(load_allowlist())


def test_validate_manifest_rejects_snapshot_for_live_requirement(tmp_path):
    allowlist = load_allowlist()
    pages = {
        url: html_page(name)
        for url, name in zip(allowlist, SCHEMES, strict=True)
    }
    store = RawArtifactStore(tmp_path)
    manifest = acquire_corpus(
        primary=MappingFetcher(pages, mode="snapshot"),
        store=store,
        clock=lambda: datetime(2026, 7, 27, tzinfo=timezone.utc),
    )
    validate_manifest(manifest, tmp_path, require_live=False)
    with pytest.raises(RegistryValidationError, match="live-promotion"):
        validate_manifest(manifest, tmp_path, require_live=True)
