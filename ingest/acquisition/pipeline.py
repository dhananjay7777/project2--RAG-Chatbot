"""Phase 1 orchestration: acquire exactly five sources or fail closed."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
from uuid import uuid4

from ingest.acquisition.http import (
    AcquisitionError,
    AllowlistViolation,
    RobotsDeniedError,
)
from ingest.acquisition.models import (
    AcquisitionManifest,
    AcquisitionRecord,
    FetchPayload,
)
from ingest.acquisition.registry import load_source_definitions
from ingest.acquisition.storage import RawArtifactStore, StorageError
from ingest.acquisition.validation import ContentValidationError, validate_payload
from policy.loader import canonicalize_url, load_allowlist
from schemas.source import SourceRecord, SourceStatus

LOGGER = logging.getLogger(__name__)


class PageFetcher(Protocol):
    def fetch(self, url: str) -> FetchPayload: ...


def _updated_source(definition: SourceRecord, **updates) -> SourceRecord:
    payload = definition.model_dump(mode="python")
    payload.update(updates)
    return SourceRecord.model_validate(payload)


class CorpusIncompleteError(AcquisitionError):
    """At least one frozen source failed, so no new corpus was promoted."""

    def __init__(self, manifest: AcquisitionManifest):
        failed = [
            item.source.source_id
            for item in manifest.records
            if item.source.status != SourceStatus.ACTIVE
        ]
        super().__init__(
            "Corpus acquisition failed closed; inactive sources: "
            + ", ".join(failed)
        )
        self.manifest = manifest


class SnapshotDirectoryFetcher:
    """Offline development bootstrap from provided HTML/Markdown snapshots."""

    def __init__(self, snapshot_dir: Path, allowlist: list[str] | None = None):
        self.snapshot_dir = snapshot_dir
        self.allowlist = set(allowlist or load_allowlist())

    def fetch(self, url: str) -> FetchPayload:
        canonical = canonicalize_url(url)
        if canonical not in self.allowlist:
            raise AllowlistViolation(
                f"Refusing non-allowlisted snapshot URL: {url}"
            )
        slug = Path(urlparse(canonical).path).name
        exact_candidates = [
            self.snapshot_dir / f"{slug}.html",
            self.snapshot_dir / f"{slug}.md",
        ]
        candidates = [path for path in exact_candidates if path.is_file()]
        if not candidates:
            candidates = sorted(
                [
                    *self.snapshot_dir.glob(f"{slug}-*.html"),
                    *self.snapshot_dir.glob(f"{slug}-*.md"),
                ]
            )
        if len(candidates) != 1:
            raise AcquisitionError(
                f"Expected exactly one snapshot for {slug}, found "
                f"{len(candidates)} in {self.snapshot_dir}"
            )
        path = candidates[0]
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise AcquisitionError(f"Cannot read snapshot {path}: {exc}") from exc
        return FetchPayload(
            content=content,
            final_url=canonical,
            mode="snapshot",
            content_type=(
                "text/markdown" if path.suffix.lower() == ".md" else "text/html"
            ),
        )


def _previous_by_source(
    store: RawArtifactStore,
) -> dict[str, AcquisitionRecord]:
    previous = store.load_latest()
    if previous is None:
        return {}
    return {item.source.source_id: item for item in previous.records}


def _fetch_and_validate(
    definition: SourceRecord,
    primary: PageFetcher,
    fallback: PageFetcher | None,
    fetched_at: datetime,
) -> tuple[FetchPayload, date, bool]:
    expected_scheme = definition.scheme_names[0]
    try:
        payload = primary.fetch(str(definition.url))
        effective_date, nav_date_found = validate_payload(
            payload,
            expected_scheme,
            fetched_at=fetched_at,
        )
        return payload, effective_date, nav_date_found
    except (AllowlistViolation, RobotsDeniedError):
        raise
    except (AcquisitionError, ContentValidationError) as primary_error:
        if fallback is None:
            raise
        LOGGER.warning(
            "Primary acquisition failed for %s; trying headless fallback: %s",
            definition.source_id,
            primary_error,
        )
        payload = fallback.fetch(str(definition.url))
        effective_date, nav_date_found = validate_payload(
            payload,
            expected_scheme,
            fetched_at=fetched_at,
        )
        return payload, effective_date, nav_date_found


def acquire_corpus(
    *,
    primary: PageFetcher,
    store: RawArtifactStore,
    fallback: PageFetcher | None = None,
    registry_path: Path | None = None,
    allowlist_path: Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> AcquisitionManifest:
    """Acquire all five sources, write a run manifest, and promote only if complete."""

    clock = clock or (lambda: datetime.now(timezone.utc))
    definitions = load_source_definitions(registry_path, allowlist_path)
    previous = _previous_by_source(store)
    records: list[AcquisitionRecord] = []

    for definition in definitions:
        fetched_at = clock()
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        old = previous.get(definition.source_id)
        previous_hash = old.source.content_sha256 if old else None

        try:
            payload, effective_date, nav_date_found = _fetch_and_validate(
                definition,
                primary,
                fallback,
                fetched_at,
            )
            if not nav_date_found:
                LOGGER.warning(
                    "NAV date missing for %s; using fetched_at UTC date",
                    definition.source_id,
                )
            suffix = ".md" if payload.content_type == "text/markdown" else ".html"
            digest, artifact_path, _created = store.write_artifact(
                definition.source_id,
                payload.content,
                suffix=suffix,
            )
            changed = digest != previous_hash
            source = _updated_source(
                definition,
                effective_date=effective_date,
                fetched_at=fetched_at,
                content_sha256=digest,
                status=SourceStatus.ACTIVE,
                supersedes=(
                    f"{definition.source_id}@{previous_hash[:12]}"
                    if previous_hash and changed
                    else None
                ),
                artifact_path=artifact_path,
                fetch_mode=payload.mode,
                final_url=payload.final_url,
                last_error=None,
            )
            records.append(
                AcquisitionRecord(
                    source=source,
                    changed=changed,
                    previous_content_sha256=previous_hash,
                )
            )
        except (AcquisitionError, ContentValidationError, StorageError, OSError) as exc:
            LOGGER.error("Acquisition failed for %s: %s", definition.source_id, exc)
            source = _updated_source(
                definition,
                fetched_at=fetched_at,
                status=SourceStatus.FETCH_FAILED,
                last_error=str(exc),
                content_sha256=previous_hash,
                effective_date=old.source.effective_date if old else None,
                artifact_path=old.source.artifact_path if old else None,
                fetch_mode=old.source.fetch_mode if old else None,
            )
            records.append(
                AcquisitionRecord(
                    source=source,
                    changed=False,
                    previous_content_sha256=previous_hash,
                )
            )

    generated_at = clock()
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    all_active = all(
        record.source.status == SourceStatus.ACTIVE for record in records
    )
    live_only = all(
        record.source.fetch_mode in {"http", "headless"} for record in records
    )
    run_id = (
        generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid4().hex[:8]
    )
    manifest = AcquisitionManifest(
        run_id=run_id,
        generated_at=generated_at,
        promotion_ready=all_active and live_only,
        records=records,
    )
    store.write_manifest(manifest)
    if not all_active:
        raise CorpusIncompleteError(manifest)
    return manifest
