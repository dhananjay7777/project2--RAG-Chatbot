"""Generate eval/golden/factual.yaml from policy/fact_seed.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

SCHEMES = [
    "groww-nippon-india-value-fund-direct-growth",
    "groww-samco-mid-cap-fund-direct-growth",
    "groww-franklin-india-multi-cap-fund-direct-growth",
]
KEYS = [
    "expense_ratio",
    "exit_load",
    "min_sip",
    "aum",
    "nav",
    "category",
    "risk_rating",
]
TEMPLATES = {
    "expense_ratio": [
        "What is the expense ratio of {name}?",
        "Tell me the TER / expense ratio for {name}.",
        "Expense ratio for {name} please.",
    ],
    "exit_load": [
        "What is the exit load on {name}?",
        "Exit load for {name}?",
        "What exit load applies to {name}?",
    ],
    "min_sip": [
        "What is the minimum SIP for {name}?",
        "Minimum SIP amount in {name}?",
        "What is the min SIP for {name}?",
    ],
    "aum": [
        "What is the AUM of {name}?",
        "AUM for {name}?",
        "What assets under management does {name} report?",
    ],
    "nav": [
        "What is the NAV of {name}?",
        "Current NAV for {name}?",
        "NAV of {name}?",
    ],
    "category": [
        "What is the category of {name}?",
        "Which category is {name} in?",
        "Fund category for {name}?",
    ],
    "risk_rating": [
        "What is the risk rating of {name}?",
        "Risk rating for {name}?",
        "How is {name} rated for risk on Groww?",
    ],
}


def main() -> None:
    seed = yaml.safe_load((ROOT / "policy/fact_seed.yaml").read_text(encoding="utf-8"))
    cases: list[dict] = []
    n = 0
    for sid in SCHEMES:
        name = seed["schemes"][sid]["scheme_name"]
        facts = seed["schemes"][sid]["facts"]
        for key in KEYS:
            val = facts.get(key)
            if val is None:
                continue
            needle = str(val).split("(")[0].strip()
            if len(needle) > 48:
                needle = needle[:48].rstrip()
            for tmpl in TEMPLATES[key]:
                n += 1
                cases.append(
                    {
                        "id": f"fact-{n:03d}",
                        "query": tmpl.format(name=name),
                        "expected_route": "FACTUAL",
                        "expected_source_id": sid,
                        "fact_key": key,
                        "expected_value_contains": needle,
                    }
                )
    out = {"version": 1, "set": "factual", "cases": cases}
    path = ROOT / "eval/golden/factual.yaml"
    path.write_text(
        yaml.safe_dump(out, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"wrote {len(cases)} factual cases to {path}")


if __name__ == "__main__":
    main()
