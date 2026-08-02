"""Write Phase 2 processed artifacts under data/processed/."""

from __future__ import annotations

import json
from pathlib import Path

from schemas.chunk import Chunk
from schemas.fact_card import FactCard

from ingest.processing.models import ProcessingResult


def write_processed(
    processed_root: Path,
    *,
    chunks: list[Chunk],
    facts: list[FactCard],
    results: list[ProcessingResult],
) -> None:
    processed_root.mkdir(parents=True, exist_ok=True)
    chunks_path = processed_root / "chunks.jsonl"
    facts_path = processed_root / "facts.jsonl"
    summary_path = processed_root / "processing_summary.json"

    with chunks_path.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(chunk.model_dump_json() + "\n")

    with facts_path.open("w", encoding="utf-8") as fh:
        for fact in facts:
            fh.write(fact.model_dump_json() + "\n")

    payload = {
        "sources": [r.model_dump(mode="json") for r in results],
        "chunk_count": len(chunks),
        "fact_count": len(facts),
        "quarantined_chunks": sum(r.quarantined_chunks for r in results),
    }
    summary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_chunks(processed_root: Path) -> list[Chunk]:
    path = processed_root / "chunks.jsonl"
    rows: list[Chunk] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(Chunk.model_validate_json(line))
    return rows


def load_facts(processed_root: Path) -> list[FactCard]:
    path = processed_root / "facts.jsonl"
    rows: list[FactCard] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(FactCard.model_validate_json(line))
    return rows
