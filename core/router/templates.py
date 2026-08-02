"""Fill policy templates for refusal / redirect / clarify."""

from __future__ import annotations

import re

from policy.taxonomy import intent_classes


def render_template(intent: str, *, citation_url: str, citation_label: str) -> str:
    spec = intent_classes()[intent]
    template = spec.get("template")
    if not template:
        raise ValueError(f"No template for intent {intent}")
    text = template.replace("{{citation_url}}", citation_url)
    text = text.replace("{{citation_label}}", citation_label)
    return text.strip()


def sentence_count(text: str) -> int:
    parts = re.split(r"[.!?]+", text)
    return len([p for p in parts if p.strip()])
