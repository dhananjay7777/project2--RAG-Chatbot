"""Phase 3 index build tests with stub embedder."""

from __future__ import annotations

import json
from pathlib import Path

from ingest.indexing.pipeline import build_index
from ingest.processing.models import ProcessingResult
from ingest.processing.writer import write_processed
from schemas.chunk import Chunk


class StubEmbedder:
    def encode_queries(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    def encode_passages(self, texts):
        return [[0.2, 0.1, 0.0] for _ in texts]


def test_build_index_idempotent(tmp_path: Path):
    processed = tmp_path / "processed"
    index_root = tmp_path / "index"
    chunk = Chunk(
        chunk_id="groww-nippon-india-value-fund-direct-growth#001",
        source_id="groww-nippon-india-value-fund-direct-growth",
        text="Expense ratio 1.27% for Nippon India Value Fund Direct Growth",
        fact_tags=["expense_ratio"],
    )
    write_processed(
        processed,
        chunks=[chunk],
        facts=[],
        results=[
            ProcessingResult(
                source_id=chunk.source_id,
                scheme_name="Nippon India Value Fund Direct Growth",
                chunk_count=1,
                fact_count=0,
                verified_facts=0,
                null_facts=0,
                quarantined_chunks=0,
            )
        ],
    )

    manifest1 = build_index(
        processed_root=processed,
        index_root=index_root,
        embedder=StubEmbedder(),
    )
    manifest2 = build_index(
        processed_root=processed,
        index_root=index_root,
        embedder=StubEmbedder(),
    )
    assert manifest1.chunk_count == 1
    assert manifest2.records == manifest1.records
    manifest_path = index_root / "index_manifest.json"
    assert manifest_path.is_file()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["chunk_count"] == 1
