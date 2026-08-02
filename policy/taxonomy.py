"""Load refusal taxonomy (Phase 4)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from policy import POLICY_DIR
from policy.loader import load_registry


class TaxonomyError(ValueError):
    pass


def load_refusal_taxonomy(path: Path | None = None) -> dict[str, Any]:
    path = path or (POLICY_DIR / "refusal_taxonomy.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TaxonomyError("refusal_taxonomy.yaml must be a mapping")
    return data


@lru_cache(maxsize=1)
def intent_classes() -> dict[str, dict[str, Any]]:
    data = load_refusal_taxonomy()
    classes = data.get("classes")
    if not isinstance(classes, dict):
        raise TaxonomyError("classes mapping required")
    return classes


def default_citation_url() -> str:
    return str(load_refusal_taxonomy()["default_citation_url"])


def registry_by_source_id() -> dict[str, dict[str, Any]]:
    reg = load_registry()
    return {row["source_id"]: row for row in reg["sources"]}


def default_citation_source_id() -> str:
    reg = load_registry()
    return str(reg.get("default_citation_source_id") or reg["sources"][0]["source_id"])
