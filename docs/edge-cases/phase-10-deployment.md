# Phase 10 — Deployment & Handover — Edge Cases

> Architecture: [Architecture.md § Phase 10](../Architecture.md).
> Goal: ship a reproducible demo; never advertise a broken public URL; docs complete.

| ID | Scenario | Expected behaviour | Severity | Test hint |
| --- | --- | --- | --- | --- |
| P10-01 | Secrets in image / repo | Env-only secrets; image build fails if `.env` copied. | Critical | Docker review |
| P10-02 | Cold start without index files | Container / host must ship read-only index from Phase 9 artifacts; missing index → healthcheck fail (`MF_HEALTH_STRICT=1`). | Critical | Healthcheck |
| P10-03 | Rate limit exceeded (per-IP) | 429 with safe message; no stack trace. | Medium | API test |
| P10-04 | README missing five schemes / setup / disclaimer | Handover checklist fails. | High | Docs checklist |
| P10-05 | KnownLimitations omits "exactly five Groww URLs" / no ELSS | Docs checklist fails. | High | Docs checklist |
| P10-06 | Multiple instances write to shared mutable index | Deploy read-only index; Phase 9 refresh produces new artifacts, then Railway redeploy swaps image. | High | Deploy design review |
| P10-07 | Rollback needed | Previous Railway deployment retained; one-step rollback. | High | Runbook |
| P10-08 | Public URL down / healthcheck fail | Alert; do not advertise demo until green. | High | Monitoring |
| P10-09 | Disclaimer missing from deployed UI build | Smoke test after deploy asserts disclaimer string. | Critical | Smoke |
| P10-10 | Cost runaway from bot traffic | Per-IP rate limit + optional global daily LLM budget kill switch. | High | Ops config |
| P10-11 | Deploy uses stale corpus while Phase 9 failed | Prefer last good promoted artifacts; surface freshness footer; do not silent-skip SLA. | High | Ops + Validator 8 |
| P10-12 | Vercel UI calls wrong API / CORS blocked | `MF_API_URL` + Railway `CORS_ORIGINS` must match; UI surfaces a safe offline message. | High | Deploy smoke |

### Exit-gate reminders

- Public URL reachable; smoke + disclaimer assert green.
- README enables clean-clone reproduction.
- Registry cardinality == 5 in deployed config.
- Deploy target: **Vercel frontend + Railway FastAPI** ([Deploy.md](../Deploy.md)).
