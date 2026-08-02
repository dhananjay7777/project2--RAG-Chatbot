"""Phase 7 FastAPI smoke tests."""

from __future__ import annotations

import pytest

from app.api.main import AskRequest, ask, health
from app.ui.presenter import DISCLAIMER, max_input_chars


def test_health_reports_disclaimer_and_phase():
    payload = health()
    assert payload["status"] == "ok"
    assert payload["disclaimer"] == DISCLAIMER
    assert payload["phase"]


def test_ask_request_model_rejects_empty_query():
    with pytest.raises(Exception):
        AskRequest.model_validate({"query": ""})


def test_ask_function_returns_envelope_shape():
    payload = ask({"query": "Should I invest in Nippon India Value Fund?"})
    assert payload["route"] == "REFUSAL"
    assert payload["answer"]
    assert payload["citation"]["url"]
    assert payload["footer"].startswith("Last updated from sources:")
    assert "validator_report" in payload


def test_fastapi_app_mounts_when_available():
    from app.api import main as api_main

    if api_main.app is None:
        pytest.skip("FastAPI not installed")
    from fastapi.testclient import TestClient

    client = TestClient(api_main.app)
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["disclaimer"] == DISCLAIMER

    too_long = "x" * (max_input_chars() + 1)
    bad = client.post("/ask", json={"query": too_long})
    assert bad.status_code == 422

    ok = client.post(
        "/ask",
        json={"query": "Should I invest in Tata Multi Asset Allocation Fund?"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["route"] == "REFUSAL"
    assert "groww.in/mutual-funds/" in body["citation"]["url"]
