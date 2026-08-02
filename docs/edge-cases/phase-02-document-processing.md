# Phase 2 — Document Processing — Edge Cases

> Architecture: [Architecture.md § Phase 2](../Architecture.md).
> Goal: clean, chunked, PII-free corpus and human-verified Fact Cards; strip returns/holdings/related-funds noise.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| P2-01 | Return calculator / historic returns table present | Section **stripped**; never appears in `chunks.jsonl`. | Critical | Integration: strip audit |
| P2-02 | Category rank / "Returns and rankings" table present | Stripped. Prevents performance leakage and comparative framing. | Critical | Strip audit |
| P2-03 | Holdings table present | Stripped from index (holdings are non-goals). | High | Strip audit |
| P2-04 | "Also manages these schemes" / related-fund link farm | Stripped. Prevents sibling-scheme contamination. | Critical | Strip audit |
| P2-05 | Exit-load historical rules (older dates above current rule) | Fact Card uses **current** rule text only (latest / primary "Exit load" body). Historical lines may be kept in a non-answer metadata note or dropped — never mixed into `value_text`. | Critical | Fact Card review |
| P2-06 | Chunker would split "1% if redeemed" from "within 30 days" | Forbidden. Label+value and threshold+rate stay in one chunk. | Critical | Unit: chunk integrity |
| P2-07 | Tata / Kotak benchmark field blank (`Fund benchmark--`) | Fact Card `benchmark = null`; queries for benchmark → `NO_ANSWER` (or clarify), not invented index names. | Critical | Fact Card + golden |
| P2-08 | Samco page shows scheme AUM ₹78.64 Cr and a larger AMC AUM in About text | `aum` Fact Card = **scheme hero** figure only. | Critical | Fact Card review |
| P2-09 | AMC phone / email in Fund house block | Redact before index; quarantine chunk if unretractable. Never answer with contact PII. | Critical | PII scrub test |
| P2-10 | Sample PAN-like token in page text | Redact to `[REDACTED:PAN]`; do not index raw. | High | PII scrub test |
| P2-11 | Expense ratio appears twice (hero vs body) with same value | One Fact Card; both chunks may exist if needed; values must match or human review flags conflict. | High | Fact extraction |
| P2-12 | Expense ratio conflict (two different % on same page) | Do not auto-pick. Quarantine Fact Card; block promotion until human resolves. | Critical | Fact extraction gate |
| P2-13 | LLM extraction paraphrases exit load | Reject Pass B output; require verbatim substring of chunk. | Critical | Unit: verbatim check |
| P2-14 | Trafilatura drops the Exit Load heading | Fallback BeautifulSoup section scrape by known heading list; fail source if exit_load still missing (all five pages currently have it). | High | Parse regression |
| P2-15 | Boilerplate Groww tax blurb identical across funds | Allowed as `tax_implication_text` Fact Card per scheme; still cite that scheme's URL. | Medium | Fact Card |
| P2-16 | Currency / percent variants (`1.27 %`, `Rs.100`, `INR 100`) | Normalize in text used for BM25 synonyms; preserve display form in `value_text` as on page where possible. | Medium | Normalize unit tests |
| P2-17 | Quarantined chunk accidentally upserted to index | Indexer refuses chunks with `pii_scan != clean` or `quarantined=true`. | Critical | Index precondition |
| P2-18 | Human verification skipped for a Fact Card | `verified_by_human=false` blocks deterministic path for that key; generative path may still run but prefer fail-closed in v1. | High | Fact Card gate |

### Exit-gate reminders

- Strip audit passes on all five pages.
- Every in-scope Fact Card cell is verified or explicit null.
- No return / holdings / related-funds chunks in active set.
