# Mutual Fund FAQ Assistant (Facts-Only)

Facts-only RAG assistant for five Groww mutual-fund scheme pages.
**No investment advice.** Every answer carries exactly one citation and a last-updated footer.

## Disclaimer

**Facts-only. No investment advice.**

## Corpus (locked)

Exactly five Groww Direct Growth schemes — see [`docs/Corpus.md`](docs/Corpus.md):

1. Nippon India Value Fund Direct Growth
2. Tata Multi Asset Allocation Fund Direct Growth
3. Kotak Multi Asset Allocation Fund Direct Growth
4. Franklin India Multi Cap Fund Direct Growth
5. Samco Mid Cap Fund Direct Growth

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
pre-commit install
cp .env.example .env   # then set GROQ_API_KEY
```

Factual answers are **RAG**: retrieve corpus chunks (plus optional Fact Card context) →
**Groq** → answer. Set `GROQ_API_KEY` in `.env` (see
[console.groq.com](https://console.groq.com/)). Without a key, factual asks return
no-answer rather than dumping scraped text. Refusals / redirects do not call Groq.
Optional Tier-2 routing also uses Groq.

Build the corpus once (or after Phase 9 refresh):

```bash
make refresh   # live fetch → validate → process → index
# or stepwise: make ingest && make process && make index
```

```python
from core.ask import ask

envelope = ask("What is the expense ratio of Nippon India Value Fund Direct Growth?")
```

On Windows, `chromadb` may not install without MSVC; Phase 3 falls back to
`data/index/dense_vectors.pkl` automatically. Linux/macOS (Railway) uses Chroma when available.

## Local UI / API

```bash
make serve-api   # FastAPI → http://127.0.0.1:8000
make serve-web   # Next.js UI → http://localhost:3000
make serve       # Streamlit (local / optional MF_API_URL)
```

```bash
cd frontend
cp .env.example .env.local   # NEXT_PUBLIC_MF_API_URL=http://127.0.0.1:8000
npm install && npm run dev
```

## Deploy (Phase 10)

Public demo split:

| Layer | Host | Config |
| --- | --- | --- |
| Chat UI | **Vercel** | Next.js `frontend/` (`NEXT_PUBLIC_MF_API_URL`) |
| Ask API | **Railway** | `Dockerfile` + `railway.toml` (`GROQ_API_KEY`, `CORS_ORIGINS`) |

Full runbook: [`docs/Deploy.md`](docs/Deploy.md).

## Commands

```bash
make test             # run pytest
make ingest           # fetch all five live URLs (strict, no partial promotion)
make ingest-headless  # same, with optional Playwright fallback
make process          # Phase 2: chunk + Fact Cards into data/processed
make process-audit    # audit strip + verification on processed output
make index            # Phase 3: Chroma + BM25 from data/processed
make refresh          # Phase 9: python -m ingest.freshness refresh
make eval             # Phase 8: golden scorecard (python -m eval.run_eval)
make validate-corpus  # validate latest manifest and raw artifacts
make lint-policy      # validate policy files and allowlist cardinality
make serve            # Streamlit UI (Phase 7)
make serve-api        # FastAPI on :8000
make serve-web        # Next.js UI on :3000
```

Daily corpus refresh is also scheduled in GitHub Actions
([`.github/workflows/corpus-refresh.yml`](.github/workflows/corpus-refresh.yml)):
daily **10:00 AM IST** (`30 4 * * *` UTC), plus manual **Run workflow**. On success it force-commits updated
`data/raw`, `data/processed`, and `data/index` for Railway image builds.

Windows / direct Python equivalents:

```powershell
python -m ingest.acquisition fetch
python -m ingest.processing process
python -m ingest.indexing build
python -m ingest.freshness refresh
streamlit run app/ui/streamlit_app.py
uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Snapshot bootstrap is for offline development only and writes
`promotion_ready: false`. Before a demo or eval promotion, run a live fetch. For
the optional browser fallback, install `requirements-headless.txt` and run
`playwright install chromium`.

## Project layout

| Path | Phase | Role |
| --- | --- | --- |
| `policy/` | 0 | Compliance rules, allowlist, refusal templates, fact seeds |
| `schemas/` | 0 | Pydantic data contracts |
| `ingest/acquisition/` | 1 | Fetch, robots, storage, manifest CLI |
| `ingest/processing/` | 2 | Parse, strip, normalize, PII, chunk, Fact Cards |
| `ingest/indexing/` | 3 | Chroma + BM25 index build |
| `ingest/freshness/` | 9 | Scheduled live refresh orchestrator |
| `core/` | 3–6 | Retrieve, synthesize, validate, compose |
| `app/ui/` | 7 | Streamlit UI (local) |
| `app/api/` | 7–10 | FastAPI `GET /health`, `POST /ask` (+ CORS, rate limit) |
| `frontend/` | 10 | Next.js (Vercel) Stitch / Lumina Nexus chat UI |
| `data/` | 1–9 | Raw HTML, processed chunks, indexes (refreshed by Phase 9) |
| `eval/` | 8 | Golden sets + scorecard (`eval/artifacts/`) |
| `docs/` | — | Architecture, Deploy, KnownLimitations, Corpus, Disclaimer |
| `tests/` | all | Automated tests |

## Architecture & limitations

- Architecture: [`docs/Architecture.md`](docs/Architecture.md)
- Known limitations: [`docs/KnownLimitations.md`](docs/KnownLimitations.md)
- Deploy: [`docs/Deploy.md`](docs/Deploy.md)
- Disclaimer: [`docs/Disclaimer.md`](docs/Disclaimer.md)

## Status

- [x] Phase 0 — Foundations & Compliance Spec
- [x] Phase 1 — Corpus Acquisition
- [x] Phase 2 — Document Processing
- [x] Phase 3 — Indexing & Retrieval
- [x] Phase 4 — Guardrails: Intent Router
- [x] Phase 5 — Constrained Synthesis
- [x] Phase 6 — Output Validation
- [x] Phase 7 — Minimal UI
- [x] Phase 8 — Evaluation & Observability (`make eval`, structured telemetry)
- [x] Phase 9 — Freshness Scheduler (`ingest.freshness`, Actions `corpus-refresh`, `make refresh`)
- [x] Phase 10 — Deployment & Handover (Vercel UI + Railway API)
