"""Lookup verified Fact Cards for grounded answers (LLM phrasing + template fallback)."""

from __future__ import annotations

from pathlib import Path

from core.retrieval.query_inference import infer_fact_tags, infer_scheme
from core.settings import load_settings
from ingest.processing.writer import load_facts
from schemas.fact_card import FactCard


def _processed_root(path: Path | None = None) -> Path:
    if path is not None:
        return path
    settings = load_settings()
    return Path(settings.get("paths", {}).get("data_processed", "data/processed"))


def load_fact_index(processed_root: Path | None = None) -> dict[tuple[str, str], FactCard]:
    """Map (source_id, fact_key) -> FactCard."""

    index: dict[tuple[str, str], FactCard] = {}
    for fact in load_facts(_processed_root(processed_root)):
        index[(fact.source_id, fact.fact_key)] = fact
    return index


def pick_fact_key(query: str, explicit_tags: list[str] | None = None) -> str | None:
    tags = explicit_tags if explicit_tags else infer_fact_tags(query)
    if not tags:
        return None
    return tags[0]


def lookup_fact_card(
    query: str,
    *,
    source_id: str | None = None,
    fact_key: str | None = None,
    processed_root: Path | None = None,
    require_verified: bool = True,
) -> FactCard | None:
    inference = infer_scheme(query)
    sid = source_id or inference.source_id
    key = fact_key or pick_fact_key(query)
    if not sid or not key:
        return None

    fact = load_fact_index(processed_root).get((sid, key))
    if fact is None:
        return None
    if require_verified and not fact.verified_by_human:
        return None
    if not fact.value_text or not str(fact.value_text).strip():
        return None
    return fact
