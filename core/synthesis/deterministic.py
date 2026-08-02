"""Deterministic Fact Card phrasing (no LLM)."""

from __future__ import annotations

import re

from schemas.fact_card import FactCard

FACT_LABELS: dict[str, str] = {
    "expense_ratio": "expense ratio",
    "exit_load": "exit load",
    "min_sip": "minimum SIP",
    "min_lumpsum": "minimum lumpsum investment",
    "risk_rating": "risk rating",
    "category": "category",
    "aum": "fund size (AUM)",
    "nav": "NAV",
    "benchmark": "benchmark",
    "fund_manager": "fund manager",
    "launch_date": "launch date",
    "investment_objective": "investment objective",
    "stamp_duty": "stamp duty",
    "tax_implication_text": "tax implication text shown on Groww",
    "standard_deviation": "standard deviation",
    "beta": "beta",
    "sharpe_ratio": "Sharpe ratio",
    "sortino_ratio": "Sortino ratio",
    "alpha": "alpha",
    "information_ratio": "information ratio",
    "tracking_error": "tracking error",
}


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def cap_sentences(text: str, max_sentences: int = 3) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return text.strip()
    return " ".join(sentences[:max_sentences])


def count_sentences(text: str) -> int:
    return len(_split_sentences(text)) or (1 if text.strip() else 0)


def format_fact_answer(fact: FactCard, *, max_sentences: int = 3) -> str:
    if not fact.value_text:
        raise ValueError("Fact card has no value_text")
    label = FACT_LABELS.get(fact.fact_key, fact.fact_key.replace("_", " "))
    value = fact.value_text.strip()

    if fact.fact_key == "fund_manager":
        managers = [part.strip() for part in value.split(",") if part.strip()]
        if len(managers) > 1:
            listed = ", ".join(managers[:-1]) + f", and {managers[-1]}"
            return f"The fund managers of {fact.scheme_name} are {listed}."
        return f"The fund manager of {fact.scheme_name} is {managers[0]}."

    long_form_keys = {
        "exit_load",
        "investment_objective",
        "tax_implication_text",
    }
    if fact.fact_key in long_form_keys:
        body = cap_sentences(value.replace("\n\n", " ").replace("\n", " "), max_sentences)
        return f"For {fact.scheme_name}, the {label} is: {body}"
    body = cap_sentences(value, max_sentences)
    return f"The {label} of {fact.scheme_name} is {body}."
