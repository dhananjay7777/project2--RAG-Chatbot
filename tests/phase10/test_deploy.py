"""Phase 10 — deployment contracts (Vercel + Railway)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_deploy_docs_and_configs_exist():
    required = [
        "Dockerfile",
        "railway.toml",
        "vercel.json",
        ".dockerignore",
        "frontend/package.json",
        "frontend/src/app/page.tsx",
        "frontend/src/components/ChatApp.tsx",
        "frontend/src/components/WelcomeView.tsx",
        "frontend/.env.example",
        "docs/Deploy.md",
        "docs/KnownLimitations.md",
        "docs/Disclaimer.md",
        "docs/Corpus.md",
        "eval/artifacts/scorecard.latest.json",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, missing


def test_dockerfile_refuses_dotenv_and_asserts_registry():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert ".env" in text
    assert "load_source_definitions" in text
    assert "uvicorn app.api.main:app" in text
    assert "MF_HEALTH_STRICT=1" in text
    assert "MF_RETRIEVAL_MODE=bm25" in text
    assert "requirements.api.txt" in text
    assert (ROOT / "requirements.api.txt").is_file()
    api_reqs = (ROOT / "requirements.api.txt").read_text(encoding="utf-8").lower()
    assert "sentence-transformers" not in [
        line.strip() for line in api_reqs.splitlines() if line.strip() and not line.strip().startswith("#")
    ]
    assert not any(line.startswith("torch") for line in api_reqs.splitlines() if line.strip())


def test_dockerignore_excludes_dotenv():
    text = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert ".env" in text


def test_vercel_json_points_at_frontend():
    import json

    data = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert data.get("framework") == "nextjs"
    assert "frontend" in data.get("buildCommand", "")


def test_frontend_contains_disclaimer_and_brand():
    import json

    welcome = (ROOT / "frontend" / "src" / "components" / "WelcomeView.tsx").read_text(
        encoding="utf-8"
    )
    assert "DISCLAIMER" in welcome
    assert "Mutual Fund FAQ Assistant" in welcome
    assert "SchemeRail" in welcome or "Covered schemes" in welcome or "Corpus" in welcome
    chat = (ROOT / "frontend" / "src" / "components" / "ChatView.tsx").read_text(
        encoding="utf-8"
    )
    assert "RAG Workspace" in chat
    assert "New Chat" in chat
    assert "SchemeRail" in chat
    rail = (ROOT / "frontend" / "src" / "components" / "SchemeRail.tsx").read_text(
        encoding="utf-8"
    )
    assert "Covered schemes" in rail or "Corpus" in rail
    pkg = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert "next" in pkg.get("dependencies", {})


def test_known_limitations_covers_exit_criteria():
    text = (ROOT / "docs" / "KnownLimitations.md").read_text(encoding="utf-8").lower()
    assert "five" in text and "groww" in text
    assert "elss" in text
    assert "investment advice" in text
    assert "multi-turn" in text or "multi turn" in text


def test_readme_handover_checklist():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Facts-only. No investment advice." in text
    assert "Nippon India Value Fund" in text or "docs/Corpus.md" in text
    assert "Vercel" in text and "Railway" in text
    assert "Phase 10" in text


def test_config_deploy_rate_limit_and_phase():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert cfg["project"]["phase_complete"] == 10
    assert cfg["deploy"]["rate_limit_per_ip_per_hour"] == 30
    assert cfg["deploy"]["frontend"] == "vercel"
    assert cfg["deploy"]["backend"] == "railway"
    assert cfg["corpus"]["expected_source_count"] == 5


def test_health_and_rate_limit_via_fastapi(monkeypatch: pytest.MonkeyPatch):
    from app.api import main as api_main
    from app.ui.presenter import DISCLAIMER

    if api_main.app is None:
        pytest.skip("FastAPI not installed")

    monkeypatch.setenv("MF_HEALTH_STRICT", "0")
    monkeypatch.setenv("MF_RATE_LIMIT_PER_HOUR", "3")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

    # Re-import middleware limits are bound at app creation; exercise limiter unit + health.
    payload = api_main.health()
    assert payload["disclaimer"] == DISCLAIMER
    assert payload["registry_count"] == 5
    assert payload["status"] == "ok"
    assert "schemes" in payload

    from fastapi.testclient import TestClient

    from app.api.rate_limit import PerIpRateLimitMiddleware

    # Mount a fresh mini-app to prove 429 without depending on reloaded globals.
    from fastapi import FastAPI

    probe = FastAPI()
    probe.add_middleware(PerIpRateLimitMiddleware, max_per_hour=2, path="/ask")

    @probe.post("/ask")
    def _ok():
        return {"ok": True}

    client = TestClient(probe)
    assert client.post("/ask").status_code == 200
    assert client.post("/ask").status_code == 200
    limited = client.post("/ask")
    assert limited.status_code == 429
    assert "Rate limit" in limited.json()["detail"]


def test_strict_health_fails_without_index(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from app.api import main as api_main

    if api_main.app is None:
        pytest.skip("FastAPI not installed")

    monkeypatch.setenv("MF_HEALTH_STRICT", "1")
    monkeypatch.setattr(
        "app.api.main.index_ready",
        lambda: (False, ["data/index/bm25.pkl"]),
    )

    from fastapi.testclient import TestClient

    client = TestClient(api_main.app)
    resp = client.get("/health")
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["disclaimer"] == "Facts-only. No investment advice."
    assert detail["index_ready"] is False
