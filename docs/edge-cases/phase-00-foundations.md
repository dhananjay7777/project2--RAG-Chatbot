# Phase 0 — Foundations & Compliance Spec — Edge Cases

> Architecture: [Architecture.md § Phase 0](../Architecture.md).
> Goal: freeze schemas and policy so later phases cannot quietly widen scope.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| P0-01 | `source_allowlist.yaml` uses a domain wildcard (`*.groww.in` or `groww.in/*`) | Schema / policy loader **rejects** the file at startup. Exact five-URL list only. | Critical | Unit: allowlist loader |
| P0-02 | Allowlist has 4 or 6 URLs | CI / registry validation fails. Cardinality must be exactly 5. | Critical | Unit + CI |
| P0-03 | Allowlist URL has trailing slash, `http://`, or different casing vs Corpus.md | Reject or normalize to the canonical HTTPS no-trailing-slash form from Corpus.md; never accept a sixth distinct string as valid. | Critical | Unit: URL canonicalizer |
| P0-04 | Someone adds an AMFI / SEBI / AMC URL "just for refusals" | Policy review fails. Refusal templates may only cite allowlisted URLs. Documented deviation stays in force. | Critical | Policy review checklist |
| P0-05 | `AnswerEnvelope` missing `route`, `citation`, or `footer` field | Pydantic validation fails; API cannot return a partial envelope. | Critical | Schema unit tests |
| P0-06 | `route` set to an unknown value (e.g. `ADVICE`) | Schema rejects. Enum is closed: `FACTUAL \| REFUSAL \| PERFORMANCE_REDIRECT \| NO_ANSWER \| CLARIFY`. | Critical | Schema unit tests |
| P0-07 | `prohibited_lexicon.yaml` empty or missing required terms (`should`, `recommend`, `best`) | Policy integrity test fails before merge. | High | Unit: lexicon presence |
| P0-08 | PII pattern for PAN matches ordinary words / fund codes too aggressively | Tune pattern with negative fixtures (scheme names, ISINs if present, "Direct Growth"). False-positive rate on corpus text must be near zero. | High | Unit: PII fixtures |
| P0-09 | PAN / Aadhaar regex accepts invalid checksum formats without length checks | Patterns require length + charset gates; invalid lengths do not trigger PII route by themselves if clearly not PII — but over-triggering to refuse is preferred over under-triggering. | Medium | Unit: PII fixtures |
| P0-10 | Two policy files disagree (taxonomy says refuse; lexicon omits the trigger word) | Taxonomy is source of truth for routing; lexicon is source of truth for *output* scanning. Document the split; add a consistency test for overlapping advisory stems. | High | Policy consistency test |
| P0-11 | `SourceRecord.doc_type` set to `SID` / `KIM` | Schema rejects. Only `GROWW_SCHEME_PAGE` is valid for this corpus. | High | Schema unit tests |
| P0-12 | `.env.example` accidentally includes a real API key | Pre-commit secret scan fails; `.env` stays gitignored. | Critical | Pre-commit / gitleaks |
| P0-13 | Repo layout ships `ingest/parse/pdf.py` as a live path | Keep stub or delete; HTML-only ingest is the supported path. Calling PDF parser in CI is a fail. | Medium | Ingest smoke test |
| P0-14 | Constraint arbitration table ignored (multi-fund answer with two links drafted in policy templates) | Template linter asserts ≤1 URL placeholder per template. | Critical | Template lint |
| P0-15 | Refusal template includes AMFI educational URL | Template lint fails against allowlist. | Critical | Template lint |

### Exit-gate reminders

- Policy files committed and reviewed.
- Schemas importable; empty pytest suite green.
- Edge cases above have corresponding unit stubs even if behaviour is "reject config".
