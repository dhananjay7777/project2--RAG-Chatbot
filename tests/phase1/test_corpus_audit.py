"""Corpus audit: bootstrap snapshots vs live HTML for Advanced ratios."""

from pathlib import Path

from ingest.acquisition.corpus_audit import audit_raw_corpus


def test_bootstrap_artifacts_lack_ui_advanced_block():
    root = Path("data/raw")
    if not (root / "latest.json").exists():
        return
    rows = audit_raw_corpus(root)
    assert len(rows) == 5
    # Markdown bootstrap captures holdings/returns but not the Advanced ratios panel.
    assert all(not r.ui_advanced_block for r in rows)
