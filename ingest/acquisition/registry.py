"""Policy registry parsing and runtime manifest validation for Phase 1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from policy import POLICY_DIR
from policy.loader import AllowlistError, canonicalize_url, load_allowlist, load_yaml
from schemas.source import SourceRecord, SourceStatus

from ingest.acquisition.models import AcquisitionManifest


class RegistryValidationError(ValueError):
    """The frozen registry or a runtime acquisition manifest is invalid."""


_SOURCE_FIELDS = {
    "source_id",
    "url",
    "publisher",
    "amc",
    "authority_tier",
    "doc_type",
    "scheme_names",
    "isin",
    "parser_version",
    "status",
}


def load_source_definitions(
    registry_path: Path | None = None,
    allowlist_path: Path | None = None,
) -> list[SourceRecord]:
    """Load exactly five unique policy sources and match them 1:1 to allowlist."""

    registry_path = registry_path or (POLICY_DIR / "source_registry.yaml")
    data = load_yaml(registry_path)
    rows = data.get("sources")
    if not isinstance(rows, list) or len(rows) != 5:
        raise RegistryValidationError("Registry must contain exactly 5 sources")

    allowlist = set(load_allowlist(allowlist_path))
    source_ids: set[str] = set()
    registry_urls: set[str] = set()
    records: list[SourceRecord] = []

    for row in rows:
        if not isinstance(row, dict):
            raise RegistryValidationError("Each registry source must be a mapping")

        source_id = str(row.get("source_id", ""))
        if not source_id or source_id in source_ids:
            raise RegistryValidationError(
                f"Duplicate or missing source_id: {source_id!r}"
            )
        source_ids.add(source_id)

        try:
            url = canonicalize_url(str(row.get("url", "")))
        except AllowlistError as exc:
            raise RegistryValidationError(str(exc)) from exc
        if url not in allowlist:
            raise RegistryValidationError(
                f"Registry URL is not exactly allowlisted: {url}"
            )
        if url in registry_urls:
            raise RegistryValidationError(f"Duplicate registry URL: {url}")
        registry_urls.add(url)

        record_data = {key: value for key, value in row.items() if key in _SOURCE_FIELDS}
        record_data["url"] = url
        records.append(SourceRecord.model_validate(record_data))

    if registry_urls != allowlist:
        raise RegistryValidationError(
            "Registry URLs must match the five-entry allowlist exactly"
        )
    return records


def validate_manifest(
    manifest: AcquisitionManifest,
    raw_root: Path,
    *,
    require_live: bool = False,
) -> None:
    """Enforce the Phase 1 exit gate on a runtime manifest.

    Snapshot manifests are valid for offline development but cannot be marked
    production-promotion-ready when ``require_live`` is true.
    """

    if len(manifest.records) != 5:
        raise RegistryValidationError("Manifest must contain exactly 5 records")

    source_ids: set[str] = set()
    urls: set[str] = set()
    allowlist = set(load_allowlist())

    for item in manifest.records:
        source = item.source
        if source.source_id in source_ids:
            raise RegistryValidationError(
                f"Duplicate manifest source_id: {source.source_id}"
            )
        source_ids.add(source.source_id)

        url = canonicalize_url(str(source.url))
        if url not in allowlist:
            raise RegistryValidationError(f"Manifest URL not allowlisted: {url}")
        urls.add(url)

        if source.status != SourceStatus.ACTIVE:
            raise RegistryValidationError(
                f"Source is not active: {source.source_id} ({source.status.value})"
            )
        if not source.content_sha256 or not source.effective_date:
            raise RegistryValidationError(
                f"Source lacks hash/effective date: {source.source_id}"
            )
        if not source.artifact_path:
            raise RegistryValidationError(
                f"Source lacks artifact path: {source.source_id}"
            )
        artifact = raw_root / source.artifact_path
        if not artifact.is_file():
            raise RegistryValidationError(
                f"Raw artifact is missing for {source.source_id}: {artifact}"
            )
        try:
            actual_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
        except OSError as exc:
            raise RegistryValidationError(
                f"Cannot read raw artifact for {source.source_id}: {exc}"
            ) from exc
        if actual_hash != source.content_sha256:
            raise RegistryValidationError(
                f"Raw artifact hash mismatch for {source.source_id}"
            )
        if require_live and source.fetch_mode == "snapshot":
            raise RegistryValidationError(
                f"Snapshot source is not live-promotion eligible: {source.source_id}"
            )

    if urls != allowlist or manifest.active_count != 5:
        raise RegistryValidationError("Manifest must have exactly 5 active URLs")
