"""Dense vector store (Chroma when available, else local pickle)."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Protocol, Sequence

from ingest.indexing.models import ChunkIndexRecord

COLLECTION_NAME = "mf_faq_chunks"


def _metadata(record: ChunkIndexRecord) -> dict[str, Any]:
    return {
        "chunk_id": record.chunk_id,
        "source_id": record.source_id,
        "scheme_name": record.scheme_name,
        "status": record.status,
        "doc_type": record.doc_type,
        "fact_tags": ",".join(record.fact_tags),
        "effective_date": record.effective_date or "",
        "content_hash": record.content_hash,
    }


class DenseVectorStore(Protocol):
    def upsert(
        self,
        records: Sequence[ChunkIndexRecord],
        embeddings: Sequence[Sequence[float]],
    ) -> None: ...

    def delete_ids(self, chunk_ids: Sequence[str]) -> None: ...

    def query_dense(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]: ...


class FileDenseStore:
    """Small-corpus dense index (no native deps)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._records: dict[str, ChunkIndexRecord] = {}
        self._embeddings: dict[str, list[float]] = {}
        if path.is_file():
            with path.open("rb") as fh:
                payload = pickle.load(fh)
            self._records = payload["records"]
            self._embeddings = payload["embeddings"]

    def upsert(
        self,
        records: Sequence[ChunkIndexRecord],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        for record, emb in zip(records, embeddings):
            self._records[record.chunk_id] = record
            self._embeddings[record.chunk_id] = list(emb)
        self._persist()

    def delete_ids(self, chunk_ids: Sequence[str]) -> None:
        for cid in chunk_ids:
            self._records.pop(cid, None)
            self._embeddings.pop(cid, None)
        self._persist()

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("wb") as fh:
            pickle.dump(
                {"records": self._records, "embeddings": self._embeddings},
                fh,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

    def _matches_where(self, record: ChunkIndexRecord, where: dict[str, Any] | None) -> bool:
        if not where:
            return True
        for key, value in where.items():
            if key == "status" and record.status != value:
                return False
            if key == "source_id" and record.source_id != value:
                return False
        return True

    @staticmethod
    def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def query_dense(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for cid, emb in self._embeddings.items():
            record = self._records.get(cid)
            if record is None or not self._matches_where(record, where):
                continue
            scored.append((cid, self._cosine(query_embedding, emb)))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


class ChromaChunkStore:
    def __init__(self, persist_dir: Path, collection_name: str = COLLECTION_NAME) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        records: Sequence[ChunkIndexRecord],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if not records:
            return
        ids = [r.chunk_id for r in records]
        documents = [r.index_text for r in records]
        metadatas = [_metadata(r) for r in records]
        self._collection.upsert(
            ids=ids,
            embeddings=list(embeddings),
            documents=documents,
            metadatas=metadatas,
        )

    def delete_ids(self, chunk_ids: Sequence[str]) -> None:
        if chunk_ids:
            self._collection.delete(ids=list(chunk_ids))

    def query_dense(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int,
        where: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        kwargs: dict[str, Any] = {
            "query_embeddings": [list(query_embedding)],
            "n_results": top_k,
            "include": ["distances"],
        }
        if where:
            kwargs["where"] = where
        result = self._collection.query(**kwargs)
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [(cid, float(1.0 - dist)) for cid, dist in zip(ids, distances)]


def create_dense_store(index_root: Path) -> DenseVectorStore:
    chroma_dir = index_root / "chroma"
    dense_path = index_root / "dense_vectors.pkl"
    try:
        import chromadb  # noqa: F401

        return ChromaChunkStore(chroma_dir)
    except Exception:
        return FileDenseStore(dense_path)
