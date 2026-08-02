# Phase 1 — Corpus Acquisition — Edge Cases

> Architecture: [Architecture.md § Phase 1](../Architecture.md).
> Corpus lock: [Corpus.md](../Corpus.md).
> Goal: exactly five active Groww sources with provenance; nothing else enters `data/raw/`.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| P1-01 | Fetcher is asked for a sixth URL (any host, including other Groww pages) | Hard error before HTTP. No bytes written under `data/raw/`. | Critical | Unit: fetch allowlist gate |
| P1-02 | Groww returns 403 / 429 / 5xx for one of the five | Retry with backoff; on terminal failure mark `status: fetch_failed` and **block promotion** (active count must not drop silently). | Critical | Integration: fetch failure |
| P1-03 | Groww returns 200 but empty / challenge HTML (bot wall) | Detect sparse body (below min-byte or missing scheme H1); mark fetch failed or escalate to Playwright path — never index bot-wall HTML as a scheme page. | Critical | Integration: sparse-body detector |
| P1-04 | Static HTML empty; Playwright succeeds | Same `source_id` / URL; store Playwright snapshot as the raw artifact; record `parser_version` / fetch mode in metadata. | High | Integration: headless fallback |
| P1-05 | Content hash unchanged on re-fetch | Touch `fetched_at` only; do not rewrite raw file; skip downstream reprocess. | Medium | Unit: change detection |
| P1-06 | Content hash changed (layout or fact update) | Write new raw object keyed by new sha256; keep old raw immutable; mark prior `SourceRecord` superseded only after successful reprocess + eval. | High | Integration: supersede chain |
| P1-07 | Slug redirects to a different path (301 to new Groww URL) | Do **not** follow into a non-allowlisted final URL. Fail fetch; treat as corpus-breaking (update Architecture + Corpus + allowlist together). | Critical | Integration: redirect policy |
| P1-08 | HTTP `Last-Modified` disagrees with on-page NAV date | Prefer on-page `NAV: <date>` for `effective_date`; ignore CDN headers. | High | Unit: effective_date extraction |
| P1-09 | NAV date missing on page | Fall back to UTC date of `fetched_at`; log warning. | Medium | Unit |
| P1-10 | Bootstrap from offline snapshot vs live fetch diverge | Live fetch wins for promotion; snapshots allowed only for offline unit tests, flagged `status` / env. | High | CI env matrix |
| P1-11 | Partial corpus: 4/5 fetched successfully | Ingest job fails closed. Demo/index build must not proceed on a subset. | Critical | Integration |
| P1-12 | Disk write of raw HTML fails mid-way | Transactional: no half-registered `SourceRecord` with missing artifact. | High | Integration: crash recovery |
| P1-13 | `robots.txt` disallows the path | Log and fail that source; do not scrape in violation. Escalate to manual snapshot only with documented exception in Corpus.md. | High | Manual + fetch gate |
| P1-14 | Duplicate `source_id` inserted into registry | Reject; `source_id` unique. | Critical | Unit: registry CRUD |
| P1-15 | Registry row URL ≠ allowlist entry (typo) | Validation fails; row not activated. | Critical | Unit: registry vs allowlist |

### Exit-gate reminders

- `len(active) == 5` asserted in CI.
- Every active row has `content_sha256` + `effective_date`.
- No raw artifact exists for a non-allowlisted URL.
