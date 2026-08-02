"""Phase 3 unit tests (no model downloads)."""

from __future__ import annotations

from datetime import date

import pytest

from core.retrieval.gate import apply_confidence_gate, tie_break_reranked
from core.retrieval.models import RetrievalStatus, ScoredChunk
from core.retrieval.query_inference import infer_scheme
from core.retrieval.rrf import reciprocal_rank_fusion
from ingest.indexing.bm25_index import build_bm25
from ingest.indexing.models import ChunkIndexRecord
from schemas.chunk import Chunk


def _chunk(cid: str, source_id: str, text: str, tags: list[str] | None = None) -> Chunk:
    return Chunk(
        chunk_id=cid,
        source_id=source_id,
        text=text,
        fact_tags=tags or [],
        effective_date=date(2026, 7, 24),
    )


def _scored(chunk: Chunk, source_id: str, rerank: float | None = None) -> ScoredChunk:
    return ScoredChunk(
        chunk=chunk,
        source_id=source_id,
        rerank_score=rerank,
    )


def test_rrf_merges_disjoint_lists():
    fused = reciprocal_rank_fusion(
        [["a", "b"], ["c", "a"]],
        k=60,
        top_n=3,
    )
    ids = [cid for cid, _ in fused]
    assert ids[0] == "a"
    assert set(ids) == {"a", "b", "c"}


def test_gate_low_tau_is_no_answer():
    ranked = [
        _scored(_chunk("1", "s1", "x"), "s1", rerank=0.1),
    ]
    status, reason = apply_confidence_gate(
        ranked,
        tau=0.35,
        scheme_margin_epsilon=0.05,
        scheme_confident=True,
        ambiguous_multi_asset=False,
    )
    assert status == RetrievalStatus.NO_ANSWER
    assert reason == "low_rerank_score"


def test_gate_cross_scheme_margin():
    ranked = [
        _scored(_chunk("1", "groww-tata-multi-asset-allocation-fund-direct-growth", "a"), "groww-tata-multi-asset-allocation-fund-direct-growth", rerank=0.5),
        _scored(_chunk("2", "groww-kotak-multi-asset-allocation-fund-direct-growth", "b"), "groww-kotak-multi-asset-allocation-fund-direct-growth", rerank=0.48),
    ]
    status, reason = apply_confidence_gate(
        ranked,
        tau=0.35,
        scheme_margin_epsilon=0.05,
        scheme_confident=False,
        ambiguous_multi_asset=False,
    )
    assert status == RetrievalStatus.CLARIFY
    assert reason == "cross_scheme_margin"


def test_infer_scheme_nippon_alias():
    inference = infer_scheme("What is the expense ratio for Nippon Value Direct?")
    assert inference.source_id == "groww-nippon-india-value-fund-direct-growth"
    assert "expense_ratio" in inference.fact_tags
    assert inference.brand_only is False


def test_infer_brand_only_nippon_does_not_bind_scheme():
    inference = infer_scheme("nav of nippon")
    assert inference.source_id is None
    assert inference.brand_only is True
    assert "nav" in inference.fact_tags


def test_infer_nippon_value_product_token_binds():
    inference = infer_scheme("nav of nippon value")
    assert inference.source_id == "groww-nippon-india-value-fund-direct-growth"
    assert inference.scheme_confident is True


def test_infer_ambiguous_multi_asset():
    inference = infer_scheme("What is the exit load on multi asset allocation fund?")
    assert inference.ambiguous_multi_asset is True
    assert inference.source_id is None


def test_bm25_finds_exit_load_token():
    records = [
        ChunkIndexRecord(
            chunk_id="c1",
            source_id="groww-nippon-india-value-fund-direct-growth",
            scheme_name="Nippon India Value Fund Direct Growth",
            text="Exit load 1% if redeemed within 30 days",
            index_text="Exit load 1% if redeemed within 30 days",
            fact_tags=["exit_load"],
            content_hash="abc",
        )
    ]
    index = build_bm25(records)
    hits = index.search("exit load", top_k=5)
    assert hits and hits[0][0] == "c1"


def test_tie_break_prefers_later_effective_date():
    older = ScoredChunk(
        chunk=_chunk("o", "s", "old", tags=[]),
        source_id="s",
        rerank_score=0.9,
    )
    older.chunk.effective_date = date(2026, 1, 1)
    newer = ScoredChunk(
        chunk=_chunk("n", "s", "new", tags=[]),
        source_id="s",
        rerank_score=0.9,
    )
    newer.chunk.effective_date = date(2026, 7, 24)
    ordered = tie_break_reranked([older, newer])
    assert ordered[0].chunk.chunk_id == "n"
