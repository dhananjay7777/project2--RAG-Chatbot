"""Phase 7 UI contract tests (presenter + API, no browser needed)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from app.api.main import health
from app.ui.presenter import (
    DISCLAIMER,
    WELCOME_BODY,
    WELCOME_TITLE,
    check_input,
    corpus_scheme_names,
    detect_pii_warnings,
    envelope_to_view,
    error_view,
    example_questions,
    max_input_chars,
)
from policy.loader import load_allowlist
from schemas.answer import (
    AnswerEnvelope,
    AnswerRoute,
    Citation,
    ValidatorReport,
)

ALLOWLISTED = "https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth"


def _envelope(
    route: AnswerRoute = AnswerRoute.FACTUAL,
    url: str = ALLOWLISTED,
    answer: str = "The expense ratio of Nippon India Value Fund Direct Growth is 1.27%.",
) -> AnswerEnvelope:
    return AnswerEnvelope(
        query_id=uuid4(),
        route=route,
        answer=answer,
        sentence_count=1,
        citation=Citation(
            url=url,
            source_id="groww-nippon-india-value-fund-direct-growth",
            label="Nippon India Value Fund Direct Growth — Groww",
        ),
        footer="Last updated from sources: 24 Jul 2026",
        confidence=0.95,
        validator_report=ValidatorReport(passed=True),
    )


def test_required_elements_present():
    assert WELCOME_TITLE and WELCOME_BODY
    assert DISCLAIMER == "Facts-only. No investment advice."
    assert health()["disclaimer"] == DISCLAIMER


def test_corpus_lists_exactly_five_scheme_names():
    names = corpus_scheme_names()
    assert len(names) == 5
    blob = " ".join(names).lower()
    assert "nippon india value" in blob
    assert "tata multi asset" in blob
    assert "kotak multi asset" in blob
    assert "franklin india multi cap" in blob
    assert "samco mid cap" in blob


def test_exactly_three_example_questions_covering_boundaries():
    questions = example_questions()
    assert len(questions) == 3
    blob = " ".join(questions).lower()
    assert "exit load" in blob
    assert "minimum sip" in blob
    assert "should i invest" in blob


def test_empty_input_blocks_submit():
    check = check_input("   ")
    assert not check.ok
    assert check.error


def test_over_length_input_blocks_submit():
    limit = max_input_chars()
    check = check_input("a" * (limit + 1))
    assert not check.ok
    assert str(limit) in (check.error or "")


def test_pan_in_input_warns_before_submit():
    warnings = detect_pii_warnings("My PAN is ABCDE1234F, what is the exit load?")
    assert warnings
    assert "PAN" in warnings[0]


def test_clean_input_has_no_warnings():
    check = check_input("What is the exit load on Nippon India Value Fund Direct Growth?")
    assert check.ok
    assert check.warnings == []


def test_factual_view_renders_citation_and_footer():
    view = envelope_to_view(_envelope())
    assert view.citation_url in set(load_allowlist())
    assert view.citation_label
    assert view.footer.startswith("Last updated from sources:")
    assert view.tone == "factual"


@pytest.mark.parametrize(
    "route,tone",
    [
        (AnswerRoute.REFUSAL, "refusal"),
        (AnswerRoute.PERFORMANCE_REDIRECT, "redirect"),
        (AnswerRoute.NO_ANSWER, "empty"),
        (AnswerRoute.CLARIFY, "clarify"),
    ],
)
def test_each_route_has_distinct_styling(route: AnswerRoute, tone: str):
    view = envelope_to_view(_envelope(route=route))
    factual = envelope_to_view(_envelope())
    assert view.tone == tone
    assert view.tone != factual.tone
    assert view.accent != factual.accent


@pytest.mark.parametrize(
    "route",
    [
        AnswerRoute.REFUSAL,
        AnswerRoute.PERFORMANCE_REDIRECT,
        AnswerRoute.NO_ANSWER,
        AnswerRoute.CLARIFY,
    ],
)
def test_non_factual_routes_hide_citation_link(route: AnswerRoute):
    view = envelope_to_view(_envelope(route=route))
    assert view.citation_url is None
    assert view.citation_label == ""
    assert view.footer == ""


def test_non_allowlisted_citation_is_not_rendered_as_link():
    view = envelope_to_view(_envelope(url="https://www.amfiindia.com/"))
    assert view.citation_url is None


def test_error_view_is_user_safe():
    view = error_view("The assistant could not complete that lookup just now.")
    assert view.route == AnswerRoute.NO_ANSWER
    assert "Traceback" not in view.answer
    assert view.citation_url is None
