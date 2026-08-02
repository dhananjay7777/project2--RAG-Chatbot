"""Run Phase 9 with ``python -m ingest.freshness``."""

from __future__ import annotations

import logging

from ingest.freshness.cli import main

try:
    raise SystemExit(main())
except Exception as exc:  # noqa: BLE001 — CLI fail-closed
    logging.basicConfig(level=logging.ERROR)
    logging.getLogger(__name__).error("%s", exc)
    raise SystemExit(1) from exc
