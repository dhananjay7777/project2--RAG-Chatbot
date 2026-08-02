# Phase 6 — Output Validation — Edge Cases

> Architecture: [Architecture.md § Phase 6](../Architecture.md).
> Goal: no response bypasses the validator chain; repair only for formatting; hard-fail for substance.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| V1 / P6-01 | Answer has 4 sentences; abbreviations like `Rs.` / `i.e.` / `1.5%` | Segmenter must not over-count abbreviations; true 4th sentence → repair once. | High | SentenceCount fixtures |
| V1 / P6-02 | Repair still yields >3 sentences | Cap repairs at 1 → canned safe response. | Critical | Repair cap test |
| V2 / P6-03 | Envelope has 0 citations | Repair / composer fix; if unrestorable → canned. | Critical | Cardinality |
| V2 / P6-04 | Envelope has 2 citations | Fail cardinality; never ship. | Critical | Cardinality |
| V2 / P6-05 | Answer body contains a URL or `groww.in` string | Fail / repair to remove; link only in `citation.url`. | Critical | Cardinality |
| V3 / P6-06 | Citation is `https://groww.in/mutual-funds` (hub) | **Hard fail** — not an exact allowlisted scheme URL. | Critical | Allowlist |
| V3 / P6-07 | Citation is correct URL + `?utm=…` or trailing `/` | Canonicalize then compare; reject if canonical form ∉ allowlist. | Critical | Allowlist |
| V3 / P6-08 | Citation is AMC site / AMFI / SEBI | Hard fail. | Critical | Allowlist |
| V4 / P6-09 | Answer says 1.28% but chunk has 1.27% | Hard fail groundedness → canned. **No repair.** | Critical | Groundedness |
| V4 / P6-10 | Answer mentions "Kotak" but supporting chunks are Tata-only | Hard fail. | Critical | Groundedness |
| V4 / P6-11 | Answer includes a date not in chunks | Hard fail. | High | Groundedness |
| V5 / P6-12 | Contains "best", "should", "recommend", "outperform" | Hard fail → canned. No repair. | Critical | Lexicon |
| V5 / P6-13 | "This fund is better than debt funds" | Hard fail. | Critical | Lexicon |
| V6 / P6-14 | PAN / phone / email appears in answer (e.g. from fund-house bleed) | Hard fail → canned. | Critical | PIIEgress |
| V7 / P6-15 | Missing footer | Repair once to inject `Last updated from sources: <date>`. | High | FooterIntegrity |
| V7 / P6-16 | Footer date ≠ max(effective_date) of supporting sources | Repair to correct date. | High | FooterIntegrity |
| V7 / P6-17 | Footer uses relative text ("yesterday") | Fail / repair to absolute date format. | Medium | FooterIntegrity |
| V8 / P6-18 | Expense ratio source older than 7-day SLA | Annotate staleness or `NO_ANSWER` for volatile facts (prefer NO_ANSWER for TER/NAV if beyond SLA). | High | Staleness |
| V8 / P6-19 | Exit load source within 30-day SLA | Pass. | Medium | Staleness |
| P6-20 | Hard-fail path returns empty body | Canned response must still be a valid `AnswerEnvelope` with allowlisted citation + footer + disclaimer-safe text. | Critical | Canned fixtures |
| P6-21 | Validators run out of order / skipped | Chain is ordered and mandatory; middleware asserts all 8 ran (or early exit after hard fail with report). | Critical | Chain integration |
| P6-22 | REFUSAL / PERFORMANCE_REDIRECT skip groundedness incorrectly | Still run allowlist, cardinality, lexicon, PII, footer; performance route additionally asserts **no digits** in answer. | Critical | Route-specific chain |
| P6-23 | Double-encoded unicode lookalikes in advice words | Normalize before lexicon match (NFKC). | Medium | Lexicon |
| P6-24 | Repair prompt asks model to "fix everything" | Repair directive is single-issue only; second full rewrite forbidden. | High | Repair unit |

### Exit-gate reminders

- Zero constraint violations on full eval set.
- Each validator has malformed-input unit tests.
- Every hard-fail canned path tested.
