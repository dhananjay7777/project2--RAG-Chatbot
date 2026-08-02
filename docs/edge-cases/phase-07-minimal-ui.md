# Phase 7 — Minimal UI — Edge Cases

> Architecture: [Architecture.md § Phase 7](../Architecture.md).
> Goal: four required UI elements; no PII ingress surfaces; distinct refusal / no-answer states.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| P7-01 | Disclaimer hidden below fold at 1366×768 | Fail UX checklist. Must be visible without scrolling. | Critical | Manual / Playwright screenshot |
| P7-02 | Disclaimer only in footer expander | Fail. Must be persistent header (or always-visible top chrome). | Critical | UI checklist |
| P7-03 | Fewer or more than 3 example chips | Fail. Exactly three: exit-load (Nippon), min-SIP (Samco), advisory refuse (Tata). | High | UI checklist |
| P7-04 | Example chip pre-fills and auto-submits advisory question | OK to submit; must render **refusal** styling, not a normal answer card. | High | E2E |
| P7-05 | Citation rendered as plain text without link | Fail. Must be clickable `<a href>` to exact allowlisted URL. | Critical | E2E |
| P7-06 | Citation points to non-allowlisted href (UI bug) | Client should render only envelope.citation.url from API; no client-side URL rewrite. Add assert. | Critical | E2E |
| P7-07 | Footer "Last updated…" missing in UI though present in API | Fail render contract. | Critical | E2E |
| P7-08 | User pastes PAN in input | Client-side warning; on submit API redacts/refuses. Do not store in logs/UI history as raw PAN. | Critical | E2E + log audit |
| P7-09 | Input > ~500 characters | Block submit with clear message; no API call. | Medium | Unit UI |
| P7-10 | Empty submit | Disable button / show validation; no API call. | Low | Unit UI |
| P7-11 | API returns REFUSAL | Distinct visual state (not identical to factual success). | High | Visual QA |
| P7-12 | API returns NO_ANSWER | Distinct "no answer found" state — does not look like a crash. | High | Visual QA |
| P7-13 | API returns PERFORMANCE_REDIRECT | Show numeral-free message + single link; no charts. | High | E2E |
| P7-14 | Mobile narrow viewport | Disclaimer still visible; chips wrap without hiding disclaimer. | High | Screenshot mobile |
| P7-15 | User requests chat export / email transcript | Feature must not exist. | Critical | Product checklist |
| P7-16 | File upload control present | Must not exist (PII/doc ingress). | Critical | Product checklist |
| P7-17 | Refresh mid-session | In-memory history may clear; no server-side persistence. Acceptable. | Medium | Manual |
| P7-18 | Double-click submit | Debounce / disable while in-flight; one request. | Medium | E2E |
| P7-19 | API 500 / timeout | User-visible error without stack traces or secrets. | High | E2E |
| P7-20 | Welcome message missing | Fail required-elements checklist. | Critical | UI checklist |

### Exit-gate reminders

- Screenshot evidence for desktop + mobile disclaimer visibility.
- Refusal and no-answer states styled and reviewed.
- No accounts, uploads, export, or persisted chat.
