"""Dense embeddings with BAAI/bge-small-en-v1.5."""

from __future__ import annotations

from typing import Protocol, Sequence

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder(Protocol):
    def encode_queries(self, texts: Sequence[str]) -> list[list[float]]: ...

    def encode_passages(self, texts: Sequence[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Lazy-load sentence-transformers to keep import cost out of unit tests."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def encode_queries(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        prefixed = [QUERY_PREFIX + t for t in texts]
        vectors = model.encode(prefixed, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def encode_passages(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(list(texts), normalize_embeddings=True)
        return [v.tolist() for v in vectors]
