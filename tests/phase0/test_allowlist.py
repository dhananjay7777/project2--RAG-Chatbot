"""Phase 0 — allowlist cardinality, exact-URL mode, registry match."""

from pathlib import Path

import pytest
import yaml

from policy.loader import (
    AllowlistError,
    canonicalize_url,
    is_allowlisted,
    load_allowlist,
    load_registry,
)

ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = ROOT / "policy" / "source_allowlist.yaml"


def test_load_allowlist_exactly_five():
    urls = load_allowlist()
    assert len(urls) == 5
    assert len(set(urls)) == 5


def test_allowlist_mode_exact_url():
    data = yaml.safe_load(ALLOWLIST.read_text(encoding="utf-8"))
    assert data["allowlist_mode"] == "exact_url"


def test_reject_wildcard_url():
    with pytest.raises(AllowlistError):
        canonicalize_url("https://*.groww.in/mutual-funds/x")


def test_reject_http_scheme():
    with pytest.raises(AllowlistError):
        canonicalize_url(
            "http://groww.in/mutual-funds/nippon-india-value-fund-direct-growth"
        )


def test_reject_bare_domain():
    with pytest.raises(AllowlistError):
        canonicalize_url("https://groww.in/")


def test_is_allowlisted_positive():
    assert is_allowlisted(
        "https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth"
    )


def test_is_allowlisted_rejects_hub_and_sixth_url():
    assert not is_allowlisted("https://groww.in/mutual-funds")
    assert not is_allowlisted(
        "https://groww.in/mutual-funds/hdfc-flexi-cap-fund-direct-growth"
    )
    assert not is_allowlisted("https://www.amfiindia.com/")


def test_trailing_slash_canonicalizes_to_allowlisted():
    assert is_allowlisted(
        "https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth/"
    )


def test_registry_matches_allowlist():
    data = load_registry()
    assert len(data["sources"]) == 5
    assert data["default_citation_source_id"].startswith("groww-")


def test_allowlist_file_rejects_wrong_cardinality(tmp_path: Path):
    bad = tmp_path / "bad_allowlist.yaml"
    bad.write_text(
        """
allowlist_mode: exact_url
expected_count: 5
urls:
  - https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth
  - https://groww.in/mutual-funds/tata-multi-asset-allocation-fund-direct-growth
  - https://groww.in/mutual-funds/kotak-multi-asset-allocation-fund-direct-growth
  - https://groww.in/mutual-funds/franklin-india-multi-cap-fund-direct-growth
""",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistError, match="cardinality"):
        load_allowlist(bad)


def test_allowlist_rejects_non_exact_mode(tmp_path: Path):
    bad = tmp_path / "domain_mode.yaml"
    bad.write_text(
        """
allowlist_mode: domain
expected_count: 5
urls:
  - https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth
  - https://groww.in/mutual-funds/tata-multi-asset-allocation-fund-direct-growth
  - https://groww.in/mutual-funds/kotak-multi-asset-allocation-fund-direct-growth
  - https://groww.in/mutual-funds/franklin-india-multi-cap-fund-direct-growth
  - https://groww.in/mutual-funds/samco-mid-cap-fund-direct-growth
""",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistError, match="allowlist_mode"):
        load_allowlist(bad)
