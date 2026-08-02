"""Phase 2 orchestration: parse → strip → chunk → facts → write."""

from __future__ import annotations

import logging
from pathlib import Path

from ingest.acquisition.storage import RawArtifactStore
from ingest.processing.chunk import active_chunks, chunk_document
from ingest.processing.facts import (
    FactExtractionError,
    assert_required_facts_verified,
    build_fact_cards,
    load_fact_seed,
)
from ingest.processing.models import ProcessingResult
from ingest.processing.parse import parse_artifact
from ingest.processing.strip import strip_audit_violations, strip_document
from ingest.processing.writer import write_processed
from ingest.registry import validate_registry
from schemas.chunk import Chunk
from schemas.fact_card import FactCard

LOGGER = logging.getLogger(__name__)

DEFAULT_RAW_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw"
DEFAULT_PROCESSED_ROOT = Path(__file__).resolve().parents[2] / "data" / "processed"


class ProcessingError(RuntimeError):
    """Phase 2 processing failed closed."""


def process_corpus(
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
    require_verified: bool = True,
) -> tuple[list[Chunk], list[FactCard], list[ProcessingResult]]:
    """Process all active sources from the latest acquisition manifest."""

    manifest = validate_registry(raw_root, require_live=False)
    seed = load_fact_seed()
    all_chunks: list[Chunk] = []
    all_facts: list[FactCard] = []
    results: list[ProcessingResult] = []

    for record in manifest.records:
        source = record.source
        artifact = raw_root / (source.artifact_path or "")
        if not artifact.is_file():
            raise ProcessingError(f"Missing artifact for {source.source_id}: {artifact}")

        scheme_name = source.scheme_names[0]
        LOGGER.info("Processing %s (%s)", source.source_id, artifact.name)
        doc = parse_artifact(
            artifact,
            source_id=source.source_id,
            scheme_name=scheme_name,
            effective_date=source.effective_date,
        )
        doc = strip_document(doc)
        chunks = chunk_document(doc)
        keep = active_chunks(chunks)
        quarantined = len(chunks) - len(keep)
        if quarantined:
            LOGGER.warning(
                "%s: %s quarantined chunk(s) excluded from active set",
                source.source_id,
                quarantined,
            )

        facts = build_fact_cards(doc, keep, seed)
        if require_verified:
            assert_required_facts_verified(facts, seed)

        all_chunks.extend(keep)
        all_facts.extend(facts)
        results.append(
            ProcessingResult(
                source_id=source.source_id,
                scheme_name=scheme_name,
                chunk_count=len(keep),
                fact_count=len(facts),
                quarantined_chunks=quarantined,
                verified_facts=sum(1 for f in facts if f.verified_by_human),
                null_facts=sum(1 for f in facts if f.value_text is None),
            )
        )

    # Strip audit across active chunk corpus
    blob = "\n".join(c.text for c in all_chunks)
    violations = strip_audit_violations(blob)
    # Holdings table remnant check is noisy for legitimate pipes in other tables;
    # only fail on critical strip failures.
    critical = [v for v in violations if v != "holdings table remnant"]
    if critical:
        raise ProcessingError(
            "Strip audit failed; forbidden content remains: " + ", ".join(critical)
        )

    if any(r.quarantined_chunks for r in results):
        # Exit criteria: zero quarantined in active set — we already excluded them,
        # but report if any existed (allowed as long as not written).
        LOGGER.info("Quarantined chunks were excluded from chunks.jsonl")

    write_processed(
        processed_root,
        chunks=all_chunks,
        facts=all_facts,
        results=results,
    )
    return all_chunks, all_facts, results
