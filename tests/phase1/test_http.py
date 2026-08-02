"""P1-01, P1-02, P1-07: strict HTTP fetcher behaviour."""

from __future__ import annotations

import pytest

from ingest.acquisition.http import (
    AllowlistViolation,
    AllowAllRobotsPolicy,
    FetchFailedError,
    RateLimiter,
    StrictHttpFetcher,
)
from policy.loader import load_allowlist
from tests.phase1.helpers import FakeResponse, QueueSession, html_page

ALLOWLIST = load_allowlist()
NIPPON = ALLOWLIST[0]
SIXTH = "https://groww.in/mutual-funds/hdfc-flexi-cap-fund-direct-growth"


def test_refuses_sixth_url_before_http():
    session = QueueSession([])
    fetcher = StrictHttpFetcher(
        session=session,
        robots=AllowAllRobotsPolicy(),
        limiter=RateLimiter(min_interval_seconds=0),
        allowlist=ALLOWLIST,
    )
    with pytest.raises(AllowlistViolation):
        fetcher.fetch(SIXTH)
    assert session.calls == []


def test_retries_then_succeeds():
    body = html_page("Nippon India Value Fund Direct Growth")
    session = QueueSession(
        [
            FakeResponse(503, content=b"error"),
            FakeResponse(200, content=body),
        ]
    )
    sleeps: list[float] = []

    fetcher = StrictHttpFetcher(
        session=session,
        robots=AllowAllRobotsPolicy(),
        limiter=RateLimiter(min_interval_seconds=0),
        retries=2,
        backoff_seconds=0.01,
        sleeper=sleeps.append,
        allowlist=ALLOWLIST,
    )
    payload = fetcher.fetch(NIPPON)
    assert payload.mode == "http"
    assert len(payload.content) >= 1000
    assert len(sleeps) == 1


def test_terminal_http_failure_after_retries():
    session = QueueSession(
        [FakeResponse(403, content=b"blocked")] * 4
    )
    fetcher = StrictHttpFetcher(
        session=session,
        robots=AllowAllRobotsPolicy(),
        limiter=RateLimiter(min_interval_seconds=0),
        retries=2,
        backoff_seconds=0,
        sleeper=lambda _: None,
        allowlist=ALLOWLIST,
    )
    with pytest.raises(FetchFailedError):
        fetcher.fetch(NIPPON)


def test_redirect_to_non_allowlisted_url_is_rejected():
    session = QueueSession(
        [
            FakeResponse(
                301,
                headers={"Location": SIXTH},
                content=b"",
            )
        ]
    )
    fetcher = StrictHttpFetcher(
        session=session,
        robots=AllowAllRobotsPolicy(),
        limiter=RateLimiter(min_interval_seconds=0),
        allowlist=ALLOWLIST,
    )
    with pytest.raises(AllowlistViolation, match="Redirect changed"):
        fetcher.fetch(NIPPON)


def test_same_url_redirect_is_followed():
    body = html_page("Nippon India Value Fund Direct Growth")
    session = QueueSession(
        [
            FakeResponse(
                302,
                headers={"Location": NIPPON},
                content=b"",
            ),
            FakeResponse(200, content=body),
        ]
    )
    fetcher = StrictHttpFetcher(
        session=session,
        robots=AllowAllRobotsPolicy(),
        limiter=RateLimiter(min_interval_seconds=0),
        allowlist=ALLOWLIST,
    )
    payload = fetcher.fetch(NIPPON)
    assert payload.final_url == NIPPON
