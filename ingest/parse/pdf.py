"""PDF parsing is out of scope for the Groww HTML-only corpus.

Kept as an explicit stub so callers fail loudly if invoked.
"""


def parse_pdf(raw: bytes) -> str:
    raise NotImplementedError(
        "PDF parsing is not used in this project (HTML-only corpus)"
    )
