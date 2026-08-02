"""Individual validators (Phase 6)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from urllib.parse import urlparse

import yaml

from core.validate.context import ValidationContext
from core.validate.grounding import extract_grounding_tokens, grounded_in_context
from core.validate.models import CheckResult, FailAction
from core.validate.sentences import sentence_count
from core.settings import load_settings
from ingest.processing.pii import load_pii_patterns
from policy import POLICY_DIR
from policy.loader import canonicalize_url, is_allowlisted
from schemas.answer import AnswerRoute


def _nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def check_sentence_count(ctx: ValidationContext) -> CheckResult:
    count = sentence_count(ctx.answer_body)
    if count <= 3:
        return CheckResult(validator="SentenceCount", passed=True, details={"count": count})
    return CheckResult(
        validator="SentenceCount",
        passed=False,
        action=FailAction.REPAIR,
        reason="too_many_sentences",
        details={"count": count},
    )


_URL_RE = re.compile(r"https?://[^\s)]+|groww\.in[^\s)]+", re.I)


def check_citation_cardinality(ctx: ValidationContext) -> CheckResult:
    body_urls = _URL_RE.findall(ctx.answer_body)
    if body_urls:
        return CheckResult(
            validator="CitationCardinality",
            passed=False,
            action=FailAction.REPAIR,
            reason="url_in_answer_body",
            details={"urls": body_urls},
        )
    if not ctx.citation_url:
        return CheckResult(
            validator="CitationCardinality",
            passed=False,
            action=FailAction.REPAIR,
            reason="missing_citation_url",
        )
    return CheckResult(validator="CitationCardinality", passed=True)


def check_citation_allowlist(ctx: ValidationContext) -> CheckResult:
    try:
        canonical = canonicalize_url(ctx.citation_url)
    except Exception as exc:
        return CheckResult(
            validator="CitationAllowlist",
            passed=False,
            action=FailAction.HARD_FAIL,
            reason="invalid_citation_url",
            details={"error": str(exc)},
        )
    if not is_allowlisted(canonical):
        return CheckResult(
            validator="CitationAllowlist",
            passed=False,
            action=FailAction.HARD_FAIL,
            reason="citation_not_allowlisted",
            details={"url": canonical},
        )
    host = urlparse(canonical).netloc
    if "amfiindia.com" in host or "sebi.gov.in" in host:
        return CheckResult(
            validator="CitationAllowlist",
            passed=False,
            action=FailAction.HARD_FAIL,
            reason="forbidden_publisher",
        )
    return CheckResult(validator="CitationAllowlist", passed=True, details={"url": canonical})


def check_groundedness(ctx: ValidationContext) -> CheckResult:
    if ctx.skip_groundedness or ctx.route != AnswerRoute.FACTUAL:
        return CheckResult(validator="Groundedness", passed=True, details={"skipped": True})
    if not ctx.supporting_texts:
        return CheckResult(
            validator="Groundedness",
            passed=False,
            action=FailAction.HARD_FAIL,
            reason="no_supporting_context",
        )
    tokens = extract_grounding_tokens(ctx.answer_body)
    missing = [t for t in tokens if not grounded_in_context(t, ctx.supporting_texts)]
    if missing:
        return CheckResult(
            validator="Groundedness",
            passed=False,
            action=FailAction.HARD_FAIL,
            reason="ungrounded_tokens",
            details={"missing": missing},
        )
    return CheckResult(validator="Groundedness", passed=True, details={"tokens": tokens})


def _load_lexicon() -> tuple[list[str], list[re.Pattern[str]]]:
    data = yaml.safe_load((POLICY_DIR / "prohibited_lexicon.yaml").read_text(encoding="utf-8"))
    terms = [str(t).lower() for t in data.get("terms") or []]
    patterns = [
        re.compile(p, re.I) for p in (data.get("patterns") or [])
    ]
    return terms, patterns


def check_advice_lexicon(ctx: ValidationContext) -> CheckResult:
    if ctx.route != AnswerRoute.FACTUAL:
        return CheckResult(validator="AdviceLexicon", passed=True, details={"skipped": True})
    text = _nfkc(ctx.answer_body.lower())
    if "not investment advice" in text or "no investment advice" in text:
        return CheckResult(validator="AdviceLexicon", passed=True)
    terms, patterns = _load_lexicon()
    for term in terms:
        if re.search(rf"\b{re.escape(term)}\b", text):
            return CheckResult(
                validator="AdviceLexicon",
                passed=False,
                action=FailAction.HARD_FAIL,
                reason="prohibited_term",
                details={"term": term},
            )
    for pat in patterns:
        if pat.search(text):
            return CheckResult(
                validator="AdviceLexicon",
                passed=False,
                action=FailAction.HARD_FAIL,
                reason="prohibited_pattern",
                details={"pattern": pat.pattern},
            )
    return CheckResult(validator="AdviceLexicon", passed=True)


def check_pii_egress(ctx: ValidationContext) -> CheckResult:
    patterns = load_pii_patterns().get("patterns") or {}
    blob = ctx.answer_body + " " + ctx.footer
    for name, spec in patterns.items():
        flags = re.IGNORECASE if "IGNORECASE" in (spec.get("flags") or []) else 0
        regex = re.compile(spec["regex"], flags)
        ctx_keys = [k.lower() for k in (spec.get("requires_context_keywords") or [])]

        for match in regex.finditer(blob):
            if ctx_keys:
                window = blob[max(0, match.start() - 40) : match.end() + 40].lower()
                if not any(k in window for k in ctx_keys):
                    continue
            return CheckResult(
                validator="PIIEgress",
                passed=False,
                action=FailAction.HARD_FAIL,
                reason="pii_in_output",
                details={"kind": name},
            )
    return CheckResult(validator="PIIEgress", passed=True)


def _max_effective_date(ctx: ValidationContext) -> date | None:
    if not ctx.effective_dates:
        return None
    return max(ctx.effective_dates)


def reference_today() -> date:
    """Calendar 'today' for freshness checks.

    Set ``MF_AS_OF_DATE=YYYY-MM-DD`` during Phase 8 eval so SLA checks are
    reproducible against a frozen corpus capture date (no live Groww fetch).
    """

    import os

    raw = (os.getenv("MF_AS_OF_DATE") or "").strip()
    if raw:
        return date.fromisoformat(raw)
    return date.today()


def format_footer(max_date: date | None) -> str:
    if max_date is None:
        max_date = reference_today()
    formatted = max_date.strftime("%d %b %Y")
    return f"Last updated from sources: {formatted}"


def check_footer_integrity(ctx: ValidationContext) -> CheckResult:
    expected = format_footer(_max_effective_date(ctx))
    if not ctx.footer.startswith("Last updated from sources:"):
        return CheckResult(
            validator="FooterIntegrity",
            passed=False,
            action=FailAction.REPAIR,
            reason="missing_footer",
            details={"expected": expected},
        )
    if "yesterday" in ctx.footer.lower() or "today" in ctx.footer.lower():
        return CheckResult(
            validator="FooterIntegrity",
            passed=False,
            action=FailAction.REPAIR,
            reason="relative_footer",
            details={"expected": expected},
        )
    # Allow an optional staleness annotation after the canonical footer prefix.
    if ctx.footer.strip() != expected.strip() and not ctx.footer.strip().startswith(
        expected.strip()
    ):
        return CheckResult(
            validator="FooterIntegrity",
            passed=False,
            action=FailAction.REPAIR,
            reason="footer_date_mismatch",
            details={"expected": expected, "actual": ctx.footer},
        )
    return CheckResult(validator="FooterIntegrity", passed=True)


def check_staleness(ctx: ValidationContext) -> CheckResult:
    if ctx.route != AnswerRoute.FACTUAL or not ctx.fact_key:
        return CheckResult(validator="Staleness", passed=True, details={"skipped": True})
    sla_map = load_settings().get("freshness_sla_days") or {}
    sla_days = int(sla_map.get(ctx.fact_key, 90))
    max_d = _max_effective_date(ctx)
    if max_d is None:
        return CheckResult(validator="Staleness", passed=True, details={"skipped": True})
    age = (reference_today() - max_d).days
    if age > sla_days:
        # Already annotated by the repair pass — do not fail again (avoids canned loop).
        if "outdated" in ctx.footer.lower() or "freshness sla" in ctx.footer.lower():
            return CheckResult(
                validator="Staleness",
                passed=True,
                details={"age_days": age, "sla_days": sla_days, "annotated": True},
            )
        # Annotate rather than hard-fail: Architecture allows footer annotation for
        # SLA breach; wiping a grounded NAV/TER into a canned "no information"
        # refusal is misleading when the Fact Card exists.
        return CheckResult(
            validator="Staleness",
            passed=False,
            action=FailAction.REPAIR,
            reason="stale_source",
            details={"age_days": age, "sla_days": sla_days},
        )
    return CheckResult(validator="Staleness", passed=True, details={"age_days": age})


def check_performance_no_digits(ctx: ValidationContext) -> CheckResult:
    if ctx.route != "PERFORMANCE_REDIRECT":
        return CheckResult(validator="PerformanceNumeralFree", passed=True, details={"skipped": True})
    if re.search(r"\d", ctx.answer_body):
        return CheckResult(
            validator="PerformanceNumeralFree",
            passed=False,
            action=FailAction.HARD_FAIL,
            reason="digits_in_performance_redirect",
        )
    return CheckResult(validator="PerformanceNumeralFree", passed=True)


VALIDATORS = [
    check_sentence_count,
    check_citation_cardinality,
    check_citation_allowlist,
    check_groundedness,
    check_advice_lexicon,
    check_pii_egress,
    check_footer_integrity,
    check_staleness,
    check_performance_no_digits,
]
