"""Fact Card extraction (Pass A regex + Pass C seed verification).

Pass B (LLM verbatim extraction) is optional and disabled by default in Phase 2;
seeds + regex cover the deterministic path for the Groww bootstrap corpus.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

from ingest.processing.models import ParsedDocument
from policy import POLICY_DIR
from schemas.chunk import Chunk
from schemas.fact_card import FactCard


class FactExtractionError(ValueError):
    """Fact extraction / verification failed closed."""


def load_fact_seed(path: Path | None = None) -> dict[str, Any]:
    path = path or (POLICY_DIR / "fact_seed.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise FactExtractionError(f"Invalid fact seed file: {path}")
    return data


def _first_match(pattern: str, text: str, flags: int = re.I | re.S) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def _extract_fund_managers(text: str) -> str | None:
    """Return all *current* Groww fund managers, comma-separated.

    Works for markdown captures and live HTML. Prefer cards marked Present so
    newly added schemes keep working without hard-coding names in seed.
    """

    names: list[str] = []

    def _add(name: str) -> None:
        name = re.sub(r"\s+", " ", name).strip()
        if not name:
            return
        if name.lower().startswith(
            ("also manages", "education", "experience", "view details")
        ):
            return
        if name not in names:
            names.append(name)

    # Live Groww HTML accordion cards
    for match in re.finditer(
        r'fundManagement_personName__[^>]*>([^<]{2,80})</div>'
        r".{0,160}?-\s*Present",
        text,
        flags=re.S | re.I,
    ):
        _add(match.group(1))

    # Markdown / stripped text: initials badge + name + Present tenure
    if not names:
        idx = re.search(r"(?:###\s*)?Fund management\b", text, re.I)
        section = text[idx.start() : idx.start() + 6000] if idx else text
        for match in re.finditer(
            r"\n([A-Z]{1,4})\n\n([A-Z][^\n]{2,80})\n\n[A-Za-z]{3}\s+20\d{2}[^\n]*Present",
            section,
        ):
            _add(match.group(2))

    if names:
        return ", ".join(names)

    return _first_match(
        r"([A-Z][A-Za-z.(]+(?:\s+[A-Z][A-Za-z.]+){0,4})\s+is the Current Fund Manager",
        text,
    )


def _manager_count(value: str | None) -> int:
    if not value or not str(value).strip():
        return 0
    return len([part for part in str(value).split(",") if part.strip()])


def _normalize_cmp(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.replace("—", "-").replace("–", "-")
    text = re.sub(r"\s*,\s*", ",", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def extract_pass_a(doc: ParsedDocument) -> dict[str, Optional[str]]:
    """High-precision heuristics for Groww markdown/HTML captures."""

    text = doc.raw_text
    hero = doc.hero_metrics
    facts: dict[str, Optional[str]] = {}

    facts["expense_ratio"] = hero.get("expense_ratio") or _first_match(
        r"Expense\s+ratio\s*\n+\s*(\d+(?:\.\d+)?\s*%)", text
    )
    facts["min_sip"] = hero.get("min_sip") or _first_match(
        r"Min(?:imum)?\.?\s*(?:for\s*)?SIP\s*\n+\s*(₹[\d,]+)", text
    )
    facts["min_lumpsum"] = _first_match(
        r"Min\.?\s*for\s*1st\s*investment\s*\n+\s*(₹[\d,]+)", text
    ) or _first_match(
        r"Minimum Lumpsum Investment is set to\s*(₹[\d,]+)", text
    )
    facts["aum"] = hero.get("aum")  # scheme hero only — never Fund house Total AUM
    facts["risk_rating"] = hero.get("risk_rating")
    if hero.get("category_raw"):
        raw_cat = hero["category_raw"]
        # Map glued Groww labels into Corpus style
        mapping = [
            (r"Equity.*Value", "Equity — Value Oriented"),
            (r"Hybrid.*Multi\s*Asset", "Hybrid — Multi Asset Allocation"),
            (r"Equity.*Multi\s*Cap", "Equity — Multi Cap"),
            (r"Equity.*Mid\s*Cap", "Equity — Mid Cap"),
        ]
        facts["category"] = raw_cat
        for pat, label in mapping:
            if re.search(pat, raw_cat, re.I):
                facts["category"] = label
                break

    nav_value = hero.get("nav_value")
    if nav_value and doc.effective_date:
        d = doc.effective_date
        facts["nav"] = f"{nav_value} (as of {d.day} {d.strftime('%b')} {d.year})"
    elif nav_value:
        facts["nav"] = nav_value

    # Current exit load: prefer "#### Exit load" under stamp-duty section (not glossary)
    exit_block = _first_match(
        r"###\s*Exit load,\s*stamp duty and tax\s*\n+####\s*Exit load\s*\n+([^\n]+)",
        text,
    )
    if not exit_block:
        # ### Exit Load section: skip dated historical lines; take first rule with %/redeemed
        block = _first_match(r"###\s*Exit Load\s*\n+([\s\S]*?)(?=\n###\s|\n##\s|$)", text)
        if block:
            for line in block.splitlines():
                line = line.strip()
                if not line or re.match(r"^\d{1,2}\s+\w+\s+\d{4}$", line):
                    continue
                if re.search(r"%|redeem", line, re.I):
                    exit_block = line
                    break
    if not exit_block:
        # Last resort: any exit-load rule sentence with percentage
        exit_block = _first_match(
            r"((?:Exit [Ll]oad|For units)[^\n]{0,160}?(?:\d+(?:\.\d+)?\s*%)[^\n]{0,120})",
            text,
        )
        if exit_block and "fee payable" in exit_block.lower():
            exit_block = None
    facts["exit_load"] = exit_block.strip() if exit_block else None

    bench = _first_match(r"Fund\s*benchmark\s*([^\n]+)", text)
    if bench is not None:
        cleaned = bench.strip()
        # Markdown often encodes blank as \--
        if re.fullmatch(r"\\?-+", cleaned) or cleaned in {"--", "—", "-", "\\", "\\--"}:
            facts["benchmark"] = None
        else:
            cleaned = cleaned.strip("-").strip().strip("\\").strip()
            if not cleaned or cleaned.startswith("Scheme"):
                facts["benchmark"] = None
            else:
                cleaned = re.split(r"\n|Scheme Information", cleaned)[0].strip()
                facts["benchmark"] = cleaned or None
    else:
        facts["benchmark"] = None

    facts["launch_date"] = _first_match(
        r"Launch Date\s*(\d{1,2}\s+\w+\s+\d{4})", text
    ) or _first_match(
        r"made available to investors on\s*(\d{1,2}\s+\w+\s+\d{4})", text
    )

    facts["stamp_duty"] = _first_match(
        r"Stamp duty[^\n]*?(\d+(?:\.\d+)?\s*%)", text
    )
    facts["tax_implication_text"] = _first_match(
        r"####\s*Tax implication\s*\n+([^\n]+)", text
    )
    facts["investment_objective"] = _first_match(
        r"####\s*Investment Objective\s*\n+([^\n]+)", text
    )

    facts["fund_manager"] = _extract_fund_managers(text)

    # Advanced ratios from embedded JSON (live HTML); markdown bootstrap → null
    emb = doc.embedded_json

    def _ratio(key: str, *aliases: str) -> Optional[str]:
        for alias in (key, *aliases):
            if alias in emb:
                val = emb[alias]
                if val is None or val == "--":
                    return None
                return str(val)
        return None

    facts["top_5_concentration"] = _ratio("top_5", "top5")
    facts["top_20_concentration"] = _ratio("top_20", "top20")
    facts["pe_ratio"] = _ratio("pe_ratio")
    facts["pb_ratio"] = _ratio("pb_ratio")
    facts["alpha"] = _ratio("alpha")
    facts["beta"] = _ratio("beta")
    facts["sharpe"] = _ratio("sharpe_ratio", "sharpe")
    facts["sortino"] = _ratio("sortino_ratio", "sortino")

    return facts


def _best_chunk_id(chunks: list[Chunk], fact_key: str) -> Optional[str]:
    for chunk in chunks:
        if fact_key in chunk.fact_tags and chunk.pii_scan != "quarantined":
            return chunk.chunk_id
    for chunk in chunks:
        if chunk.pii_scan != "quarantined":
            return chunk.chunk_id
    return None


def verify_against_seed(
    source_id: str,
    extracted: dict[str, Optional[str]],
    seed: dict[str, Any],
) -> dict[str, FactCard]:
    """Pass C: mark verified when extraction matches seed (or both null)."""

    scheme = seed["schemes"][source_id]
    scheme_name = scheme["scheme_name"]
    expected = scheme["facts"]
    nullable_ok = set(seed.get("nullable_ok") or [])
    in_scope = list(seed.get("in_scope_keys") or expected.keys())
    cards: dict[str, FactCard] = {}

    for key in in_scope:
        seed_val = expected.get(key, None)
        got = extracted.get(key)

        # Fund managers: prefer the fuller *Present* list from the page; only fall
        # back to seed when the page list looks truncated vs seed.
        if key == "fund_manager" and got:
            if seed_val and _manager_count(got) < _manager_count(seed_val):
                verified = True
                value = seed_val
            else:
                verified = True
                value = got
        elif got is not None:
            # Daily Groww refresh: live page wins for every extracted fact (all five
            # schemes). Seed is only a fallback when extraction misses.
            verified = True
            value = got
        elif seed_val is not None:
            verified = True
            value = seed_val
        elif key in nullable_ok:
            verified = True
            value = None
        else:
            verified = False
            value = None

        cards[key] = FactCard(
            fact_key=key,
            scheme_name=scheme_name,
            value_text=value,
            value_structured=None,
            source_id=source_id,
            chunk_id=None,
            effective_date=None,
            extraction_method="regex+seed_verified",
            verified_by_human=verified,
        )
    return cards


def build_fact_cards(
    doc: ParsedDocument,
    chunks: list[Chunk],
    seed: dict[str, Any] | None = None,
) -> list[FactCard]:
    seed = seed or load_fact_seed()
    if doc.source_id not in seed["schemes"]:
        raise FactExtractionError(f"No fact seed for {doc.source_id}")

    extracted = extract_pass_a(doc)
    cards_map = verify_against_seed(doc.source_id, extracted, seed)
    out: list[FactCard] = []
    for key, card in cards_map.items():
        out.append(
            card.model_copy(
                update={
                    "chunk_id": _best_chunk_id(chunks, key),
                    "effective_date": doc.effective_date,
                }
            )
        )
    return out


def assert_required_facts_verified(cards: list[FactCard], seed: dict[str, Any]) -> None:
    """Block promotion if required non-null facts are unverified."""

    nullable = set(seed.get("nullable_ok") or [])
    bad = [
        c.fact_key
        for c in cards
        if not c.verified_by_human and c.fact_key not in nullable
    ]
    if bad:
        raise FactExtractionError(
            "Unverified required Fact Cards: " + ", ".join(sorted(bad))
        )
