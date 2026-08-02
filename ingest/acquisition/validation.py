"""Sparse/challenge detection and NAV effective-date extraction."""

from __future__ import annotations

import html
import re
from datetime import date, datetime, timezone

from ingest.acquisition.models import FetchPayload

MIN_CONTENT_BYTES = 1_000
_CHALLENGE_MARKERS = (
    "access denied",
    "verify you are human",
    "checking your browser",
    "captcha",
    "cf-chl-",
)
_HTML_H1 = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_MARKDOWN_H1 = re.compile(r"(?m)^\s*#\s+(.+?)\s*$")
_TAG = re.compile(r"<[^>]+>")
_NAV_DATE = re.compile(
    r"\bNAV\s*:\s*(\d{1,2})\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"(?:[a-z]*)\s+[’']?(\d{2}|\d{4})\b",
    re.IGNORECASE,
)
_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


class ContentValidationError(ValueError):
    """Fetched bytes are not a usable snapshot of the expected scheme page."""


def _decode(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


def _plain_text(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", raw))).strip()


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def extract_heading(content: bytes) -> str | None:
    raw = _decode(content)
    html_match = _HTML_H1.search(raw)
    if html_match:
        return _plain_text(html_match.group(1))
    markdown_match = _MARKDOWN_H1.search(raw)
    if markdown_match:
        return markdown_match.group(1).strip()
    return None


def extract_effective_date(
    content: bytes,
    *,
    fetched_at: datetime | None = None,
) -> tuple[date, bool]:
    """Return effective date and whether it came from the on-page NAV label."""

    text = _plain_text(_decode(content))
    match = _NAV_DATE.search(text)
    if match:
        day = int(match.group(1))
        month = _MONTHS[match.group(2)[:3].lower()]
        raw_year = match.group(3)
        year = int(raw_year)
        if len(raw_year) == 2:
            year += 2000
        try:
            return date(year, month, day), True
        except ValueError as exc:
            raise ContentValidationError(
                f"Invalid NAV date found on page: {match.group(0)!r}"
            ) from exc

    fetched_at = fetched_at or datetime.now(timezone.utc)
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return fetched_at.astimezone(timezone.utc).date(), False


def validate_payload(
    payload: FetchPayload,
    expected_scheme_name: str,
    *,
    fetched_at: datetime | None = None,
) -> tuple[date, bool]:
    """Validate minimum size, bot-wall markers, H1, and return effective date."""

    if len(payload.content) < MIN_CONTENT_BYTES:
        raise ContentValidationError(
            f"Sparse response ({len(payload.content)} bytes); expected at least "
            f"{MIN_CONTENT_BYTES}"
        )

    lowered = _decode(payload.content).lower()
    marker = next((value for value in _CHALLENGE_MARKERS if value in lowered), None)
    if marker:
        raise ContentValidationError(
            f"Challenge/bot-wall response detected ({marker!r})"
        )

    heading = extract_heading(payload.content)
    if not heading:
        raise ContentValidationError("Expected scheme H1 is missing")
    expected = _normalized(expected_scheme_name)
    actual = _normalized(heading)
    if expected not in actual and actual not in expected:
        raise ContentValidationError(
            f"Scheme H1 mismatch: expected {expected_scheme_name!r}, got {heading!r}"
        )

    return extract_effective_date(payload.content, fetched_at=fetched_at)
