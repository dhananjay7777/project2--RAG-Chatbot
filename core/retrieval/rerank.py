"""Cross-encoder reranking."""

from __future__ import annotations

from typing import Protocol, Sequence


class Reranker(Protocol):
    def score_pairs(self, query: str, passages: Sequence[str]) -> list[float]: ...


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
        return self._model

    def score_pairs(self, query: str, passages: Sequence[str]) -> list[float]:
        if not passages:
            return []
        model = self._load()
        pairs = [(query, p) for p in passages]
        scores = model.predict(pairs)
        return [float(s) for s in scores]
