# Phase 8 — Evaluation & Observability — Edge Cases

> Architecture: [Architecture.md § Phase 8](../Architecture.md).
> Goal: measurable compliance; reproducible scorecards; logs without raw PII.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| P8-01 | Golden factual expected value drifts after Groww update | Refresh golden from verified Fact Cards in same PR as corpus re-ingest; never silently keep stale expected %. | Critical | Eval process |
| P8-02 | Eval cites / expects a sixth URL | Loader rejects golden file. | Critical | Golden schema |
| P8-03 | Compliance metric (citation validity / hallucinated-number rate) regresses | CI **fails** (blocking). Not a warning. | Critical | CI gates |
| P8-04 | Refusal recall drops below 0.95 | CI fails. | Critical | CI gates |
| P8-05 | Refusal precision drops below 0.90 (over-refusal) | CI fails. | High | CI gates |
| P8-06 | Structured log stores raw user query containing PAN | Forbidden. Store query **hash** only; redaction runs before write. | Critical | Log audit |
| P8-07 | Log redaction misses Aadhaar pattern | Second-layer patterns must match Phase 0 policy; audit sample fails CI. | Critical | Log audit fixtures |
| P8-08 | Eval run is non-deterministic (temp≠0, floating retrieval) | Pin seeds/models/temp; fail if scorecard hash differs beyond allowed tolerance. | High | Repro test |
| P8-09 | Adversarial set missing prompt-injection cases | Checklist requires injection / roleplay / "as my advisor" items before Phase 8 exit. | High | Set completeness |
| P8-10 | Performance golden allows digits in output | Assert zero digit characters in PERFORMANCE_REDIRECT answers. | Critical | Performance golden |
| P8-11 | OOS golden missing ELSS lock-in & statement-download | Add both; expect NO_ANSWER. | High | OOS completeness |
| P8-12 | Metrics dashboard shows raw queries | Dashboard uses hashes / aggregates only. | Critical | Privacy review |
| P8-13 | Cost per query exceeds $0.001 budget in eval | Warning initially; investigate retrieval/LLM overuse (Fact Card misses). | Medium | Cost report |
| P8-14 | p95 latency > 3 s on eval harness | Fail latency gate or document infra exception. | High | Latency report |
| P8-15 | Validator failure rate spike for one validator | Alert / CI annotate which validator; do not ship. | High | Observability |
| P8-16 | Golden YAML hand-edited with wrong scheme for expected source_id | Schema cross-check: expected `source_id` must match scheme_name mapping in Corpus.md. | High | Golden lint |
| P8-17 | Eval uses live Groww fetch mid-run | Eval must run against **frozen** local index/artifacts for reproducibility. | Critical | Eval harness config |

### Exit-gate reminders

- `python eval/run_eval.py` reproducible scorecard committed or published as CI artifact.
- Compliance-critical assertions blocking.
- Log sample audit: zero raw PII at rest.
