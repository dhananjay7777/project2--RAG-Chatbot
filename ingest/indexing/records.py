"""Build index-ready records from processed chunks + registry."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from schemas.chunk import Chunk

from ingest.indexing.models import ChunkIndexRecord
from ingest.processing.normalize import normalize_for_index
from policy.loader import load_registry


def _scheme_name_for(source_id: str, registry: dict[str, Any] | None = None) -> str:
    registry = registry or load_registry()
    for row in registry["sources"]:
        if row["source_id"] == source_id:
            names = row.get("scheme_names") or []
            if names:
                return str(names[0])
    raise KeyError(f"Unknown source_id in registry: {source_id}")


def _source_status(source_id: str, registry: dict[str, Any] | None = None) -> str:
    registry = registry or load_registry()
    for row in registry["sources"]:
        if row["source_id"] == source_id:
            return str(row.get("status") or "active")
    return "inactive"


def content_hash(index_text: str) -> str:
    return hashlib.sha256(index_text.encode("utf-8")).hexdigest()


def build_index_records(chunks: list[Chunk]) -> list[ChunkIndexRecord]:
    registry = load_registry()
    records: list[ChunkIndexRecord] = []
    for chunk in chunks:
        if chunk.pii_scan == "quarantined":
            continue
        index_text = normalize_for_index(chunk.text)
        eff: str | None = None
        if chunk.effective_date is not None:
            eff = chunk.effective_date.isoformat()
        records.append(
            ChunkIndexRecord(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                scheme_name=_scheme_name_for(chunk.source_id, registry),
                status=_source_status(chunk.source_id, registry),
                text=chunk.text,
                index_text=index_text,
                fact_tags=list(chunk.fact_tags),
                effective_date=eff,
                content_hash=content_hash(index_text),
            )
        )
    return records


def chunk_from_record(record: ChunkIndexRecord) -> Chunk:
    eff: date | None = None
    if record.effective_date:
        eff = date.fromisoformat(record.effective_date)
    return Chunk(
        chunk_id=record.chunk_id,
        source_id=record.source_id,
        text=record.text,
        fact_tags=list(record.fact_tags),
        effective_date=eff,
        pii_scan="clean",
    )
