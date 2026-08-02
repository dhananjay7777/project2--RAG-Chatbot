.PHONY: test ingest ingest-headless bootstrap bootstrap-dev validate-corpus process process-audit index refresh eval serve serve-api serve-web lint-policy install

SNAPSHOT_DIR ?=

install:
	pip install -r requirements.txt
	pre-commit install

test:
	python -m pytest tests -q

lint-policy:
	python -m pytest tests/phase0/test_policy_files.py tests/phase0/test_allowlist.py -q

ingest:
	python -m ingest.acquisition fetch

ingest-headless:
	python -m ingest.acquisition fetch --headless

bootstrap:
	python -m ingest.acquisition bootstrap --snapshot-dir "$(SNAPSHOT_DIR)"

bootstrap-dev:
	python -m ingest.acquisition bootstrap --snapshot-dir data/bootstrap/snapshots

validate-corpus:
	python -m ingest.acquisition validate

process:
	python -m ingest.processing process

process-audit:
	python -m ingest.processing audit

index:
	python -m ingest.indexing build

# Phase 9 local freshness: live fetch → validate → process → index (fail-closed).
refresh:
	python -m ingest.freshness refresh

eval:
	python -m eval.run_eval --json eval/artifacts/scorecard.latest.json

serve:
	streamlit run app/ui/streamlit_app.py

serve-api:
	uvicorn app.api.main:app --host 127.0.0.1 --port 8000

# Phase 10 — local static UI replaced by Next.js (Stitch design).
serve-web:
	npm run dev --prefix frontend
