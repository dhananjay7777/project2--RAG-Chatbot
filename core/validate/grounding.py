"""Token extraction for groundedness checks."""

from __future__ import annotations

import re
import unicodedata

from policy.loader import load_registry


def normalize_for_match(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("₹", "INR ")
    text = re.sub(r"\s+", " ", text.lower())
    return text


def extract_grounding_tokens(answer: str) -> list[str]:
    tokens: list[str] = []
    # Require fractional digits when a decimal point is present so a sentence
    # period after "₹100." is not treated as the number "100.".
    for match in re.finditer(r"\d[\d,]*(?:\.\d+)?%?", answer):
        tokens.append(match.group(0))
    for match in re.finditer(
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b",
        answer,
        re.I,
    ):
        tokens.append(match.group(0))
    for match in re.finditer(r"\b\d{4}-\d{2}-\d{2}\b", answer):
        tokens.append(match.group(0))

    registry = load_registry()
    answer_norm = normalize_for_match(answer)
    for row in registry["sources"]:
        for name in row.get("scheme_names") or []:
            if normalize_for_match(str(name)) in answer_norm:
                tokens.append(str(name))
        amc = row.get("amc")
        if amc and normalize_for_match(str(amc)) in answer_norm:
            tokens.append(str(amc))
    return tokens


def grounded_in_context(token: str, contexts: list[str]) -> bool:
    if not contexts:
        return False
    blob = normalize_for_match("\n".join(contexts))
    needle = normalize_for_match(token)
    if needle in blob:
        return True
    # Percent / number loosening: strip commas
    needle_compact = needle.replace(",", "")
    blob_compact = blob.replace(",", "")
    return needle_compact in blob_compact
