"""Lightweight scheme and fact-tag inference from query text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.settings import load_settings
from policy.loader import load_registry


@dataclass(frozen=True)
class QueryInference:
    source_id: str | None
    scheme_name: str | None
    scheme_confident: bool
    fact_tags: list[str]
    ambiguous_multi_asset: bool
    # True when the query only names an AMC brand (e.g. "nippon") without the
    # specific scheme — must not auto-bind to the one corpus fund for that brand.
    brand_only: bool = False


_FACT_KEYWORDS: list[tuple[str, str]] = [
    (r"\bexit\s*load\b", "exit_load"),
    (r"\bexpense\s*ratio\b|\bTER\b", "expense_ratio"),
    (
        r"\bminimum\s*SIP\b|\bmin\.?\s*SIP\b|\bmin\.?\s*for\s*SIP\b|\bSIP\s*minimum\b",
        "min_sip",
    ),
    (r"\bminimum\s*investment\b|\bmin\.?\s*for\s*1st\b|\blumpsum\b", "min_lumpsum"),
    (r"\bbenchmark\b", "benchmark"),
    (r"\bfund\s*manager\b|\bmanager\b", "fund_manager"),
    (r"\bAUM\b|\bfund\s*size\b|\bassets\s+under\s+management\b", "aum"),
    (r"\bNAV\b", "nav"),
    (r"\brisk\b|\briskometer\b", "risk_rating"),
    (r"\bcategor(y|ies)\b", "category"),
    (r"\binvestment\s*objective\b|\bobjective\b", "investment_objective"),
    (r"\bstandard\s*deviation\b", "standard_deviation"),
    (r"\bbeta\b", "beta"),
    (r"\bsharpe\b", "sharpe_ratio"),
    (r"\bsortino\b", "sortino_ratio"),
    (r"\balpha\b", "alpha"),
    (r"\binformation\s*ratio\b", "information_ratio"),
    (r"\btracking\s*error\b", "tracking_error"),
]

# Brand alone is insufficient — AMC houses have many schemes. Require a product
# token that identifies the one corpus scheme for that brand.
_BRAND_PRODUCT: list[tuple[str, str, str]] = [
    (
        "groww-nippon-india-value-fund-direct-growth",
        r"\bnippon\b",
        r"\bvalue\b",
    ),
    (
        "groww-tata-multi-asset-allocation-fund-direct-growth",
        r"\btata\b",
        r"\bmulti\s*asset\b",
    ),
    (
        "groww-kotak-multi-asset-allocation-fund-direct-growth",
        r"\bkotak\b",
        r"\bmulti\s*asset\b",
    ),
    (
        "groww-franklin-india-multi-cap-fund-direct-growth",
        r"\bfranklin\b",
        r"\bmulti\s*cap\b",
    ),
    (
        "groww-samco-mid-cap-fund-direct-growth",
        r"\bsamco\b",
        r"\bmid\s*cap\b",
    ),
]

_BRAND_ONLY = re.compile(
    r"\b(tata|kotak|nippon|franklin|samco)\b",
    re.I,
)


def _aliases(settings: dict[str, Any]) -> dict[str, list[str]]:
    retr = settings.get("retrieval") or {}
    raw = retr.get("scheme_aliases") or {}
    out: dict[str, list[str]] = {}
    if isinstance(raw, dict):
        for source_id, names in raw.items():
            if isinstance(names, list):
                out[str(source_id)] = [str(n) for n in names]
    return out


def infer_fact_tags(query: str) -> list[str]:
    tags: list[str] = []
    for pattern, tag in _FACT_KEYWORDS:
        if re.search(pattern, query, re.IGNORECASE):
            tags.append(tag)
    return tags


def infer_scheme(query: str) -> QueryInference:
    settings = load_settings()
    registry = load_registry()
    aliases = _aliases(settings)
    q_lower = query.lower()
    by_id = {row["source_id"]: row for row in registry["sources"]}

    matches: list[tuple[str, str, str]] = []  # source_id, scheme_name, matched_phrase
    for row in registry["sources"]:
        source_id = row["source_id"]
        scheme_names = list(row.get("scheme_names") or [])
        scheme_names.extend(aliases.get(source_id, []))
        for name in scheme_names:
            if name.lower() in q_lower:
                matches.append((source_id, str(row["scheme_names"][0]), name))

    # Brand + product token (e.g. "nippon" + "value") — not brand alone.
    for source_id, brand_re, product_re in _BRAND_PRODUCT:
        if source_id not in by_id:
            continue
        if re.search(brand_re, q_lower) and re.search(product_re, q_lower):
            if not any(m[0] == source_id for m in matches):
                scheme_name = str(by_id[source_id]["scheme_names"][0])
                matches.append((source_id, scheme_name, scheme_name))

    multi_asset_generic = (
        re.search(r"multi\s*asset\s*allocation", q_lower) is not None
        and not re.search(r"\btata\b", q_lower)
        and not re.search(r"\bkotak\b", q_lower)
    )
    tata_kotak = {m[0] for m in matches} & {
        "groww-tata-multi-asset-allocation-fund-direct-growth",
        "groww-kotak-multi-asset-allocation-fund-direct-growth",
    }
    ambiguous_multi_asset = multi_asset_generic or len(tata_kotak) > 1

    fact_tags = infer_fact_tags(query)
    brand_only = bool(_BRAND_ONLY.search(q_lower)) and not matches

    if not matches:
        return QueryInference(
            source_id=None,
            scheme_name=None,
            scheme_confident=False,
            fact_tags=fact_tags,
            ambiguous_multi_asset=ambiguous_multi_asset,
            brand_only=brand_only,
        )

    unique_sources = {m[0] for m in matches}
    if len(unique_sources) == 1:
        sid = next(iter(unique_sources))
        scheme_name = next(m[1] for m in matches if m[0] == sid)
        return QueryInference(
            source_id=sid,
            scheme_name=scheme_name,
            scheme_confident=not ambiguous_multi_asset,
            fact_tags=fact_tags,
            ambiguous_multi_asset=ambiguous_multi_asset,
            brand_only=False,
        )

    return QueryInference(
        source_id=None,
        scheme_name=None,
        scheme_confident=False,
        fact_tags=fact_tags,
        ambiguous_multi_asset=True,
        brand_only=False,
    )
