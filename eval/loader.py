"""Load and validate Phase 8 golden YAML sets."""

from __future__ import annotations

from pathlib import Path

import yaml

from eval.models import GoldenCase
from policy.loader import load_allowlist, load_registry
from schemas.answer import AnswerRoute

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
SET_FILES = {
    "factual": "factual.yaml",
    "refusal": "refusal.yaml",
    "performance": "performance.yaml",
    "pii": "pii.yaml",
    "oos": "oos.yaml",
    "adversarial": "adversarial.yaml",
}


class GoldenValidationError(ValueError):
    """Golden file violates corpus / allowlist constraints."""


def _allowed_source_ids() -> set[str]:
    return {row["source_id"] for row in load_registry()["sources"]}


def _parse_case(raw: dict, *, set_name: str, allowlist: set[str], source_ids: set[str]) -> GoldenCase:
    case_id = str(raw.get("id") or "").strip()
    query = str(raw.get("query") or "").strip()
    if not case_id or not query:
        raise GoldenValidationError(f"{set_name}: case missing id/query")

    route_name = str(raw.get("expected_route") or "").strip()
    try:
        expected_route = AnswerRoute(route_name)
    except ValueError as exc:
        raise GoldenValidationError(f"{case_id}: bad expected_route {route_name!r}") from exc

    source_id = raw.get("expected_source_id")
    if source_id is not None:
        source_id = str(source_id)
        if source_id not in source_ids:
            raise GoldenValidationError(
                f"{case_id}: expected_source_id {source_id!r} is not one of the five corpus sources"
            )

    citation_url = raw.get("expected_citation_url")
    if citation_url is not None:
        citation_url = str(citation_url).rstrip("/")
        # Allowlist entries may or may not have trailing slash — normalize via membership.
        if citation_url not in allowlist and f"{citation_url}/" not in allowlist:
            # Also try exact allowlist compare with canonicalize via set membership of stripped
            normalized = {u.rstrip("/") for u in allowlist}
            if citation_url.rstrip("/") not in normalized:
                raise GoldenValidationError(
                    f"{case_id}: expected_citation_url escapes the five-URL allowlist: {citation_url}"
                )

    return GoldenCase(
        id=case_id,
        set_name=set_name,
        query=query,
        expected_route=expected_route,
        expected_source_id=source_id,
        expected_value_contains=(
            str(raw["expected_value_contains"]) if raw.get("expected_value_contains") is not None else None
        ),
        fact_key=str(raw["fact_key"]) if raw.get("fact_key") is not None else None,
        assert_no_digits=bool(raw.get("assert_no_digits", False)),
        expected_citation_url=str(citation_url) if citation_url else None,
    )


def load_golden_set(name: str, *, golden_dir: Path | None = None) -> list[GoldenCase]:
    if name not in SET_FILES:
        raise GoldenValidationError(f"Unknown golden set: {name}")
    root = golden_dir or GOLDEN_DIR
    path = root / SET_FILES[name]
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases_raw = data.get("cases") or []
    allowlist = set(load_allowlist())
    source_ids = _allowed_source_ids()
    return [
        _parse_case(raw, set_name=name, allowlist=allowlist, source_ids=source_ids)
        for raw in cases_raw
    ]


def load_all_goldens(*, golden_dir: Path | None = None, sets: list[str] | None = None) -> list[GoldenCase]:
    names = sets or list(SET_FILES)
    out: list[GoldenCase] = []
    for name in names:
        out.extend(load_golden_set(name, golden_dir=golden_dir))
    return out
