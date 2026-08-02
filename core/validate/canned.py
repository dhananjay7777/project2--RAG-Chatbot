"""Safe canned responses on hard validator failure."""

from __future__ import annotations

from core.router.citation import fallback_citation
from core.router.templates import render_template
from core.validate.context import ValidationContext
from core.validate.validators import format_footer
from schemas.answer import AnswerRoute


def build_canned_context(ctx: ValidationContext, *, reason: str) -> ValidationContext:
    url, label, source_id = fallback_citation()
    try:
        body = render_template("OUT_OF_SCOPE", citation_url=url, citation_label=label)
    except ValueError:
        body = (
            "I could not verify that answer against the listed Groww scheme pages. "
            "Please ask about one factual detail for a named scheme."
        )
    body_lines = [ln for ln in body.splitlines() if not ln.strip().lower().startswith("source:")]
    clean_body = "\n".join(body_lines).strip()
    if "Source:" in clean_body:
        clean_body = clean_body.rsplit("Source:", 1)[0].strip()

    # Canned answers are not grounded in a cited fact date — clear source dates so
    # FooterIntegrity expects today's footer (format_footer(None)).
    return ValidationContext(
        query_id=ctx.query_id,
        route=AnswerRoute.NO_ANSWER,
        answer_body=clean_body,
        citation_url=url,
        citation_label=label,
        source_id=source_id,
        footer=format_footer(None),
        confidence=0.0,
        supporting_texts=[],
        effective_dates=[],
        skip_groundedness=True,
        timings_ms=dict(ctx.timings_ms),
    )
