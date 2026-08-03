"""Parse Groww markdown/HTML artifacts into sections + hero metrics."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from ingest.processing.models import ParsedDocument, Section

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_NAV_DATE = re.compile(
    r"NAV:\s*(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"(?:[a-z]*)\s+[’']?(\d{2}|\d{4})",
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
_JSON_KEYS = (
    "sharpe_ratio",
    "sortino_ratio",
    "pe_ratio",
    "pb_ratio",
    "beta",
    "alpha",
    "standard_deviation",
)


def _parse_nav_date(text: str) -> date | None:
    match = _NAV_DATE.search(text)
    if not match:
        match = re.search(
            r"NAV as of\s+(\d{1,2})\s+"
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+"
            r"[’']?(\d{2}|\d{4})",
            text,
            re.IGNORECASE,
        )
    if not match:
        return None
    day = int(match.group(1))
    month = _MONTHS[match.group(2)[:3].lower()]
    year = int(match.group(3))
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _extract_groww_html_metrics(raw: str) -> dict[str, str]:
    """Pull NAV/AUM/etc. from Groww HTML where values live in divs, not <p> tags."""

    metrics: dict[str, str] = {}
    about = re.search(
        r"Latest NAV as of\s+(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+"
        r"(\d{4})\s+is\s+(₹[\d,]+\.\d+)",
        raw,
        re.IGNORECASE,
    )
    if about:
        metrics["nav_value"] = about.group(4).strip()
        try:
            metrics["nav_date"] = date(
                int(about.group(3)),
                _MONTHS[about.group(2)[:3].lower()],
                int(about.group(1)),
            ).isoformat()
        except (ValueError, KeyError):
            pass
    if "nav_value" not in metrics:
        near = re.search(
            r"NAV:\s*.{0,240}?(₹[\d,]+\.\d+)",
            raw,
            re.IGNORECASE | re.DOTALL,
        )
        if near:
            metrics["nav_value"] = near.group(1).strip()

    aum = re.search(
        r"Fund size\s*\(AUM\).{0,240}?(₹[\d,]+\.?\d*\s*Cr)",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    if aum:
        metrics["aum"] = re.sub(r"\s+", " ", aum.group(1)).strip()

    expense = re.search(
        r"Expense ratio.{0,200}?(\d+(?:\.\d+)?\s*%)",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    if expense:
        metrics["expense_ratio"] = expense.group(1).strip()

    sip = re.search(
        r"Min\.\s*for\s*SIP.{0,200}?(₹[\d,]+)",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    if sip:
        metrics["min_sip"] = sip.group(1).strip()

    lumpsum = re.search(
        r"Min\.\s*for\s*1st\s*investment.{0,200}?(₹[\d,]+)",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    if lumpsum:
        metrics["min_lumpsum"] = lumpsum.group(1).strip()

    return metrics


def _extract_hero_metrics(text: str, scheme_name: str) -> dict[str, str]:
    """Pull hero block metrics that appear before Holdings / Return calculator."""

    cut = re.search(
        r"(##\s+Holdings|###\s+Return calculator|##\s+Understand terms)",
        text,
        re.IGNORECASE,
    )
    hero = text[: cut.start()] if cut else text[: 2500]
    metrics: dict[str, str] = {}

    nav = re.search(
        r"NAV:\s*[^\n]+\n\s*\n(₹[\d,]+\.?\d*)",
        hero,
        re.IGNORECASE,
    )
    if nav:
        metrics["nav_value"] = nav.group(1).strip()

    for label, key in [
        (r"Min\.\s*for\s*SIP", "min_sip"),
        (r"Expense\s+ratio", "expense_ratio"),
        (r"Fund\s+size\s*\(AUM\)", "aum"),
    ]:
        match = re.search(
            rf"{label}\s*\n+\s*(₹?[\d,]+\.?\d*\s*%?(?:\s*Cr)?)",
            hero,
            re.IGNORECASE,
        )
        if match:
            metrics[key] = match.group(1).strip()

    # Category + risk often appear as: EquityValue OrientedVery High Risk
    risk = re.search(
        r"(Very High Risk|High Risk|Moderately High Risk|Moderate Risk|"
        r"Low to Moderate Risk|Low Risk)",
        hero,
        re.IGNORECASE,
    )
    if risk:
        metrics["risk_rating"] = risk.group(1).strip()

    # Heuristic category from first content line after H1
    h1 = re.search(rf"#\s*{re.escape(scheme_name)}\s*\n+([^\n#]+)", text)
    if h1:
        line = h1.group(1).strip()
        line = re.sub(r"Very High Risk|High Risk|Moderate Risk|Low Risk", "", line, flags=re.I)
        # Insert separators for glued Groww labels
        line = re.sub(r"(Equity|Hybrid|Debt)([A-Z])", r"\1 — \2", line)
        line = re.sub(r"(Oriented|Allocation|Cap)([A-Z])", r"\1", line)
        cleaned = re.sub(r"\s+", " ", line).strip(" —")
        if cleaned and len(cleaned) < 80:
            metrics["category_raw"] = cleaned

    return metrics


def _extract_embedded_json(text: str) -> dict[str, Any]:
    """Best-effort pull of Groww embedded metric keys from live HTML."""

    found: dict[str, Any] = {}
    for key in _JSON_KEYS:
        match = re.search(rf'"{key}"\s*:\s*(null|"[^"]*"|-?\d+(?:\.\d+)?)', text)
        if not match:
            continue
        raw = match.group(1)
        if raw == "null":
            found[key] = None
        elif raw.startswith('"'):
            found[key] = raw.strip('"')
        else:
            found[key] = float(raw) if "." in raw else int(raw)
    # Concentration / advanced UI often absent from static HTML labels
    for key in ("top_5", "top_20", "top5", "top20"):
        match = re.search(rf'"{key}"\s*:\s*(null|-?\d+(?:\.\d+)?)', text, re.I)
        if match and match.group(1) != "null":
            found[key] = float(match.group(1))
    return found


def _sections_from_markdown(text: str) -> list[Section]:
    matches = list(_HEADING.finditer(text))
    if not matches:
        return [Section(heading="Document", heading_path=["Document"], text=text.strip(), level=1)]

    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(
            Section(heading="Preamble", heading_path=["Preamble"], text=preamble, level=1)
        )

    for i, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        path = [name for _, name in stack]
        sections.append(
            Section(heading=title, heading_path=path, text=body, level=level)
        )
    return sections


def _html_to_text(raw: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError(
            "beautifulsoup4 is required for HTML parsing. "
            "pip install beautifulsoup4"
        ) from exc

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    # Prefer main content if present
    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines: list[str] = []
    for el in main.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th"]):
        name = el.name or ""
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        if name.startswith("h") and name[1:].isdigit():
            level = int(name[1:])
            lines.append("#" * level + " " + text)
        else:
            lines.append(text)
    return "\n\n".join(lines)


def parse_artifact(
    path: Path,
    *,
    source_id: str,
    scheme_name: str,
    effective_date: date | None = None,
) -> ParsedDocument:
    raw_bytes = path.read_bytes()
    raw = raw_bytes.decode("utf-8", errors="replace")
    suffix = path.suffix.lower()
    content_format = "html" if suffix in {".html", ".htm"} else "markdown"
    embedded = _extract_embedded_json(raw)

    if content_format == "html":
        text = _html_to_text(raw)
    else:
        # Drop Source URL / Title metadata lines from bootstrap exports
        text = re.sub(r"^Source URL:.*$", "", raw, flags=re.M)
        text = re.sub(r"^Title:.*$", "", text, flags=re.M)

    sections = _sections_from_markdown(text)
    hero = _extract_hero_metrics(text, scheme_name)
    html_metrics: dict[str, str] = {}
    if content_format == "html":
        # Groww SPA stores NAV/AUM in divs; BeautifulSoup text pass often drops them.
        html_metrics = _extract_groww_html_metrics(raw)
        for key, value in html_metrics.items():
            if key == "nav_date":
                continue
            if value:
                hero[key] = value
    nav_date = effective_date
    if nav_date is None and html_metrics.get("nav_date"):
        try:
            nav_date = date.fromisoformat(html_metrics["nav_date"])
        except ValueError:
            nav_date = None
    if nav_date is None:
        nav_date = _parse_nav_date(text) or _parse_nav_date(raw)

    return ParsedDocument(
        source_id=source_id,
        scheme_name=scheme_name,
        effective_date=nav_date,
        raw_text=text,
        sections=sections,
        hero_metrics=hero,
        embedded_json=embedded,
        content_format=content_format,
    )
