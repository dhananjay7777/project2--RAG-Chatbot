"""Sync live-extracted fact_seed fields from processed facts.jsonl.

Used after corpus refresh so the next day's fallback seed matches Groww.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Fields that regularly change on Groww and must track daily refresh.
SYNC_KEYS = (
    "nav",
    "aum",
    "expense_ratio",
    "min_sip",
    "min_lumpsum",
    "risk_rating",
    "category",
    "exit_load",
    "fund_manager",
    "benchmark",
)


def main() -> None:
    facts: dict[str, dict[str, str | None]] = {}
    for line in (ROOT / "data/processed/facts.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        key = row["fact_key"]
        if key not in SYNC_KEYS:
            continue
        facts.setdefault(row["source_id"], {})[key] = row.get("value_text")

    path = ROOT / "policy/fact_seed.yaml"
    text = path.read_text(encoding="utf-8")
    updated = 0
    for source_id, values in facts.items():
        for key, value in values.items():
            if value is None:
                pattern = rf"(  {re.escape(source_id)}:[\s\S]*?{re.escape(key)}: )(?:null|\"[^\"]*\")"
                repl = r"\1null"
                text, n = re.subn(pattern, repl, text, count=1)
            else:
                pattern = rf'(  {re.escape(source_id)}:[\s\S]*?{re.escape(key)}: )(?:null|"[^"]*")'
                text, n = re.subn(
                    pattern,
                    lambda m, v=value: m.group(1) + json.dumps(v, ensure_ascii=False),
                    text,
                    count=1,
                )
            if n != 1:
                raise SystemExit(f"could not update {key} for {source_id} (n={n})")
            updated += 1
    path.write_text(text, encoding="utf-8")
    print(f"synced {updated} seed values across {len(facts)} schemes")


if __name__ == "__main__":
    main()
