"""Sync policy/fact_seed.yaml fund_manager fields from processed facts.jsonl."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    facts: dict[str, str] = {}
    for line in (ROOT / "data/processed/facts.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["fact_key"] == "fund_manager" and row.get("value_text"):
            facts[row["source_id"]] = row["value_text"]

    path = ROOT / "policy/fact_seed.yaml"
    text = path.read_text(encoding="utf-8")
    for source_id, value in facts.items():
        pattern = rf'(  {re.escape(source_id)}:[\s\S]*?fund_manager: )"[^"]*"'
        text, n = re.subn(pattern, lambda m, v=value: m.group(1) + json.dumps(v), text, count=1)
        if n != 1:
            raise SystemExit(f"could not update fund_manager for {source_id} (n={n})")
    path.write_text(text, encoding="utf-8")
    print(f"synced {len(facts)} fund_manager seed values")


if __name__ == "__main__":
    main()
