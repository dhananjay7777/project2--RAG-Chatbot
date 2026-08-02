"""Golden set loading and corpus constraints."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from eval.loader import GoldenValidationError, load_all_goldens, load_golden_set
from eval.metrics import TARGETS


def test_all_golden_sets_load_and_meet_size_floors():
    floors = {
        "factual": 60,
        "refusal": 25,
        "performance": 10,
        "pii": 10,
        "oos": 10,
        "adversarial": 15,
    }
    for name, floor in floors.items():
        cases = load_golden_set(name)
        assert len(cases) >= floor, f"{name} has {len(cases)} < {floor}"


def test_oos_includes_elss_and_statement_download():
    blob = " ".join(c.query.lower() for c in load_golden_set("oos"))
    assert "elss" in blob
    assert "capital gains statement" in blob or "account statement" in blob


def test_adversarial_includes_injection_and_advisor_roleplay():
    blob = " ".join(c.query.lower() for c in load_golden_set("adversarial"))
    assert "ignore" in blob
    assert "advisor" in blob or "advis" in blob
    assert "jailbreak" in blob or "pretend" in blob


def test_sixth_url_in_golden_is_rejected(tmp_path: Path):
    (tmp_path / "factual.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "set": "factual",
                "cases": [
                    {
                        "id": "bad-001",
                        "query": "What is expense ratio?",
                        "expected_route": "FACTUAL",
                        "expected_citation_url": "https://www.amfiindia.com/nav-history",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(GoldenValidationError, match="allowlist"):
        load_golden_set("factual", golden_dir=tmp_path)


def test_targets_include_compliance_critical_keys():
    assert TARGETS["citation_validity"] == 1.0
    assert TARGETS["constraint_compliance"] == 1.0
    assert TARGETS["hallucinated_number_rate"] == 0.0


def test_load_all_goldens_default():
    cases = load_all_goldens()
    assert len(cases) >= 60 + 25 + 10 + 10 + 10 + 15
