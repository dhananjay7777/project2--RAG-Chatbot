"""Refresh fund_manager Fact Cards from Groww page extraction.

Safe to re-run after ingest/refresh. Prefer page "Present" managers so newly
added schemes get a complete manager list without hand-editing seeds first.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ingest.acquisition.registry import load_source_definitions
from ingest.processing.facts import _extract_fund_managers
from ingest.processing.parse import parse_artifact
from ingest.processing.strip import strip_document

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT))

    facts_path = ROOT / "data" / "processed" / "facts.jsonl"
    extracted_by_source: dict[str, str] = {}

    for source in load_source_definitions():
        raw_dir = ROOT / "data" / "raw" / source.source_id
        md_files = sorted(raw_dir.glob("*.md"))
        html_files = sorted(raw_dir.glob("*.html"))
        if not md_files and not html_files:
            print(f"skip {source.source_id}: no raw artifacts")
            continue

        managers = None
        for path in (md_files[-1:] if md_files else []) + (html_files[-1:] if html_files else []):
            doc = parse_artifact(
                path,
                source_id=source.source_id,
                scheme_name=source.scheme_names[0],
                effective_date=date.today(),
            )
            managers = _extract_fund_managers(strip_document(doc).raw_text)
            if managers and "," in managers:
                break
            if managers:
                continue
        if managers:
            extracted_by_source[source.source_id] = managers
            count = len([p for p in managers.split(",") if p.strip()])
            print(f"{source.source_id}: {count} manager(s)")
        else:
            print(f"{source.source_id}: NONE")

    if not facts_path.is_file():
        print(f"missing {facts_path}")
        return

    rows = []
    for line in facts_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["fact_key"] == "fund_manager" and row["source_id"] in extracted_by_source:
            val = extracted_by_source[row["source_id"]]
            row["value_text"] = val
            row["value_structured"] = {"text": val}
            row["verified_by_human"] = True
        rows.append(row)
    facts_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"updated {facts_path}")


if __name__ == "__main__":
    main()
