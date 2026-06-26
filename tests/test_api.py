"""Phase 6: the REST API serves the verified pipeline, and the bind/auth posture is fail-closed."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tessera.api import create_app
from tessera.api.security import BindSecurityError


@pytest.fixture()
def client():
    with TestClient(create_app(host="127.0.0.1")) as c:  # loopback → zero-config
        yield c


def test_health_is_open_and_reports_the_dataset(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["entries"] > 500


def test_ask_returns_a_verified_pass(client):
    r = client.post("/ask", json={"question": "What was consolidated net revenue in 2025?"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "pass"
    assert body["answer"] == "5,293,985.00 USD"
    assert "is_intercompany = 0" in body["executed_sql"]


def test_ask_out_of_scope_is_warn_not_a_guess(client):
    r = client.post("/ask", json={"question": "what is the share price in 2025?"})
    assert r.status_code == 200
    assert r.json()["verdict"] == "warn"
    assert r.json()["answer"] is None


def test_ask_with_routing_reports_the_cascade(client):
    r = client.post("/ask", json={"question": "What was consolidated net revenue in 2025?",
                                   "route": True})
    body = r.json()
    assert body["verdict"] == "pass"
    assert body["routing"]["accepted_tier"] == "strong"
    assert body["routing"]["escalations"] == 1


def test_ask_then_verify_the_signed_receipt_round_trips(client):
    asked = client.post("/ask", json={"question": "What was consolidated net revenue in 2025?",
                                       "sign": True}).json()
    assert asked["receipt"] is not None
    verified = client.post("/verify", json={"receipt": asked["receipt"]}).json()
    assert verified["valid"] is True
    assert verified["verdict"] == "pass"


def test_verify_rejects_a_tampered_receipt(client):
    asked = client.post("/ask", json={"question": "What was consolidated net revenue in 2025?",
                                       "sign": True}).json()
    asked["receipt"]["payload"]["answer"] = "9,999,999.00 USD"
    verified = client.post("/verify", json={"receipt": asked["receipt"]}).json()
    assert verified["valid"] is False


def test_oversized_body_is_rejected(client):
    big = "x" * 20_000
    r = client.post("/ask", json={"question": big})
    # Either the body-cap middleware (413) or pydantic max_length (422) refuses it.
    assert r.status_code in (413, 422)


# ---- bind/auth posture ----------------------------------------------------------------------------


def test_non_loopback_bind_without_token_fails_closed():
    with pytest.raises(BindSecurityError):
        create_app(host="0.0.0.0", api_token=None)


def test_non_loopback_bind_with_token_requires_bearer():
    app = create_app(host="0.0.0.0", api_token="s3cret-token")
    with TestClient(app) as c:
        assert c.post("/ask", json={"question": "consolidated net revenue in 2025"}).status_code == 401
        ok = c.post("/ask", headers={"Authorization": "Bearer s3cret-token"},
                    json={"question": "What was consolidated net revenue in 2025?"})
        assert ok.status_code == 200
        assert c.post("/ask", headers={"Authorization": "Bearer wrong"},
                      json={"question": "x"}).status_code == 401


def test_health_stays_open_even_with_auth():
    app = create_app(host="0.0.0.0", api_token="t")
    with TestClient(app) as c:
        assert c.get("/health").status_code == 200  # health needs no auth (liveness probe)
