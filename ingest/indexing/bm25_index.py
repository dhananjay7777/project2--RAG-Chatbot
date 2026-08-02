"""BM25 lexical index over normalized chunk text."""

from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from ingest.indexing.models import ChunkIndexRecord


def tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


@dataclass
class Bm25Index:
    chunk_ids: list[str]
    _bm25: BM25Okapi

    def search(self, query: str, top_k: int = 20) -> list[tuple[str, float]]:
        if not self.chunk_ids:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(self.chunk_ids, scores),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return [(cid, float(score)) for cid, score in ranked[:top_k]]


def build_bm25(records: list[ChunkIndexRecord]) -> Bm25Index:
    chunk_ids = [r.chunk_id for r in records]
    corpus = [tokenize(r.index_text) for r in records]
    return Bm25Index(chunk_ids=chunk_ids, _bm25=BM25Okapi(corpus))


def save_bm25(index: Bm25Index, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"chunk_ids": index.chunk_ids, "bm25": index._bm25}
    with path.open("wb") as fh:
        pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)


def load_bm25(path: Path) -> Bm25Index:
    with path.open("rb") as fh:
        payload = pickle.load(fh)
    return Bm25Index(chunk_ids=payload["chunk_ids"], _bm25=payload["bm25"])
