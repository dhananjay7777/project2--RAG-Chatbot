# Phase 9 — Freshness Scheduler — Edge Cases

> Architecture: [Architecture.md § Phase 9](../Architecture.md).
> Goal: keep the five Groww pages current via scheduled refresh; never promote a
> broken or incomplete corpus.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| P9-01 | Scheduled re-fetch: 1 of 5 URLs fails | **Do not promote** partial corpus. Keep prior live artifacts; fail the job; no commit. | Critical | Refresh job |
| P9-02 | Hash changed; Fact Card value changed (e.g. TER 1.27→1.30) | Re-extract; flag for human re-verify; block deterministic serving of that key until verified. | Critical | Refresh + Fact Card gate |
| P9-03 | Hash changed; only layout/CSS noise | Reprocess; if Fact Cards unchanged and eval green, allow promote. | Medium | Diff pipeline |
| P9-04 | Eval regresses after refresh | Block promotion; retain previous artifact set. | Critical | Promote gate |
| P9-05 | Groww slug 301 to new path | Fail refresh for that source; page is corpus-breaking — update Architecture, Corpus, allowlist, UI examples in one change. | Critical | Redirect policy |
| P9-06 | Freshness SLA breach on TER ( >7 days since effective/fetch) | Validator 8 → annotate or NO_ANSWER for volatile facts; alert ops. | High | Staleness job |
| P9-07 | Freshness job runs during live traffic and mutates in place | Forbidden. Build new artifacts; commit/swap atomically (Phase 10 deploy consumes read-only). | Critical | Job design |
| P9-08 | Offline snapshot used as “live” refresh by mistake | `validate --live` rejects snapshot / non-promotion_ready manifests. | Critical | Config assert |
| P9-09 | HTTP fetch sparse; headless fallback also fails | Job fails closed; prior committed `data/` retained. | Critical | Refresh job |
| P9-10 | Concurrent scheduled + manual refresh | Serialized via `concurrency.group: corpus-refresh`; no interleaved commits. | High | Actions concurrency |

### Exit-gate reminders

- `corpus-refresh` schedule (or workflow_dispatch) runs green, or fails closed.
- `make refresh` / `python -m ingest.freshness refresh` reproduces the same pipeline locally.
- Registry cardinality == 5 after refresh.
- Refresh writes `data/raw/refresh_report.json` with per-source sha256 deltas.
