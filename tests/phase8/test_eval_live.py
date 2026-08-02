"""Live eval against ask() on frozen local artifacts (no live Groww fetch)."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest

from eval.metrics import COMPLIANCE_CRITICAL
from eval.scorecard import run_eval

ROOT = Path(__file__).resolve().parents[2]
FACTS = ROOT / "data" / "processed" / "facts.jsonl"

GUARDRAIL_SETS = ["refusal", "performance", "pii", "oos", "adversarial"]


def _freeze_as_of() -> None:
    if not FACTS.is_file():
        return
    latest: date | None = None
    for line in FACTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line).get("effective_date")
        if not raw:
            continue
        d = date.fromisoformat(str(raw)[:10])
        if latest is None or d > latest:
            latest = d
    if latest is not None:
        os.environ["MF_AS_OF_DATE"] = latest.isoformat()


@pytest.fixture(autouse=True)
def _as_of_env():
    previous = os.environ.get("MF_AS_OF_DATE")
    _freeze_as_of()
    yield
    if previous is None:
        os.environ.pop("MF_AS_OF_DATE", None)
    else:
        os.environ["MF_AS_OF_DATE"] = previous


@pytest.mark.slow
def test_guardrail_sets_meet_compliance_critical_gates():
    scorecard = run_eval(sets=GUARDRAIL_SETS, strict_latency=False)
    for name in COMPLIANCE_CRITICAL:
        assert scorecard.gates.get(name) is True, (
            name,
            scorecard.metrics,
            scorecard.meta.get("failed_cases"),
        )
    assert scorecard.gates.get("refusal_recall") is True
    assert scorecard.gates.get("refusal_precision") is True


@pytest.mark.slow
@pytest.mark.skipif(not FACTS.is_file(), reason="processed Fact Cards not present")
def test_factual_set_accuracy_on_fact_cards():
    from core.llm.client import is_groq_configured

    if not is_groq_configured():
        pytest.skip("GROQ_API_KEY required for RAG factual eval")
    scorecard = run_eval(sets=["factual"], strict_latency=False)
    assert scorecard.metrics["exact_fact_accuracy"] >= 0.95, scorecard.meta.get("failed_cases")
    assert scorecard.gates.get("citation_validity") is True
    assert scorecard.gates.get("constraint_compliance") is True
