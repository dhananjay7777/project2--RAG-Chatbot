"""Test doubles and page fixtures for Phase 1."""

from __future__ import annotations

from dataclasses import dataclass

from ingest.acquisition.models import FetchPayload


def html_page(
    scheme_name: str,
    *,
    nav_date: str | None = "24 Jul '26",
    marker: str = "",
) -> bytes:
    nav = f"<p>NAV: {nav_date}</p>" if nav_date else ""
    padding = "<p>Official Groww scheme information.</p>" * 80
    return (
        "<!doctype html><html><body>"
        f"<h1>{scheme_name}</h1>{nav}{marker}{padding}"
        "</body></html>"
    ).encode()


def markdown_page(
    scheme_name: str,
    *,
    nav_date: str | None = "24 Jul '26",
) -> bytes:
    nav = f"NAV: {nav_date}\n\n" if nav_date else ""
    padding = "Official Groww scheme information.\n\n" * 80
    return f"# {scheme_name}\n\n{nav}{padding}".encode()


@dataclass
class FakeResponse:
    status_code: int
    content: bytes = b""
    headers: dict[str, str] | None = None
    text: str = ""

    def __post_init__(self):
        if self.headers is None:
            self.headers = {"Content-Type": "text/html"}
        if not self.text and self.content:
            self.text = self.content.decode(errors="replace")


class QueueSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected HTTP request")
        return self.responses.pop(0)


class MappingFetcher:
    def __init__(self, pages: dict[str, bytes], *, mode: str = "http"):
        self.pages = pages
        self.mode = mode
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchPayload:
        self.calls.append(url)
        return FetchPayload(
            content=self.pages[url],
            final_url=url,
            mode=self.mode,
            content_type="text/html",
        )
