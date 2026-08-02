"""Strict HTTP acquisition with allowlist, robots, throttling, and retries."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

from ingest.acquisition.models import FetchPayload
from policy.loader import canonicalize_url, load_allowlist

LOGGER = logging.getLogger(__name__)
USER_AGENT = (
    "MF-FAQ-Assistant/1.0 "
    "(facts-only educational project; contact: local-project)"
)
RETRYABLE_STATUS = {403, 429, 500, 502, 503, 504}


class AcquisitionError(RuntimeError):
    """Base error for a source acquisition attempt."""


class AllowlistViolation(AcquisitionError):
    """A URL escaped the exact five-URL corpus."""


class RobotsDeniedError(AcquisitionError):
    """robots.txt disallows the frozen source path."""


class FetchFailedError(AcquisitionError):
    """Network retries were exhausted or HTTP response was terminal."""


class SessionLike(Protocol):
    def get(self, url: str, **kwargs): ...


class RobotsPolicy(Protocol):
    def assert_allowed(self, url: str, user_agent: str) -> None: ...


@dataclass
class RateLimiter:
    """Per-host minimum-interval limiter (default: one request per 2 seconds)."""

    min_interval_seconds: float = 2.0
    sleeper: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    _last_request: dict[str, float] = field(default_factory=dict)

    def wait(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        now = self.clock()
        previous = self._last_request.get(host)
        if previous is not None:
            remaining = self.min_interval_seconds - (now - previous)
            if remaining > 0:
                self.sleeper(remaining)
        self._last_request[host] = self.clock()


class RemoteRobotsPolicy:
    """Fetch and cache host robots rules.

    ``robots.txt`` is operational protocol metadata: it is never stored, indexed,
    or cited as corpus content. If it cannot be checked, acquisition fails closed.
    """

    def __init__(
        self,
        session: SessionLike | None = None,
        *,
        timeout_seconds: float = 15.0,
    ):
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self._cache: dict[str, RobotFileParser] = {}

    def assert_allowed(self, url: str, user_agent: str) -> None:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc.lower()}"
        parser = self._cache.get(origin)
        if parser is None:
            robots_url = f"{origin}/robots.txt"
            try:
                response = self.session.get(
                    robots_url,
                    headers={"User-Agent": user_agent},
                    timeout=self.timeout_seconds,
                    allow_redirects=True,
                )
            except requests.RequestException as exc:
                raise RobotsDeniedError(
                    f"Could not verify robots.txt for {origin}: {exc}"
                ) from exc
            if response.status_code >= 400:
                raise RobotsDeniedError(
                    f"Could not verify robots.txt for {origin}: "
                    f"HTTP {response.status_code}"
                )
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
            self._cache[origin] = parser

        if not parser.can_fetch(user_agent, url):
            raise RobotsDeniedError(f"robots.txt disallows: {url}")


class AllowAllRobotsPolicy:
    """Explicit offline/testing policy; never use for a live promoted run."""

    def assert_allowed(self, url: str, user_agent: str) -> None:
        del url, user_agent


class StrictHttpFetcher:
    """Fetch one allowlisted page without silently following slug changes."""

    def __init__(
        self,
        *,
        session: SessionLike | None = None,
        robots: RobotsPolicy | None = None,
        limiter: RateLimiter | None = None,
        retries: int = 3,
        backoff_seconds: float = 1.0,
        timeout_seconds: float = 30.0,
        sleeper: Callable[[float], None] = time.sleep,
        allowlist: list[str] | None = None,
    ):
        self.session = session or requests.Session()
        self.robots = robots or RemoteRobotsPolicy(self.session)
        self.limiter = limiter or RateLimiter()
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.timeout_seconds = timeout_seconds
        self.sleeper = sleeper
        self.allowlist = set(allowlist or load_allowlist())

    def fetch(self, url: str) -> FetchPayload:
        """Fetch bytes, validating the URL before any source-page HTTP call."""

        canonical = canonicalize_url(url)
        if canonical not in self.allowlist:
            raise AllowlistViolation(
                f"Refusing non-allowlisted source URL before HTTP: {url}"
            )

        self.robots.assert_allowed(canonical, USER_AGENT)
        current_url = canonical
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                self.limiter.wait(current_url)
                response = self.session.get(
                    current_url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "text/html,application/xhtml+xml",
                    },
                    timeout=self.timeout_seconds,
                    allow_redirects=False,
                )

                if 300 <= response.status_code < 400:
                    location = response.headers.get("Location")
                    if not location:
                        raise FetchFailedError(
                            f"Redirect without Location for {current_url}"
                        )
                    target = urljoin(current_url, location)
                    target_canonical = canonicalize_url(target)
                    if (
                        target_canonical not in self.allowlist
                        or target_canonical != canonical
                    ):
                        raise AllowlistViolation(
                            "Redirect changed the frozen corpus URL: "
                            f"{canonical} -> {target}"
                        )
                    current_url = target
                    continue

                if response.status_code in RETRYABLE_STATUS:
                    raise FetchFailedError(
                        f"Retryable HTTP {response.status_code} for {current_url}"
                    )
                if response.status_code >= 400:
                    raise FetchFailedError(
                        f"Terminal HTTP {response.status_code} for {current_url}"
                    )

                content_type = response.headers.get("Content-Type", "text/html")
                return FetchPayload(
                    content=response.content,
                    final_url=current_url,
                    mode="http",
                    content_type=content_type,
                )
            except AllowlistViolation:
                raise
            except (requests.RequestException, FetchFailedError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                delay = self.backoff_seconds * (2**attempt)
                LOGGER.warning(
                    "Fetch attempt %s/%s failed for %s: %s; retrying in %.1fs",
                    attempt + 1,
                    self.retries + 1,
                    canonical,
                    exc,
                    delay,
                )
                self.sleeper(delay)

        raise FetchFailedError(
            f"Fetch failed after {self.retries + 1} attempts for {canonical}: "
            f"{last_error}"
        )
