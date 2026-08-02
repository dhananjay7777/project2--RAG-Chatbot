"""Phase 6 validator and composer tests."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from core.compose import compose_answer, synthesis_to_draft
from core.synthesis.models import SynthesisPath, SynthesisResult
from core.synthesis.pipeline import synthesize_fact_card
from core.validate.context import ValidationContext
from core.validate.models import FailAction
from core.validate.sentences import sentence_count, split_sentences
from core.validate.chain import run_validation_chain
from core.validate.validators import (
    check_advice_lexicon,
    check_citation_allowlist,
    check_groundedness,
    check_performance_no_digits,
    format_footer,
)
from schemas.answer import AnswerRoute
from schemas.fact_card import FactCard

ROOT = Path(__file__).resolve().parents[2]


def test_sentence_segmenter_respects_rs_and_percent():
    text = "Min investment is Rs. 500. Expense ratio is 1.5%."
    assert sentence_count(text) == 2


def test_citation_allowlist_rejects_hub_url():
    ctx = ValidationContext(
        query_id=uuid4(),
        route=AnswerRoute.FACTUAL,
        answer_body="The expense ratio is 1.27%.",
        citation_url="https://groww.in/mutual-funds",
        citation_label="Groww",
        source_id="x",
        footer=format_footer(date(2026, 7, 24)),
        skip_groundedness=True,
    )
    result = check_citation_allowlist(ctx)
    assert not result.passed
    assert result.action == FailAction.HARD_FAIL


def test_groundedness_catches_wrong_percent():
    ctx = ValidationContext(
        query_id=uuid4(),
        route=AnswerRoute.FACTUAL,
        answer_body="The expense ratio is 1.28%.",
        citation_url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
        citation_label="Nippon — Groww",
        source_id="groww-nippon-india-value-fund-direct-growth",
        footer=format_footer(date(2026, 7, 24)),
        supporting_texts=["Expense ratio 1.27%"],
        effective_dates=[date(2026, 7, 24)],
    )
    result = check_groundedness(ctx)
    assert not result.passed
    assert result.action == FailAction.HARD_FAIL


def test_advice_lexicon_hard_fail():
    ctx = ValidationContext(
        query_id=uuid4(),
        route=AnswerRoute.FACTUAL,
        answer_body="You should consider this fund.",
        citation_url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
        citation_label="Nippon — Groww",
        source_id="groww-nippon-india-value-fund-direct-growth",
        footer=format_footer(date(2026, 7, 24)),
        skip_groundedness=True,
    )
    assert not check_advice_lexicon(ctx).passed


def test_performance_redirect_no_digits():
    ctx = ValidationContext(
        query_id=uuid4(),
        route=AnswerRoute.PERFORMANCE_REDIRECT,
        answer_body="Please view returns on the scheme page.",
        citation_url="https://groww.in/mutual-funds/samco-mid-cap-fund-direct-growth",
        citation_label="Samco — Groww",
        source_id="groww-samco-mid-cap-fund-direct-growth",
        footer=format_footer(date(2026, 7, 24)),
        skip_groundedness=True,
    )
    assert check_performance_no_digits(ctx).passed
    ctx.answer_body = "Return was 15.9% last year."
    assert not check_performance_no_digits(ctx).passed


def test_repair_strips_url_from_body():
    synthesis = SynthesisResult(
        path=SynthesisPath.ROUTER,
        route=AnswerRoute.REFUSAL,
        answer_text=(
            "I can only share facts from the listed Groww scheme pages.\n"
            "Please ask about expense ratio or exit load.\n"
            "Source: https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth"
        ),
        citation_url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
        citation_label="Nippon — Groww",
        source_id="groww-nippon-india-value-fund-direct-growth",
    )
    env = compose_answer(synthesis)
    assert "groww.in" not in env.answer.lower()
    assert env.validator_report.passed
    assert env.citation.url
    assert env.footer.startswith("Last updated from sources:")


@pytest.mark.skipif(not (ROOT / "data/processed/facts.jsonl").is_file(), reason="no corpus")
def test_compose_fact_card_passes_validation():
    fact = FactCard(
        fact_key="expense_ratio",
        scheme_name="Nippon India Value Fund Direct Growth",
        value_text="1.27%",
        source_id="groww-nippon-india-value-fund-direct-growth",
        chunk_id="groww-nippon-india-value-fund-direct-growth#002",
        effective_date=date(2026, 7, 24),
        verified_by_human=True,
    )
    synth = synthesize_fact_card(fact, "expense ratio?")
    env = compose_answer(synth, processed_root=ROOT / "data/processed")
    assert env.validator_report.passed
    assert "1.27%" in env.answer
    assert env.sentence_count <= 3


def test_hard_fail_uses_canned_envelope():
    ctx = ValidationContext(
        query_id=uuid4(),
        route=AnswerRoute.FACTUAL,
        answer_body="The expense ratio is 9.99%.",
        citation_url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
        citation_label="Nippon — Groww",
        source_id="groww-nippon-india-value-fund-direct-growth",
        footer=format_footer(date(2026, 7, 24)),
        supporting_texts=["Expense ratio 1.27%"],
        effective_dates=[date(2026, 7, 24)],
    )
    final_ctx, chain = run_validation_chain(ctx)
    assert chain.used_canned
    assert final_ctx.route == AnswerRoute.NO_ANSWER
    assert final_ctx.answer_body


def test_staleness_annotates_footer_instead_of_canned_refusal():
    old = date.today() - timedelta(days=30)
    ctx = ValidationContext(
        query_id=uuid4(),
        route=AnswerRoute.FACTUAL,
        answer_body="The expense ratio is 1.27%.",
        citation_url="https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth",
        citation_label="Nippon — Groww",
        source_id="groww-nippon-india-value-fund-direct-growth",
        footer=format_footer(old),
        supporting_texts=["Expense ratio 1.27%"],
        effective_dates=[old],
        fact_key="expense_ratio",
        skip_groundedness=False,
    )
    final_ctx, chain = run_validation_chain(ctx)
    assert not chain.used_canned
    assert final_ctx.route == AnswerRoute.FACTUAL
    assert "1.27%" in final_ctx.answer_body
    assert "outdated" in final_ctx.footer.lower() or "sla" in final_ctx.footer.lower()
    assert chain.repairs_applied >= 1
    assert any(
        c.validator == "Staleness" and (not c.passed or (c.details or {}).get("annotated"))
        for c in chain.checks
    )
