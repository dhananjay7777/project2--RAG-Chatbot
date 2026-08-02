# Phase 3 — Indexing & Retrieval — Edge Cases

> Architecture: [Architecture.md § Phase 3](../Architecture.md).
> Goal: return supporting chunks for the named scheme, or return nothing — never the wrong fund.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| P3-01 | Query names Tata Multi Asset; top dense hits are Kotak Multi Asset | Metadata pre-filter on scheme/`source_id` drops Kotak before fusion when scheme is identified. | Critical | Retrieval golden |
| P3-02 | Query says only "multi asset allocation fund" (ambiguous Tata vs Kotak) | Do not guess. Route `CLARIFY` or retrieve both then confidence gate → `NO_ANSWER` / clarify if margin tiny. Prefer clarify asking which AMC. | Critical | Router + retrieval |
| P3-03 | Rank-1 and rank-2 from different schemes with score margin < ε | Confidence gate → `NO_ANSWER` (or CLARIFY if scheme unspecified). | Critical | Unit: margin gate |
| P3-04 | Top rerank score < τ | `NO_ANSWER`. No generative call. | Critical | Unit: τ gate |
| P3-05 | Query uses nickname / abbreviation ("Nippon Value Direct") | Synonym / alias map + BM25 should still hit Nippon source; alias list maintained in config. | High | Retrieval golden |
| P3-06 | Query asks expense ratio but retrieval returns only exit-load chunks | Fact Card path should have short-circuited; if generative, groundedness later fails → safe fallback. Prefer fact-tag filter when intent known. | High | Integration |
| P3-07 | Re-index after one page changes | Only changed `chunk_id`s re-embedded; others untouched; BM25 fully rebuilt or incrementally consistent. | Medium | Index idempotency |
| P3-08 | Stale / superseded `source_id` still in Chroma | Metadata filter `status=active` excludes superseded. | Critical | Unit: filter |
| P3-09 | Empty query / whitespace after sanitize | No retrieval; API returns validation error or CLARIFY. | Medium | API test |
| P3-10 | Query for fund **not** in the five (e.g. "HDFC Flexi Cap expense ratio") | No scheme match → low confidence → `NO_ANSWER`. Never answer from parametric knowledge. | Critical | OOS golden |
| P3-11 | BM25 and dense return disjoint sets | RRF still produces ordered list; if all scores weak, gate fires. | Medium | Unit: RRF |
| P3-12 | Embedding model prefix / instruction omitted on query | Treat as bug; retrieval quality regression test catches recall drop. | Medium | Eval regression |
| P3-13 | Duplicate `chunk_id` upsert | Idempotent overwrite; no duplicate hits in top-k. | High | Index unit |
| P3-14 | Fact Card hit exists but retrieval also run | Architecture: Fact Card short-circuits hybrid retrieval (LLM still called for phrasing on the Fact Card alone). | Medium | Orchestrator test |
| P3-15 | User asks "exit load" with correct scheme; strip removed exit load by mistake | Retrieval miss → `NO_ANSWER`; strip/parse regression should have caught earlier — add canary chunk count per fact_tag. | High | Canary metrics |

### Exit-gate reminders

- Recall@5 ≥ 0.90, MRR ≥ 0.80 on factual golden set.
- All OOS probes → `NO_ANSWER`.
- Documented τ and ε with precision/recall table.
