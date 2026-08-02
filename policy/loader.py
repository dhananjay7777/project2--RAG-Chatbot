"""Load and validate source allowlist / registry (Phase 0)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import yaml

from policy import POLICY_DIR

CANONICAL_COUNT = 5
ALLOWED_MODES = {"exact_url"}


class AllowlistError(ValueError):
    """Raised when allowlist/registry policy is invalid."""


def canonicalize_url(url: str) -> str:
    """Normalize to https, lowercase host, no trailing slash, no query/fragment."""
    raw = url.strip()
    parsed = urlparse(raw)
    if parsed.scheme.lower() != "https":
        raise AllowlistError(f"Only https URLs allowed, got: {url!r}")
    if not parsed.netloc:
        raise AllowlistError(f"Invalid URL: {url!r}")
    path = parsed.path.rstrip("/")
    if not path:
        raise AllowlistError(f"URL path required (no bare domain): {url!r}")
    # Reject wildcards / glob-like entries
    if "*" in raw or raw.endswith("/*") or "groww.in/*" in raw:
        raise AllowlistError(f"Domain wildcards are forbidden: {url!r}")
    canonical = urlunparse(
        ("https", parsed.netloc.lower(), path, "", "", "")
    )
    return canonical


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise AllowlistError(f"Expected mapping in {path}")
    return data


def load_allowlist(path: Path | None = None) -> list[str]:
    path = path or (POLICY_DIR / "source_allowlist.yaml")
    data = load_yaml(path)

    mode = data.get("allowlist_mode")
    if mode not in ALLOWED_MODES:
        raise AllowlistError(
            f"allowlist_mode must be one of {ALLOWED_MODES}, got {mode!r}"
        )

    urls_raw = data.get("urls")
    if not isinstance(urls_raw, list):
        raise AllowlistError("urls must be a list")

    urls = [canonicalize_url(u) for u in urls_raw]
    expected = data.get("expected_count", CANONICAL_COUNT)
    if len(urls) != expected:
        raise AllowlistError(
            f"Allowlist cardinality must be {expected}, got {len(urls)}"
        )
    if len(set(urls)) != len(urls):
        raise AllowlistError("Allowlist contains duplicate URLs")

    # Hard reject domain-only / wildcard style entries
    for u in urls_raw:
        if "*" in str(u) or str(u).rstrip("/").endswith("groww.in"):
            raise AllowlistError(f"Invalid allowlist entry: {u!r}")

    return urls


def is_allowlisted(url: str, allowlist: list[str] | None = None) -> bool:
    allowlist = allowlist or load_allowlist()
    try:
        return canonicalize_url(url) in allowlist
    except AllowlistError:
        return False


def load_registry(path: Path | None = None) -> dict[str, Any]:
    path = path or (POLICY_DIR / "source_registry.yaml")
    data = load_yaml(path)
    sources = data.get("sources")
    if not isinstance(sources, list) or len(sources) != CANONICAL_COUNT:
        raise AllowlistError(
            f"Registry must contain exactly {CANONICAL_COUNT} sources"
        )

    allowlist = set(load_allowlist())
    registry_urls = []
    for row in sources:
        url = canonicalize_url(row["url"])
        registry_urls.append(url)
        if url not in allowlist:
            raise AllowlistError(
                f"Registry URL not in allowlist: {url}"
            )
        if row.get("doc_type") != "GROWW_SCHEME_PAGE":
            raise AllowlistError(
                f"Invalid doc_type for {row.get('source_id')}"
            )

    if set(registry_urls) != allowlist:
        raise AllowlistError("Registry URLs must match allowlist exactly")

    return data
