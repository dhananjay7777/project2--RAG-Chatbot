"""Optional Playwright fallback for sparse JavaScript-rendered source pages."""

from __future__ import annotations

from ingest.acquisition.http import (
    AcquisitionError,
    AllowlistViolation,
    RobotsPolicy,
    USER_AGENT,
)
from ingest.acquisition.models import FetchPayload
from policy.loader import canonicalize_url, load_allowlist


class HeadlessUnavailableError(AcquisitionError):
    """Playwright is not installed or its browser is unavailable."""


class PlaywrightFetcher:
    """Render one allowlisted page and return the resulting HTML."""

    def __init__(
        self,
        *,
        robots: RobotsPolicy,
        timeout_ms: int = 45_000,
        allowlist: list[str] | None = None,
    ):
        self.robots = robots
        self.timeout_ms = timeout_ms
        self.allowlist = set(allowlist or load_allowlist())

    def fetch(self, url: str) -> FetchPayload:
        canonical = canonicalize_url(url)
        if canonical not in self.allowlist:
            raise AllowlistViolation(
                f"Refusing non-allowlisted source URL before browser launch: {url}"
            )
        self.robots.assert_allowed(canonical, USER_AGENT)

        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise HeadlessUnavailableError(
                "Playwright is not installed. Install requirements-headless.txt "
                "and run `playwright install chromium`."
            ) from exc

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(user_agent=USER_AGENT)
                response = page.goto(
                    canonical,
                    wait_until="networkidle",
                    timeout=self.timeout_ms,
                )
                final_url = canonicalize_url(page.url)
                if final_url != canonical or final_url not in self.allowlist:
                    browser.close()
                    raise AllowlistViolation(
                        f"Browser navigation changed frozen URL: {canonical} -> "
                        f"{page.url}"
                    )
                if response is not None and response.status >= 400:
                    status = response.status
                    browser.close()
                    raise AcquisitionError(
                        f"Headless fetch returned HTTP {status} for {canonical}"
                    )
                content = page.content().encode("utf-8")
                browser.close()
        except AllowlistViolation:
            raise
        except PlaywrightError as exc:
            raise AcquisitionError(
                f"Headless fetch failed for {canonical}: {exc}"
            ) from exc

        return FetchPayload(
            content=content,
            final_url=canonical,
            mode="headless",
            content_type="text/html",
        )
