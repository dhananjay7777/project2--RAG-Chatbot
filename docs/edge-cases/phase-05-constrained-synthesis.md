# Phase 5 — Constrained Synthesis — Edge Cases

> Architecture: [Architecture.md § Phase 5](../Architecture.md).
> Goal: phrase retrieved facts only; ≤3 sentences; no advice; citation/footer chosen by code.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| P5-01 | Factual NAV / expense_ratio question | Retrieve chunks (+ optional Fact Card context) → **always call Groq**; never return scraped/`value_text` template as the online answer. If LLM unavailable → `NO_ANSWER`. | Critical | Orchestrator unit |
| P5-02 | Context lacks the asked fact | Model emits exactly `INSUFFICIENT_CONTEXT` → composer maps to `NO_ANSWER`. | Critical | Generative probes |
| P5-03 | Model invents benchmark for Tata (null in corpus) | Groundedness fail later; synthesis should have returned insufficient. Add probe. | Critical | Adversarial generative |
| P5-04 | Model copies return % from a chunk that escaped strip | Should not happen if Phase 2 correct; if chunk present, router should have been PERFORMANCE. Synthesis prompt forbids returns; validator + strip are backstops. | Critical | Integration canary |
| P5-05 | Model outputs 4+ sentences | Validator 1 repair once; if still failing → canned safe response. Prefer prompt that targets 1 sentence. | High | Validator + repair |
| P5-06 | Model embeds a markdown link / raw URL in answer body | Strip or repair; citation lives only in envelope. | High | Validator 2 |
| P5-07 | Model chooses wrong scheme name while chunks are Nippon | Groundedness / entity check fails → hard fail → canned. | Critical | Groundedness |
| P5-08 | Model rounds 1.27% → 1.3% | Forbidden; must copy exact numeric strings. Groundedness fails on "1.3". | Critical | Numeric probes |
| P5-09 | Model computes "SIP ₹100 × 12 = ₹1200" | Forbidden arithmetic → hard fail. | Critical | Adversarial |
| P5-10 | Model adds "you should consider…" | Advice lexicon → hard fail → canned refusal-style safe answer. | Critical | Lexicon |
| P5-11 | Temperature accidentally non-zero | Config assert `temperature==0` at call site. | High | Unit: client config |
| P5-12 | Model outputs citation / footer itself with wrong date | Composer **overwrites**; ignores model citation. | Critical | Composer unit |
| P5-13 | Top-4 chunks include two schemes despite filter bug | Synthesis must not merge; if claim spans both → insufficient or single-scheme only. Prefer fail to `NO_ANSWER`. | Critical | Integration |
| P5-14 | Exit load text is long (>3 sentences if quoted fully) | Summarize narrowly **without changing meaning**, or use deterministic Fact Card `value_text` (preferred). Truncation that drops threshold clause is invalid. | High | Exit-load fixtures |
| P5-15 | Latency spike / LLM timeout on Fact Card path | Fall back to deterministic Fact Card template (still FACTUAL). On retrieval generative path: graceful `NO_ANSWER` or retry once; never partial unguarded text to UI. | High | Integration timeout |
| P5-16 | Prompt injection inside retrieved chunk text | Unlikely on Groww; still: system rules outrank context; validators post-hoc. | Medium | Adversarial chunk fixture |
| P5-17 | `INSUFFICIENT_CONTEXT` with trailing commentary | Treat any payload ≠ exact sentinel as normal text and validate; prefer exact-match detection with strip. | Medium | Unit: sentinel parse |

### Exit-gate reminders

- 100% generative factual answers pass groundedness.
- Insufficient-context probes all fire.
- p95 generation latency < 2 s (excluding cold start).
