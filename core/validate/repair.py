"""Deterministic repairs (max one round)."""

from __future__ import annotations

import re

from core.validate.context import ValidationContext
from core.validate.models import CheckResult
from core.validate.sentences import truncate_to_sentences
from core.validate.validators import format_footer, _max_effective_date

_SOURCE_LINE = re.compile(r"^\s*Source:\s*.+$", re.I | re.M)
_URL_RE = re.compile(r"https?://[^\s)]+|groww\.in[^\s)]+", re.I)


def apply_repairs(ctx: ValidationContext, failed: list[CheckResult]) -> ValidationContext:
    reasons = {f.reason for f in failed if not f.passed}
    body = ctx.answer_body
    footer = ctx.footer

    if "too_many_sentences" in reasons:
        body = truncate_to_sentences(body, 3)

    if "url_in_answer_body" in reasons or "missing_citation_url" in reasons:
        body = _SOURCE_LINE.sub("", body).strip()
        body = _URL_RE.sub("", body).strip()

    if any(r in reasons for r in ("missing_footer", "relative_footer", "footer_date_mismatch")):
        footer = format_footer(_max_effective_date(ctx))

    if "stale_source" in reasons:
        age = sla = None
        for item in failed:
            if item.reason == "stale_source" and item.details:
                age = item.details.get("age_days")
                sla = item.details.get("sla_days")
                break
        base = format_footer(_max_effective_date(ctx))
        if age is not None and sla is not None:
            footer = (
                f"{base} — source may be outdated "
                f"({age}d old; freshness SLA {sla}d)."
            )
        else:
            footer = f"{base} — source may be outdated versus freshness SLA."

    return ValidationContext(
        query_id=ctx.query_id,
        route=ctx.route,
        answer_body=body,
        citation_url=ctx.citation_url,
        citation_label=ctx.citation_label,
        source_id=ctx.source_id,
        chunk_id=ctx.chunk_id,
        footer=footer,
        confidence=ctx.confidence,
        supporting_texts=list(ctx.supporting_texts),
        effective_dates=list(ctx.effective_dates),
        fact_key=ctx.fact_key,
        scheme_name=ctx.scheme_name,
        skip_groundedness=ctx.skip_groundedness,
        timings_ms=dict(ctx.timings_ms),
    )
