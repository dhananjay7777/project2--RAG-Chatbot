# Edge Cases Index

> Per-phase edge cases for [`Architecture.md`](../Architecture.md).
> Each file lists scenarios that must not be improvised at implementation time —
> expected behaviour is specified so tests and validators can lock it down.

| Phase | Document |
| --- | --- |
| 0 — Foundations & Compliance Spec | [phase-00-foundations.md](./phase-00-foundations.md) |
| 1 — Corpus Acquisition | [phase-01-corpus-acquisition.md](./phase-01-corpus-acquisition.md) |
| 2 — Document Processing | [phase-02-document-processing.md](./phase-02-document-processing.md) |
| 3 — Indexing & Retrieval | [phase-03-indexing-retrieval.md](./phase-03-indexing-retrieval.md) |
| 4 — Guardrails: Intent Router | [phase-04-intent-router.md](./phase-04-intent-router.md) |
| 5 — Constrained Synthesis | [phase-05-constrained-synthesis.md](./phase-05-constrained-synthesis.md) |
| 6 — Output Validation | [phase-06-output-validation.md](./phase-06-output-validation.md) |
| 7 — Minimal UI | [phase-07-minimal-ui.md](./phase-07-minimal-ui.md) |
| 8 — Evaluation & Observability | [phase-08-evaluation-observability.md](./phase-08-evaluation-observability.md) |
| 9 — Freshness Scheduler | [phase-09-freshness.md](./phase-09-freshness.md) |
| 10 — Deployment & Handover | [phase-10-deployment.md](./phase-10-deployment.md) |

### How to read each file

| Column | Meaning |
| --- | --- |
| ID | Stable test id (`P{phase}-{nn}`) |
| Scenario | What goes wrong or what unusual input arrives |
| Expected behaviour | Exact system response — not aspirational |
| Severity | `Critical` / `High` / `Medium` / `Low` |
| Test hint | Where to assert (unit / integration / golden / manual) |

Severity `Critical` cases are CI-blocking once the phase lands.
