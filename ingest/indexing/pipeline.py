"""Idempotent index build (Chroma + BM25)."""

from __future__ import annotations

import logging
from pathlib import Path

from core.settings import load_settings, retrieval_settings
from ingest.indexing.bm25_index import build_bm25, save_bm25
from ingest.indexing.vector_store import create_dense_store
from ingest.indexing.embeddings import Embedder, SentenceTransformerEmbedder
from ingest.indexing.models import IndexManifest
from ingest.indexing.records import build_index_records
from ingest.processing.writer import load_chunks

logger = logging.getLogger(__name__)

DEFAULT_INDEX_ROOT = Path("data/index")
MANIFEST_NAME = "index_manifest.json"
BM25_NAME = "bm25.pkl"
CHROMA_DIR_NAME = "chroma"


def index_paths(index_root: Path | None = None) -> tuple[Path, Path, Path]:
    root = index_root or Path(load_settings().get("paths", {}).get("data_index", DEFAULT_INDEX_ROOT))
    return root, root / CHROMA_DIR_NAME, root / BM25_NAME


def build_index(
    *,
    processed_root: Path | None = None,
    index_root: Path | None = None,
    embedder: Embedder | None = None,
) -> IndexManifest:
    settings = load_settings()
    proc_root = processed_root or Path(settings.get("paths", {}).get("data_processed", "data/processed"))
    idx_root, chroma_dir, bm25_path = index_paths(index_root)

    retr = retrieval_settings()
    model_name = str(retr.get("embedding_model", "BAAI/bge-small-en-v1.5"))
    embedder = embedder or SentenceTransformerEmbedder(model_name)

    chunks = load_chunks(proc_root)
    records = build_index_records(chunks)
    record_by_id = {r.chunk_id: r for r in records}

    manifest_path = idx_root / MANIFEST_NAME
    previous: IndexManifest | None = None
    if manifest_path.is_file():
        previous = IndexManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    prev_hashes = previous.records if previous else {}
    to_embed = [r for r in records if prev_hashes.get(r.chunk_id) != r.content_hash]
    removed = [cid for cid in prev_hashes if cid not in record_by_id]

    idx_root.mkdir(parents=True, exist_ok=True)
    store = create_dense_store(idx_root)

    if removed:
        logger.info("Removing %d stale chunk(s) from dense index", len(removed))
        store.delete_ids(removed)

    if to_embed:
        logger.info("Embedding %d chunk(s) with %s", len(to_embed), model_name)
        vectors = embedder.encode_passages([r.index_text for r in to_embed])
        store.upsert(to_embed, vectors)
    elif not records:
        logger.warning("No chunks to index")

    bm25 = build_bm25(records)
    save_bm25(bm25, bm25_path)

    manifest = IndexManifest(
        embedding_model=model_name,
        chunk_count=len(records),
        records={r.chunk_id: r.content_hash for r in records},
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    logger.info("Index built: %d chunks at %s", len(records), idx_root)
    return manifest
