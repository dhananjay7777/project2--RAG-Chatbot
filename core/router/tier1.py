"""Deterministic Tier-1 intent classification."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from core.retrieval.query_inference import infer_fact_tags, infer_scheme
from schemas.answer import AnswerRoute


@dataclass(frozen=True)
class Tier1Match:
    intent: str
    route: AnswerRoute
    confidence: float
    reason: str


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text.strip().lower())


_INJECTION = re.compile(
    r"(ignore\s+(all\s+)?(prior|previous|above)\s+rules?"
    r"|ignore\s+instructions"
    r"|disregard\s+(previous|prior)"
    r"|you\s+are\s+now"
    r"|pretend\s+you\s+are"
    r"|jailbreak"
    r"|bypass\s+(safety|rules))",
    re.I,
)

_PERFORMANCE = re.compile(
    r"(\breturns?\b"
    r"|\bperformance\b"
    r"|\bannuali[sz]ed\b"
    r"|\bcagr\b"
    r"|\bnav\s+history\b"
    r"|\bchart\b"
    r"|\bcalculate\s+my\s+sip"
    r"|\bsip\s+returns?\b"
    r"|\bgrew\s+in\s+(one|two|three|four|five|\d+)\s+years?\b"
    r"|\blast\s+year'?s?\s+return)",
    re.I,
)

_SPECULATIVE = re.compile(
    r"(\bwill\s+.+\s+(grow|double|outperform)\b"
    r"|\bpredict\b"
    r"|\bforecast\b"
    r"|\bnext\s+(year|month)\b"
    r"|\bshould\s+i\s+expect\b"
    r"|\bwhat\s+returns?\s+should\s+i\s+expect\b"
    r"|\bgoing\s+to\s+outperform\b)",
    re.I,
)

_RANKING = re.compile(
    r"(\bwhich\s+of\s+(these|the)\s+(five\s+)?funds?\s+is\s+(better|best|safest)\b"
    r"|\bwhich\s+fund\s+is\s+(the\s+)?(best|better|safest)\b"
    r"|\brank\s+(these|the)\s+funds?\b"
    r"|\bvs\.?\b|\bversus\b"
    r"|\bbetter\s+than\b"
    r"|\bwhich\s+should\s+i\s+pick\b"
    r"|\bcompare\s+.+\s+and\s+.+\s+for\s+invest)",
    re.I,
)

_ADVISORY = re.compile(
    r"(\bshould\s+i\s+invest\b"
    r"|\bgood\s+investment\b"
    r"|\bwould\s+you\s+recommend\b"
    r"|\bcan\s+you\s+advise\b"
    r"|\bis\s+it\s+wise\s+to\b"
    r"|\bhypothetically\b.*\badvis"
    r"|\bif\s+you\s+were\s+my\s+advis"
    r"|\blena\s+chahiye\b"
    r"|\bkhareedna\s+chahiye\b"
    r"|\b(?:^|\s)recommend(?:\s|$|\b)"
    r"|\b(?:^|\s)advise(?:\s|$|\b)"
    r"|\b(?:^|\s)suggest(?:\s|$|\b)"
    r"|\bgo\s+for\s+this\s+fund\b"
    r"|\bopt\s+for\s+this\s+fund\b"
    r"|\bworth\s+investing\b"
    r"|\bmust\s+buy\b)",
    re.I,
)

_OUT_OF_SCOPE = re.compile(
    r"(\bweather\b"
    r"|\belss\s+lock[- ]?in\b"
    r"|\bcapital\s+gains\s+statement\b"
    r"|\bdownload\s+(my\s+)?(account\s+)?statements?\b"
    r"|\bhdfc\s+flexi\s+cap\b"
    r"|\bsharpe\s+ratio\b"
    r"|\bsortino\b"
    r"|\binformation\s+ratio\b"
    r"|\btracking\s+error\b"
    r"|\balpha\b|\bbeta\b"
    r"|\bcricket\b"
    r"|\bfootball\b"
    # Commodities / markets / crypto — not in the five Groww scheme pages
    r"|\b(gold|silver|crude|oil|copper|platinum)\s+price\b"
    r"|\bprice\s+of\s+(gold|silver|crude|oil|copper|platinum|bitcoin|ethereum|usd|dollar)\b"
    r"|\b(gold|silver)\s+(rate|spot|quote)\b"
    r"|\bcommodity\b|\bcommodities\b"
    r"|\bcrypto(currency)?\b|\bbitcoin\b|\bethereum\b"
    r"|\bstock\s+price\b|\bshare\s+price\b"
    r"|\bsensex\b|\bnifty\s*(?!.*(fund|direct))\d*\b)",
    re.I,
)

_AMBIGUOUS = re.compile(
    r"^(what\s+about\s+the\s+load\??|expense\s+ratio\??|minimum\s+sip\s+please\??"
    r"|what\s+is\s+the\s+risk\??|tell\s+me\s+about\s+the\s+fund\.?)$",
    re.I,
)

_UNKNOWN_FUND = re.compile(
    r"\bhdfc\b|\bicici\b|\bsbi\b|\baxis\b|\buti\b|\baditya\s+birla\b",
    re.I,
)


def _route_for_intent(intent: str) -> AnswerRoute:
    from policy.taxonomy import intent_classes

    route_name = intent_classes()[intent]["route"]
    return AnswerRoute(route_name)


def classify_tier1(query: str) -> Optional[Tier1Match]:
    raw = query.strip()
    if not raw:
        return Tier1Match("AMBIGUOUS", AnswerRoute.CLARIFY, 1.0, "empty_query")

    q = _normalize(raw)
    inference = infer_scheme(raw)

    if _INJECTION.search(raw):
        return Tier1Match("ADVISORY", AnswerRoute.REFUSAL, 1.0, "prompt_injection")

    if _PERFORMANCE.search(raw):
        return Tier1Match("PERFORMANCE_RETURNS", AnswerRoute.PERFORMANCE_REDIRECT, 1.0, "performance")

    if _SPECULATIVE.search(raw):
        return Tier1Match("SPECULATIVE_FORECAST", AnswerRoute.REFUSAL, 1.0, "speculative")

    if _RANKING.search(raw):
        return Tier1Match("RANKING_COMPARATIVE", AnswerRoute.REFUSAL, 1.0, "ranking")

    if _ADVISORY.search(raw):
        return Tier1Match("ADVISORY", AnswerRoute.REFUSAL, 1.0, "advisory")

    if _OUT_OF_SCOPE.search(raw) or _UNKNOWN_FUND.search(raw):
        return Tier1Match("OUT_OF_SCOPE", AnswerRoute.NO_ANSWER, 1.0, "out_of_scope")

    if _AMBIGUOUS.match(q) or (
        inference.source_id is None
        and inference.ambiguous_multi_asset
    ):
        return Tier1Match("AMBIGUOUS", AnswerRoute.CLARIFY, 0.95, "ambiguous")

    fact_tags = infer_fact_tags(raw)
    has_fact_cue = bool(fact_tags) or re.search(
        r"\b(expense|exit\s+load|minimum|sip|aum|nav|benchmark|fund\s+manager|risk)\b",
        q,
    )

    # "nav of nippon" / "expense ratio of tata" — brand ≠ scheme. Do not bind to
    # the single corpus fund for that AMC (houses have hundreds of schemes).
    if has_fact_cue and inference.brand_only:
        return Tier1Match("AMBIGUOUS", AnswerRoute.CLARIFY, 0.95, "brand_only_scheme")

    if inference.source_id and inference.scheme_confident and has_fact_cue:
        intent = "FACTUAL_PROCESS" if "exit_load" in fact_tags else "FACTUAL_ATTRIBUTE"
        return Tier1Match(intent, AnswerRoute.FACTUAL, 0.95, "factual_with_scheme")

    if has_fact_cue and not inference.ambiguous_multi_asset:
        # e.g. confirming exit load without naming scheme — still factual path
        if re.search(r"\b(confirm|just\s+confirming)\b", q) or "exit load" in q:
            return Tier1Match("FACTUAL_ATTRIBUTE", AnswerRoute.FACTUAL, 0.85, "factual_cue")
        if inference.source_id is None and len(q.split()) <= 6:
            return Tier1Match("AMBIGUOUS", AnswerRoute.CLARIFY, 0.9, "fact_without_scheme")

    if inference.source_id and re.search(r"\btell\s+me\s+about\b", q):
        return Tier1Match("AMBIGUOUS", AnswerRoute.CLARIFY, 0.85, "vague_about_fund")

    return None
