"""Pure presentation logic for the Phase 7 UI (no Streamlit imports)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core.settings import load_settings
from ingest.processing.pii import load_pii_patterns
from policy.loader import is_allowlisted, load_registry
from schemas.answer import AnswerEnvelope, AnswerRoute

DISCLAIMER = "Facts-only. No investment advice."

WELCOME_TITLE = "Mutual Fund FAQ Assistant"
WELCOME_BODY = (
    "Ask a factual question about one of the five Groww Direct Growth schemes below — "
    "expense ratio, exit load, minimum SIP, AUM, NAV, benchmark, or fund manager. "
    "Factual answers include a source link and the date it was captured."
)


def corpus_scheme_names() -> list[str]:
    """Canonical scheme names from the locked five-URL registry."""

    names: list[str] = []
    for row in load_registry().get("sources") or []:
        scheme_names = row.get("scheme_names") or []
        if scheme_names:
            names.append(str(scheme_names[0]))
    return names

FALLBACK_EXAMPLES = [
    "What is the exit load on Nippon India Value Fund Direct Growth?",
    "What is the minimum SIP for Samco Mid Cap Fund Direct Growth?",
    "Should I invest in Tata Multi Asset Allocation Fund?",
]


@dataclass(frozen=True)
class RouteStyle:
    badge: str
    tone: str  # factual | refusal | redirect | empty | clarify
    accent: str
    note: str


ROUTE_STYLES: dict[AnswerRoute, RouteStyle] = {
    AnswerRoute.FACTUAL: RouteStyle(
        badge="Answer",
        tone="factual",
        accent="#0f766e",
        note="",
    ),
    AnswerRoute.REFUSAL: RouteStyle(
        badge="Out of bounds",
        tone="refusal",
        accent="#b45309",
        note="This assistant states facts and never gives investment advice.",
    ),
    AnswerRoute.PERFORMANCE_REDIRECT: RouteStyle(
        badge="Performance redirect",
        tone="redirect",
        accent="#0369a1",
        note="Returns and performance figures are only available on the source page.",
    ),
    AnswerRoute.NO_ANSWER: RouteStyle(
        badge="No answer found",
        tone="empty",
        accent="#64748b",
        note="Nothing in the five source pages verifies an answer to that question.",
    ),
    AnswerRoute.CLARIFY: RouteStyle(
        badge="Needs detail",
        tone="clarify",
        accent="#0e7490",
        note="Name one scheme so the lookup stays unambiguous.",
    ),
}


@dataclass
class InputCheck:
    ok: bool
    char_count: int
    max_chars: int
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class AnswerView:
    route: AnswerRoute
    badge: str
    tone: str
    accent: str
    note: str
    answer: str
    footer: str
    citation_url: str | None
    citation_label: str
    validator_passed: bool


def ui_settings() -> dict[str, Any]:
    return dict(load_settings().get("ui") or {})


def max_input_chars() -> int:
    return int(ui_settings().get("max_input_chars", 500))


def example_questions() -> list[str]:
    questions = ui_settings().get("example_questions") or FALLBACK_EXAMPLES
    return [str(q) for q in questions][:3]


def _identity_patterns() -> list[tuple[str, re.Pattern[str]]]:
    specs = load_pii_patterns().get("patterns") or {}
    out: list[tuple[str, re.Pattern[str]]] = []
    for name in ("pan", "aadhaar"):
        spec = specs.get(name)
        if not spec:
            continue
        flags = re.IGNORECASE if "IGNORECASE" in (spec.get("flags") or []) else 0
        out.append((name, re.compile(spec["regex"], flags)))
    return out


def detect_pii_warnings(text: str) -> list[str]:
    """Client-side nudge before submit; the router redacts and refuses anyway."""

    warnings: list[str] = []
    for name, pattern in _identity_patterns():
        if pattern.search(text):
            label = "PAN" if name == "pan" else "Aadhaar"
            warnings.append(
                f"That looks like a {label} number. Remove it — this assistant never needs personal identifiers."
            )
    return warnings


def check_input(text: str, *, max_chars: int | None = None) -> InputCheck:
    limit = max_chars or max_input_chars()
    stripped = (text or "").strip()
    count = len(text or "")

    if not stripped:
        return InputCheck(ok=False, char_count=count, max_chars=limit, error="Type a question first.")
    if count > limit:
        return InputCheck(
            ok=False,
            char_count=count,
            max_chars=limit,
            error=f"Questions are capped at {limit} characters. Shorten it by {count - limit}.",
        )
    return InputCheck(
        ok=True,
        char_count=count,
        max_chars=limit,
        warnings=detect_pii_warnings(stripped),
    )


def envelope_to_view(envelope: AnswerEnvelope) -> AnswerView:
    style = ROUTE_STYLES.get(envelope.route, ROUTE_STYLES[AnswerRoute.NO_ANSWER])
    url = str(envelope.citation.url)
    # The UI renders only what the envelope carries, and never a rewritten link.
    safe_url = url if is_allowlisted(url) else None
    # Show a source link only when a factual answer was produced from retrieved
    # / Fact Card data — not on refusals, redirects, clarify, or no-answer.
    show_link = envelope.route == AnswerRoute.FACTUAL and safe_url is not None
    return AnswerView(
        route=envelope.route,
        badge=style.badge,
        tone=style.tone,
        accent=style.accent,
        note=style.note,
        answer=envelope.answer.strip(),
        footer=envelope.footer if show_link else "",
        citation_url=safe_url if show_link else None,
        citation_label=envelope.citation.label if show_link else "",
        validator_passed=envelope.validator_report.passed,
    )


def error_view(message: str) -> AnswerView:
    style = ROUTE_STYLES[AnswerRoute.NO_ANSWER]
    return AnswerView(
        route=AnswerRoute.NO_ANSWER,
        badge="Something went wrong",
        tone="empty",
        accent=style.accent,
        note="",
        answer=message,
        footer="",
        citation_url=None,
        citation_label="",
        validator_passed=False,
    )
