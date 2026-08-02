"""Phase 2 HTML parsing helpers."""

from ingest.processing.parse import _html_to_text


def parse_html(raw: bytes) -> str:
    return _html_to_text(raw.decode("utf-8", errors="replace"))
