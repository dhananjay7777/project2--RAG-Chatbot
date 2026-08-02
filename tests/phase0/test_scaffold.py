"""Phase 0 — scaffold smoke tests."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PATHS = [
    "policy/source_allowlist.yaml",
    "policy/source_registry.yaml",
    "policy/refusal_taxonomy.yaml",
    "policy/prohibited_lexicon.yaml",
    "policy/pii_patterns.yaml",
    "schemas/__init__.py",
    "schemas/source.py",
    "schemas/chunk.py",
    "schemas/fact_card.py",
    "schemas/answer.py",
    "ingest/fetch.py",
    "ingest/registry.py",
    "ingest/acquisition/__init__.py",
    "ingest/acquisition/http.py",
    "ingest/acquisition/pipeline.py",
    "ingest/processing/__init__.py",
    "ingest/processing/pipeline.py",
    "ingest/processing/facts.py",
    "ingest/indexing/pipeline.py",
    "ingest/indexing/__init__.py",
    "policy/fact_seed.yaml",
    "ingest/parse/html.py",
    "ingest/parse/pdf.py",
    "ingest/normalize.py",
    "ingest/chunk.py",
    "ingest/facts.py",
    "ingest/index.py",
    "ingest/freshness/pipeline.py",
    "ingest/freshness/cli.py",
    ".github/workflows/corpus-refresh.yml",
    "core/router.py",
    "core/router/pipeline.py",
    "core/synthesis/pipeline.py",
    "core/synthesis/orchestrator.py",
    "core/retrieve.py",
    "core/synthesize.py",
    "core/llm/client.py",
    "core/validate/chain.py",
    "app/api/main.py",
    "app/ui/streamlit_app.py",
    "app/ui/presenter.py",
    "frontend/package.json",
    "frontend/src/app/page.tsx",
    "Dockerfile",
    "railway.toml",
    "vercel.json",
    "docs/Deploy.md",
    "docs/KnownLimitations.md",
    "eval/run_eval.py",
    "eval/golden/factual.yaml",
    "data/raw/.gitkeep",
    "data/processed/.gitkeep",
    "data/index/.gitkeep",
    "config.yaml",
    ".env.example",
    "Makefile",
    "docs/Corpus.md",
    "docs/Disclaimer.md",
    "docs/Architecture.md",
]


def test_phase_folder_scaffold_exists():
    missing = [p for p in REQUIRED_PATHS if not (ROOT / p).exists()]
    assert not missing, f"Missing scaffold paths: {missing}"


def test_health_stub():
    from app.api.main import health

    payload = health()
    assert payload["status"] == "ok"
    assert "Facts-only" in payload["disclaimer"]


def test_pdf_parser_stub_is_explicit_noop_failure():
    from ingest.parse.pdf import parse_pdf

    try:
        parse_pdf(b"%PDF")
        assert False, "expected NotImplementedError"
    except NotImplementedError as exc:
        assert "HTML-only" in str(exc) or "not used" in str(exc).lower()
