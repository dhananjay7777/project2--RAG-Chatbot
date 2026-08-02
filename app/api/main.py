"""Phase 7/10 API: GET /health and POST /ask.

`health()` stays a plain function so scaffold tests can import this module
without FastAPI installed.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from pydantic import BaseModel, Field

from app.api.readiness import (
    cors_origins,
    deploy_rate_limit_per_hour,
    index_ready,
    registry_cardinality,
)
from app.ui.presenter import DISCLAIMER, corpus_scheme_names, example_questions, max_input_chars
from core.settings import load_settings

logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1)
    last_source_id: str | None = None


def health() -> dict[str, Any]:
    settings = load_settings()
    phase = str(settings.get("project", {}).get("phase_complete", 7))
    ready, missing = index_ready()
    try:
        count = registry_cardinality()
    except Exception:  # noqa: BLE001 — health must stay cheap
        count = -1
    # Registry cardinality is the hard deploy contract; index readiness is separate
    # so local/scaffold tests can import health() without built artifacts.
    status = "ok" if count == 5 else "degraded"
    return {
        "status": status,
        "phase": phase,
        "disclaimer": DISCLAIMER,
        "registry_count": count,
        "index_ready": ready,
        "missing_artifacts": missing,
        "schemes": corpus_scheme_names(),
        "example_questions": example_questions(),
        "rate_limit_per_ip_per_hour": deploy_rate_limit_per_hour(),
    }


def ask(payload: dict[str, Any]) -> dict[str, Any]:
    """Answer a query and return the AnswerEnvelope as a JSON-ready dict."""

    from core.ask import ask as run_ask

    request = AskRequest.model_validate(payload)
    envelope = run_ask(request.query, last_source_id=request.last_source_id)
    return envelope.model_dump(mode="json")


try:  # pragma: no cover - exercised only when FastAPI is installed
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.rate_limit import PerIpRateLimitMiddleware

    def _warm_retrieval_models() -> None:
        """Load embedding + reranker weights once so the first /ask is not a multi-minute stall."""
        try:
            from sentence_transformers import CrossEncoder, SentenceTransformer

            SentenceTransformer("BAAI/bge-small-en-v1.5")
            CrossEncoder("BAAI/bge-reranker-base")
            logger.info("retrieval models warmed")
        except Exception:  # noqa: BLE001 — startup should not crash the API
            logger.exception("retrieval model warm-up failed")

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        _warm_retrieval_models()
        yield

    app = FastAPI(
        title="Mutual Fund FAQ Assistant",
        description=DISCLAIMER,
        version="1.0.0",
        lifespan=_lifespan,
    )

    origins = cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(
        PerIpRateLimitMiddleware,
        max_per_hour=deploy_rate_limit_per_hour(),
        path="/ask",
    )

    @app.get("/health")
    def _health() -> dict[str, Any]:
        payload = health()
        # Railway sets MF_HEALTH_STRICT=1 so cold starts without an index fail closed.
        strict = os.getenv("MF_HEALTH_STRICT", "0").strip() not in {"0", "false", "False"}
        if strict and (not payload.get("index_ready") or payload.get("registry_count") != 5):
            raise HTTPException(status_code=503, detail=payload)
        return payload

    @app.post("/ask")
    def _ask(request: AskRequest) -> dict[str, Any]:
        query = request.query.strip()
        limit = max_input_chars()
        if not query:
            raise HTTPException(status_code=422, detail="query must not be empty")
        if len(request.query) > limit:
            raise HTTPException(
                status_code=422,
                detail=f"query exceeds {limit} characters",
            )
        ready, missing = index_ready()
        if not ready:
            raise HTTPException(
                status_code=503,
                detail=f"assistant unavailable (missing index artifacts: {missing})",
            )
        try:
            return ask(request.model_dump())
        except Exception:  # noqa: BLE001 — no stack traces across the API boundary
            logger.exception("ask failed")
            raise HTTPException(status_code=503, detail="assistant unavailable") from None

except ImportError:  # pragma: no cover
    app = None
