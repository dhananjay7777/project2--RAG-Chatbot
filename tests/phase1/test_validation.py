"""P1-03, P1-08, P1-09: source-page validation and dates."""

from datetime import date, datetime, timezone

import pytest

from ingest.acquisition.models import FetchPayload
from ingest.acquisition.validation import (
    ContentValidationError,
    extract_effective_date,
    validate_payload,
)
from tests.phase1.helpers import html_page, markdown_page

SCHEME = "Nippon India Value Fund Direct Growth"


def payload(content: bytes, content_type: str = "text/html") -> FetchPayload:
    return FetchPayload(
        content=content,
        final_url=(
            "https://groww.in/mutual-funds/"
            "nippon-india-value-fund-direct-growth"
        ),
        mode="http",
        content_type=content_type,
    )


def test_extract_nav_date_from_html_ignores_http_metadata():
    effective, found = validate_payload(payload(html_page(SCHEME)), SCHEME)
    assert effective == date(2026, 7, 24)
    assert found is True


def test_extract_nav_date_from_markdown_snapshot():
    effective, found = validate_payload(
        payload(markdown_page(SCHEME), "text/markdown"),
        SCHEME,
    )
    assert effective == date(2026, 7, 24)
    assert found is True


def test_missing_nav_date_falls_back_to_utc_fetch_date():
    fetched_at = datetime(2026, 8, 3, 23, 30, tzinfo=timezone.utc)
    effective, found = extract_effective_date(
        html_page(SCHEME, nav_date=None),
        fetched_at=fetched_at,
    )
    assert effective == date(2026, 8, 3)
    assert found is False


def test_sparse_page_is_rejected():
    with pytest.raises(ContentValidationError, match="Sparse"):
        validate_payload(payload(b"<h1>Nippon India Value Fund Direct Growth</h1>"), SCHEME)


def test_missing_h1_is_rejected():
    content = ("<html><body>" + "<p>content</p>" * 200 + "</body></html>").encode()
    with pytest.raises(ContentValidationError, match="H1 is missing"):
        validate_payload(payload(content), SCHEME)


def test_wrong_scheme_h1_is_rejected():
    with pytest.raises(ContentValidationError, match="H1 mismatch"):
        validate_payload(
            payload(html_page("Tata Multi Asset Allocation Fund Direct Growth")),
            SCHEME,
        )


@pytest.mark.parametrize(
    "marker",
    ["Access Denied", "Verify you are human", "captcha", "cf-chl-token"],
)
def test_challenge_pages_are_rejected(marker):
    with pytest.raises(ContentValidationError, match="bot-wall"):
        validate_payload(payload(html_page(SCHEME, marker=marker)), SCHEME)
