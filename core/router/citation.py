"""Resolve allowlisted citations for router responses."""

from __future__ import annotations

from core.retrieval.query_inference import infer_scheme
from policy.taxonomy import (
    default_citation_source_id,
    default_citation_url,
    registry_by_source_id,
)


def resolve_citation(query: str, *, last_source_id: str | None = None) -> tuple[str, str, str]:
    """Return (url, label, source_id) from the five-URL registry."""

    by_id = registry_by_source_id()
    inference = infer_scheme(query)
    source_id = inference.source_id or last_source_id or default_citation_source_id()
    if source_id not in by_id:
        source_id = default_citation_source_id()
    row = by_id[source_id]
    url = str(row["url"])
    label = str(row.get("default_citation_label") or row["scheme_names"][0])
    return url, label, source_id


def fallback_citation() -> tuple[str, str, str]:
    by_id = registry_by_source_id()
    source_id = default_citation_source_id()
    row = by_id[source_id]
    return str(row["url"]), str(row.get("default_citation_label", "")), source_id


def ensure_allowlisted(url: str) -> str:
    from policy.loader import is_allowlisted

    if is_allowlisted(url):
        return url
    return default_citation_url()
