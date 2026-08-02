"""Normalize Groww text for indexing (preserve display forms in Fact Cards)."""

from __future__ import annotations

import re

_ABBREV = {
    "TER": "Total Expense Ratio",
    "SIP": "Systematic Investment Plan",
    "NAV": "Net Asset Value",
    "AUM": "Assets Under Management",
    "ELSS": "Equity Linked Savings Scheme",
}


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_currency_and_percent(text: str) -> str:
    text = re.sub(r"\bRs\.?\s*", "INR ", text)
    text = text.replace("₹", "INR ")
    text = re.sub(r"(\d)\s+%", r"\1%", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def synonym_field(text: str) -> str:
    """Extra BM25 tokens expanded from known abbreviations present in text."""

    extras: list[str] = []
    upper = text.upper()
    for abbr, expansion in _ABBREV.items():
        if re.search(rf"\b{abbr}\b", upper):
            extras.append(expansion)
    return " ".join(extras)


def normalize_for_index(text: str) -> str:
    base = normalize_whitespace(text)
    base = normalize_currency_and_percent(base)
    syn = synonym_field(base)
    if syn:
        return f"{base}\n{syn}"
    return base
