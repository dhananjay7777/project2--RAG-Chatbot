"""Phase 2 unit and integration tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ingest.processing.chunk import chunk_document
from ingest.processing.facts import extract_pass_a, load_fact_seed, verify_against_seed
from ingest.processing.normalize import normalize_currency_and_percent, synonym_field
from ingest.processing.parse import parse_artifact
from ingest.processing.pii import scrub_pii
from ingest.processing.pipeline import process_corpus
from ingest.processing.strip import strip_audit_violations, strip_document

ROOT = Path(__file__).resolve().parents[2]
NIPPON_MD = (
    ROOT
    / "data"
    / "raw"
    / "groww-nippon-india-value-fund-direct-growth"
    / "4e6678169c887e9cfa84493405d5b5352cd9e9fb74ebfe75a162e0ba9d966e3f.md"
)


@pytest.fixture
def nippon_doc():
    return parse_artifact(
        NIPPON_MD,
        source_id="groww-nippon-india-value-fund-direct-growth",
        scheme_name="Nippon India Value Fund Direct Growth",
        effective_date=date(2026, 7, 24),
    )


def test_normalize_currency_and_percent():
    assert "1.27%" in normalize_currency_and_percent("1.27 %")
    assert "INR" in normalize_currency_and_percent("Rs.100")


def test_synonym_field_expands_abbreviations():
    syn = synonym_field("SIP and NAV and AUM and TER")
    assert "Systematic Investment Plan" in syn
    assert "Net Asset Value" in syn


def test_pii_redacts_pan():
    result = scrub_pii("Contact PAN ABCDE1234F please")
    assert "[REDACTED:PAN]" in result.text
    assert result.pii_scan in {"redacted", "quarantined"}


def test_strip_removes_returns_and_holdings(nippon_doc):
    stripped = strip_document(nippon_doc)
    blob = "\n".join(s.heading.lower() + "\n" + s.text.lower() for s in stripped.sections)
    assert "return calculator" not in blob
    assert "returns and rankings" not in blob
    assert "also manages these schemes" not in blob
    assert not any(s.heading.lower().startswith("holdings") for s in stripped.sections)


def test_exit_load_stays_together(nippon_doc):
    stripped = strip_document(nippon_doc)
    chunks = chunk_document(stripped)
    exit_chunks = [c for c in chunks if "exit_load" in c.fact_tags]
    assert exit_chunks
    joined = " ".join(c.text for c in exit_chunks)
    assert "1%" in joined
    assert "12 months" in joined or "12 month" in joined


def test_pass_a_extracts_core_nippon_facts(nippon_doc):
    facts = extract_pass_a(strip_document(nippon_doc))
    assert facts["expense_ratio"] == "1.27%"
    assert facts["min_sip"] == "₹100"
    assert facts["aum"] == "₹8,962.36 Cr"
    assert facts["benchmark"] and "NIFTY 500" in facts["benchmark"]
    assert "10%" in (facts["exit_load"] or "")


def test_pass_a_extracts_all_franklin_fund_managers():
    path = (
        ROOT
        / "data"
        / "raw"
        / "groww-franklin-india-multi-cap-fund-direct-growth"
        / "7af12341599c1bb6d42d87e1102fa608096366470a0f699942ca5192c64cad49.md"
    )
    doc = parse_artifact(
        path,
        source_id="groww-franklin-india-multi-cap-fund-direct-growth",
        scheme_name="Franklin India Multi Cap Fund Direct Growth",
        effective_date=date(2026, 7, 24),
    )
    facts = extract_pass_a(strip_document(doc))
    managers = [m.strip() for m in (facts["fund_manager"] or "").split(",") if m.strip()]
    assert managers == [
        "Akhil Kalluri",
        "R Janakiraman",
        "Kiran Sebastian",
        "Sandeep Manam",
    ]


def test_fund_manager_verification_prefers_page_list_over_partial_seed():
    seed = load_fact_seed()
    extracted = {
        "expense_ratio": "0.93%",
        "exit_load": "Exit load of 1%, if redeemed within 1 year.",
        "min_sip": "₹500",
        "min_lumpsum": "₹5,000",
        "risk_rating": "Very High Risk",
        "category": "Equity — Multi Cap",
        "aum": "₹5,029.48 Cr",
        "nav": "₹10.94 (as of 24 Jul 2026)",
        "benchmark": "Nifty 500 Multicap 50:25:25 Total Return Index",
        "launch_date": "19 Feb 1996",
        "fund_manager": "Akhil Kalluri, R Janakiraman, Kiran Sebastian, Sandeep Manam",
        "stamp_duty": "0.005%",
        "tax_implication_text": seed["schemes"][
            "groww-franklin-india-multi-cap-fund-direct-growth"
        ]["facts"]["tax_implication_text"],
        "investment_objective": None,
        "top_5_concentration": None,
        "top_20_concentration": None,
        "pe_ratio": None,
        "pb_ratio": None,
        "alpha": None,
        "beta": None,
        "sharpe": None,
        "sortino": None,
    }
    # Simulate outdated seed that only kept the first manager
    seed["schemes"]["groww-franklin-india-multi-cap-fund-direct-growth"]["facts"][
        "fund_manager"
    ] = "Akhil Kalluri"
    cards = verify_against_seed(
        "groww-franklin-india-multi-cap-fund-direct-growth", extracted, seed
    )
    assert cards["fund_manager"].verified_by_human is True
    assert "R Janakiraman" in (cards["fund_manager"].value_text or "")
    assert "Sandeep Manam" in (cards["fund_manager"].value_text or "")


def test_samco_aum_uses_hero_not_fund_house():
    path = (
        ROOT
        / "data"
        / "raw"
        / "groww-samco-mid-cap-fund-direct-growth"
        / "8a8b01efbc188ea4092d82965cabc1542f69e913f7c8dd02f8aa99dc528ed43a.md"
    )
    doc = parse_artifact(
        path,
        source_id="groww-samco-mid-cap-fund-direct-growth",
        scheme_name="Samco Mid Cap Fund Direct Growth",
        effective_date=date(2026, 7, 24),
    )
    facts = extract_pass_a(strip_document(doc))
    assert facts["aum"] == "₹78.64 Cr"


def test_tata_benchmark_null():
    path = (
        ROOT
        / "data"
        / "raw"
        / "groww-tata-multi-asset-allocation-fund-direct-growth"
        / "b6d1ec849ecbb988d497abeb8fa993df3101e3fe736588a9ba0ff5f3418acb4a.md"
    )
    doc = parse_artifact(
        path,
        source_id="groww-tata-multi-asset-allocation-fund-direct-growth",
        scheme_name="Tata Multi Asset Allocation Fund Direct Growth",
        effective_date=date(2026, 7, 24),
    )
    facts = extract_pass_a(strip_document(doc))
    assert facts["benchmark"] is None


def test_seed_verification_marks_verified():
    seed = load_fact_seed()
    extracted = {
        "expense_ratio": "1.27%",
        "exit_load": "For units more than 10% of the investments, an exit load of 1% if redeemed within 12 months.",
        "min_sip": "₹100",
        "min_lumpsum": "₹500",
        "risk_rating": "Very High Risk",
        "category": "Equity — Value Oriented",
        "aum": "₹8,962.36 Cr",
        "nav": "₹244.42 (as of 24 Jul 2026)",
        "benchmark": "NIFTY 500 Total Return Index",
        "launch_date": "30 Jun 1995",
        "fund_manager": "Amber Singhania",
        "stamp_duty": "0.005%",
        "tax_implication_text": (
            "If you redeem within one year, returns are taxed at 20%. "
            "If you redeem after one year, returns exceeding Rs 1.25 lakh "
            "in a financial year are taxed at 12.5%."
        ),
        "investment_objective": (
            "The scheme seeks capital appreciation and/or to generate consistent "
            "returns by actively investing in equity/ equity related securities "
            "predominantly into value stocks."
        ),
        "top_5_concentration": None,
        "top_20_concentration": None,
        "pe_ratio": None,
        "pb_ratio": None,
        "alpha": None,
        "beta": None,
        "sharpe": None,
        "sortino": None,
    }
    cards = verify_against_seed(
        "groww-nippon-india-value-fund-direct-growth", extracted, seed
    )
    assert cards["expense_ratio"].verified_by_human is True
    assert cards["benchmark"].value_text is not None


def test_live_nav_overrides_stale_seed():
    seed = load_fact_seed()
    extracted = {
        key: seed["schemes"]["groww-nippon-india-value-fund-direct-growth"]["facts"].get(
            key
        )
        for key in seed["in_scope_keys"]
    }
    extracted["nav"] = "₹250.01 (as of 31 Jul 2026)"
    extracted["aum"] = "₹9,000.00 Cr"
    cards = verify_against_seed(
        "groww-nippon-india-value-fund-direct-growth", extracted, seed
    )
    assert cards["nav"].value_text == "₹250.01 (as of 31 Jul 2026)"
    assert cards["aum"].value_text == "₹9,000.00 Cr"
    assert cards["nav"].verified_by_human is True


def test_html_nav_extracted_from_div_markup(tmp_path: Path):
    from ingest.processing.parse import parse_artifact

    html = """
    <html><body>
    <div>NAV: 31 Jul '26</div><div>₹250.01</div>
    <div>Fund size (AUM)</div><div>₹8,962.36 Cr</div>
    <p>The Latest NAV as of 31 Jul 2026 is ₹250.01.</p>
    </body></html>
    """
    path = tmp_path / "scheme.html"
    path.write_text(html, encoding="utf-8")
    doc = parse_artifact(
        path,
        source_id="groww-nippon-india-value-fund-direct-growth",
        scheme_name="Nippon India Value Fund Direct Growth",
    )
    assert doc.hero_metrics.get("nav_value") == "₹250.01"
    assert doc.effective_date == date(2026, 7, 31)


@pytest.mark.skipif(not NIPPON_MD.exists(), reason="raw corpus not bootstrapped")
def test_process_corpus_integration(tmp_path):
    raw = ROOT / "data" / "raw"
    out = tmp_path / "processed"
    chunks, facts, results = process_corpus(
        raw_root=raw,
        processed_root=out,
        require_verified=True,
    )
    assert len(results) == 5
    assert len(chunks) > 0
    assert len(facts) >= 5 * 10
    assert all(c.pii_scan != "quarantined" for c in chunks)
    violations = strip_audit_violations("\n".join(c.text for c in chunks))
    critical = [v for v in violations if v != "holdings table remnant"]
    assert critical == []
    assert (out / "chunks.jsonl").exists()
    assert (out / "facts.jsonl").exists()
