# Known Limitations

Honest scope for the Mutual Fund FAQ Assistant (facts-only RAG over five Groww pages).

## Corpus

- Exactly **five** Groww Direct Growth scheme URLs. No sixth URL of any kind.
- No AMC / AMFI / SEBI primary documents (SID, KIM, factsheets, educational pages).
- No ELSS scheme → no lock-in answers (`NO_ANSWER`).
- No statement / capital-gains download process answers (`NO_ANSWER`).
- Holdings / portfolio tables are stripped from the index and never answered.
- Corpus currency is the last successful Phase 9 refresh (footer dates + Validator 8 SLAs).

## Behaviour

- **Facts-only. No investment advice.** Advisory and comparative queries are refused.
- No performance / returns / rank / calculator answers. Those routes redirect to the
  scheme’s Groww page without quoting return tables.
- Tax *text* present on a Groww page may be quoted; tax *outcomes* are never calculated.
- English-oriented UI and prompts; no multi-turn memory across questions.
- Each query is answered independently (no conversation state on the server).

## Model / ops

- Factual phrasing requires **Groq** (`GROQ_API_KEY`). Scraped pages and Fact Cards are
  CONTEXT only — never shown raw to the user. If Groq is unavailable, factual asks
  become no-answer.
- Refusals and performance redirects skip Groq.
- Public demo: **Vercel** (static UI) + **Railway** (FastAPI). Ask-time serving never
  live-fetches Groww; it reads the last promoted `data/` artifacts only.
- Railway deploy uses **BM25-only** retrieval (`MF_RETRIEVAL_MODE=bm25`) to stay within
  Hobby RAM; local/dev keeps hybrid BM25 + dense + `bge-reranker-base`.
- Fact answers come from the last promoted corpus (daily **corpus-refresh** + Railway
  image rebuild). Chat never live-scrapes Groww at ask time.
- Per-IP rate limit (~30 `/ask` calls per hour) bounds LLM cost.

## Advanced ratios

Groww’s live site may show Top 5 / Top 20, P/E, P/B, and risk ratios (often `--` when
Groww has no value). Markdown bootstrap snapshots may omit that panel; live HTML ingest
carries embedded JSON for Phase 2. Do not invent ratios when the source shows `--`.
