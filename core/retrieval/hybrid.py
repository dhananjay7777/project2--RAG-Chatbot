"""Hybrid BM25 + dense retrieval with rerank and confidence gate."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Sequence

from core.retrieval.gate import apply_confidence_gate, tie_break_reranked
from core.retrieval.models import RetrievalResult, RetrievalStatus, ScoredChunk
from core.retrieval.query_inference import QueryInference, infer_scheme
from core.retrieval.rerank import CrossEncoderReranker, Reranker
from core.retrieval.rrf import reciprocal_rank_fusion
from core.settings import load_settings, retrieval_settings
from ingest.indexing.bm25_index import Bm25Index, load_bm25
from ingest.indexing.vector_store import DenseVectorStore, create_dense_store
from ingest.indexing.embeddings import Embedder, SentenceTransformerEmbedder
from ingest.indexing.pipeline import index_paths
from ingest.indexing.records import build_index_records, chunk_from_record
from ingest.processing.writer import load_chunks
from policy.loader import load_registry

logger = logging.getLogger(__name__)


def retrieval_mode() -> str:
    """`hybrid` (default) or `bm25` for memory-constrained hosts (Railway Hobby)."""
    env = os.getenv("MF_RETRIEVAL_MODE", "").strip().lower()
    if env:
        return "bm25" if env in {"bm25", "light"} else env
    configured = str(retrieval_settings().get("mode", "hybrid")).strip().lower()
    return "bm25" if configured in {"bm25", "light"} else configured


class _ZeroEmbedder:
    """No-op embedder for BM25-only deploy (avoids loading sentence-transformers)."""

    def encode_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]

    def encode_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]


class _EmptyDenseStore:
    def upsert(self, records: Sequence[Any], embeddings: Sequence[Sequence[float]]) -> None:
        return None

    def delete_ids(self, chunk_ids: Sequence[str]) -> None:
        return None

    def query_dense(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        return []


class _PassthroughReranker:
    def score_pairs(self, query: str, passages: Sequence[str]) -> list[float]:
        return [0.0 for _ in passages]


class HybridRetriever:
    def __init__(
        self,
        *,
        bm25: Bm25Index,
        dense: DenseVectorStore,
        chunk_by_id: dict[str, ScoredChunk],
        embedder: Embedder,
        reranker: Reranker,
        settings: dict | None = None,
    ) -> None:
        self._bm25 = bm25
        self._dense = dense
        self._chunk_by_id = chunk_by_id
        self._embedder = embedder
        self._reranker = reranker
        self._settings = settings or retrieval_settings()
        self._active_source_ids = {
            row["source_id"]
            for row in load_registry()["sources"]
            if str(row.get("status", "active")) == "active"
        }

    @classmethod
    def from_disk(
        cls,
        *,
        processed_root: Path | None = None,
        index_root: Path | None = None,
        embedder: Embedder | None = None,
        reranker: Reranker | None = None,
    ) -> "HybridRetriever":
        settings = load_settings()
        proc_root = processed_root or Path(
            settings.get("paths", {}).get("data_processed", "data/processed")
        )
        _idx_root, _chroma_dir, bm25_path = index_paths(index_root)
        idx_root = _idx_root
        retr = retrieval_settings()
        light = retrieval_mode() == "bm25"
        if light:
            logger.info("retrieval mode=bm25 (no embedding/reranker models)")
            embedder = embedder or _ZeroEmbedder()
            reranker = reranker or _PassthroughReranker()
            dense: DenseVectorStore = _EmptyDenseStore()
        else:
            embedder = embedder or SentenceTransformerEmbedder(
                str(retr.get("embedding_model", "BAAI/bge-small-en-v1.5"))
            )
            reranker = reranker or CrossEncoderReranker(
                str(retr.get("reranker_model", "BAAI/bge-reranker-base"))
            )
            dense = create_dense_store(idx_root)

        bm25 = load_bm25(bm25_path)
        records = build_index_records(load_chunks(proc_root))
        chunk_by_id: dict[str, ScoredChunk] = {}
        for rec in records:
            chunk_by_id[rec.chunk_id] = ScoredChunk(
                chunk=chunk_from_record(rec),
                source_id=rec.source_id,
                scheme_name=rec.scheme_name,
            )
        return cls(
            bm25=bm25,
            dense=dense,
            chunk_by_id=chunk_by_id,
            embedder=embedder,
            reranker=reranker,
            settings=retr,
        )

    def _metadata_where(self, inference: QueryInference) -> dict | None:
        if inference.source_id and inference.scheme_confident:
            return {"source_id": inference.source_id, "status": "active"}
        return {"status": "active"}

    def _filter_source(self, chunk_ids: list[str], source_id: str | None) -> list[str]:
        if not source_id:
            return chunk_ids
        return [
            cid
            for cid in chunk_ids
            if self._chunk_by_id.get(cid) and self._chunk_by_id[cid].source_id == source_id
        ]

    def _filter_active(self, chunk_ids: list[str]) -> list[str]:
        return [
            cid
            for cid in chunk_ids
            if self._chunk_by_id.get(cid)
            and self._chunk_by_id[cid].source_id in self._active_source_ids
        ]

    def _post_filter_fact_tags(
        self, chunk_ids: list[str], fact_tags: list[str]
    ) -> list[str]:
        if not fact_tags or len(fact_tags) != 1:
            return chunk_ids
        tag = fact_tags[0]
        tagged = [
            cid
            for cid in chunk_ids
            if cid in self._chunk_by_id and tag in self._chunk_by_id[cid].chunk.fact_tags
        ]
        return tagged if tagged else chunk_ids

    def retrieve(self, query: str) -> RetrievalResult:
        q = query.strip()
        if not q:
            return RetrievalResult(
                status=RetrievalStatus.NO_ANSWER,
                query=query,
                reason="empty_query",
            )

        inference = infer_scheme(q)
        if retrieval_mode() == "bm25":
            return self._retrieve_bm25_only(q, inference)

        bm25_top_k = int(self._settings.get("bm25_top_k", 20))
        dense_top_k = int(self._settings.get("dense_top_k", 20))
        rrf_k = int(self._settings.get("rrf_k", 60))
        rerank_top_k = int(self._settings.get("rerank_top_k", 4))
        tau = float(self._settings.get("confidence_tau", 0.35))
        epsilon = float(self._settings.get("scheme_margin_epsilon", 0.05))

        bm25_hits = self._bm25.search(q, top_k=bm25_top_k)
        bm25_ids = [cid for cid, _ in bm25_hits]

        where = self._metadata_where(inference)
        query_vec = self._embedder.encode_queries([q])[0]
        dense_hits = self._dense.query_dense(query_vec, top_k=dense_top_k, where=where)
        dense_ids = [cid for cid, _ in dense_hits]

        bm25_ids = self._filter_active(bm25_ids)
        dense_ids = self._filter_active(dense_ids)

        if inference.source_id and inference.scheme_confident:
            bm25_ids = self._filter_source(bm25_ids, inference.source_id)
            dense_ids = self._filter_source(dense_ids, inference.source_id)

        fused = reciprocal_rank_fusion([bm25_ids, dense_ids], k=rrf_k, top_n=20)
        fused_ids = [cid for cid, _ in fused]
        fused_ids = self._post_filter_fact_tags(fused_ids, inference.fact_tags)

        candidates: list[ScoredChunk] = []
        bm25_rank_map = {cid: i + 1 for i, cid in enumerate(bm25_ids)}
        dense_rank_map = {cid: i + 1 for i, cid in enumerate(dense_ids)}
        rrf_map = dict(fused)

        for cid in fused_ids:
            base = self._chunk_by_id.get(cid)
            if base is None:
                continue
            candidates.append(
                ScoredChunk(
                    chunk=base.chunk,
                    bm25_rank=bm25_rank_map.get(cid),
                    dense_rank=dense_rank_map.get(cid),
                    rrf_score=rrf_map.get(cid, 0.0),
                    source_id=base.source_id,
                    scheme_name=base.scheme_name,
                )
            )

        if not candidates:
            return RetrievalResult(
                status=RetrievalStatus.NO_ANSWER,
                query=q,
                reason="no_candidates",
                inferred_source_id=inference.source_id,
                inferred_fact_tags=inference.fact_tags,
            )

        pool = candidates[:20]
        rerank_scores = self._reranker.score_pairs(q, [c.chunk.text for c in pool])
        for idx, score in enumerate(rerank_scores):
            pool[idx].rerank_score = score

        reranked = tie_break_reranked(pool)[:rerank_top_k]

        status, reason = apply_confidence_gate(
            reranked,
            tau=tau,
            scheme_margin_epsilon=epsilon,
            scheme_confident=inference.scheme_confident,
            ambiguous_multi_asset=inference.ambiguous_multi_asset,
        )

        if status != RetrievalStatus.OK:
            return RetrievalResult(
                status=status,
                query=q,
                chunks=[],
                reason=reason,
                inferred_source_id=inference.source_id,
                inferred_fact_tags=inference.fact_tags,
            )

        return RetrievalResult(
            status=RetrievalStatus.OK,
            query=q,
            chunks=reranked,
            inferred_source_id=inference.source_id,
            inferred_fact_tags=inference.fact_tags,
        )

    def _retrieve_bm25_only(self, q: str, inference: QueryInference) -> RetrievalResult:
        """Lexical-only path for low-RAM hosts (no torch / HF weights)."""
        bm25_top_k = int(self._settings.get("bm25_top_k", 20))
        rerank_top_k = int(self._settings.get("rerank_top_k", 4))
        tau = float(self._settings.get("bm25_confidence_tau", 0.05))
        epsilon = float(self._settings.get("scheme_margin_epsilon", 0.05))

        bm25_hits = self._bm25.search(q, top_k=bm25_top_k)
        bm25_ids = self._filter_active([cid for cid, _ in bm25_hits])
        if inference.source_id and inference.scheme_confident:
            bm25_ids = self._filter_source(bm25_ids, inference.source_id)
        bm25_ids = self._post_filter_fact_tags(bm25_ids, inference.fact_tags)
        score_map = {cid: float(score) for cid, score in bm25_hits}

        candidates: list[ScoredChunk] = []
        for rank, cid in enumerate(bm25_ids, start=1):
            base = self._chunk_by_id.get(cid)
            if base is None:
                continue
            candidates.append(
                ScoredChunk(
                    chunk=base.chunk,
                    bm25_rank=rank,
                    rrf_score=score_map.get(cid, 0.0),
                    source_id=base.source_id,
                    scheme_name=base.scheme_name,
                )
            )

        if not candidates:
            return RetrievalResult(
                status=RetrievalStatus.NO_ANSWER,
                query=q,
                reason="no_candidates",
                inferred_source_id=inference.source_id,
                inferred_fact_tags=inference.fact_tags,
            )

        raw_scores = [score_map.get(c.chunk.chunk_id, 0.0) for c in candidates]
        max_score = max(raw_scores)
        min_score = min(raw_scores)
        span = max_score - min_score
        for item in candidates:
            raw = score_map.get(item.chunk.chunk_id, 0.0)
            # BM25Okapi can be negative; keep a relative 0..1 score for the gate.
            item.rerank_score = 1.0 if span <= 1e-12 else (raw - min_score) / span

        ranked = tie_break_reranked(candidates)[:rerank_top_k]
        status, reason = apply_confidence_gate(
            ranked,
            tau=tau,
            scheme_margin_epsilon=epsilon,
            scheme_confident=inference.scheme_confident,
            ambiguous_multi_asset=inference.ambiguous_multi_asset,
        )
        if status != RetrievalStatus.OK:
            return RetrievalResult(
                status=status,
                query=q,
                chunks=[],
                reason=reason,
                inferred_source_id=inference.source_id,
                inferred_fact_tags=inference.fact_tags,
            )
        return RetrievalResult(
            status=RetrievalStatus.OK,
            query=q,
            chunks=ranked,
            inferred_source_id=inference.source_id,
            inferred_fact_tags=inference.fact_tags,
        )
