"""Phase 7: the shared runtime and the MCP tool handlers (no MCP transport dependency)."""

from __future__ import annotations

import pytest

from tessera.mcp.server import tool_ask, tool_verify
from tessera.runtime import Runtime


@pytest.fixture(scope="module")
def rt():
    runtime = Runtime()
    yield runtime
    runtime.close()


def test_runtime_answers_and_verifies(rt):
    out = rt.ask("What was consolidated net revenue in 2025?")
    assert out["verdict"] == "pass"
    assert out["answer"] == "5,293,985.00 USD"
    assert "is_intercompany = 0" in out["executed_sql"]


def test_runtime_out_of_scope_is_warn(rt):
    out = rt.ask("what is the share price in 2025?")
    assert out["verdict"] == "warn"
    assert out["answer"] is None


def test_runtime_routing_reports_cascade(rt):
    out = rt.ask("consolidated net revenue in 2025", route=True)
    assert out["verdict"] == "pass"
    assert out["routing"]["accepted_tier"] == "strong"
    assert out["routing"]["escalations"] == 1


def test_mcp_ask_then_verify_round_trips(rt):
    asked = tool_ask(rt, "What was consolidated net revenue in 2025?", sign=True)
    assert asked["receipt"] is not None
    verified = tool_verify(rt, asked["receipt"])
    assert verified["valid"] is True
    assert verified["verdict"] == "pass"


def test_mcp_verify_rejects_tampered_receipt(rt):
    asked = tool_ask(rt, "What was consolidated net revenue in 2025?", sign=True)
    asked["receipt"]["payload"]["answer"] = "9,999,999.00 USD"
    assert tool_verify(rt, asked["receipt"])["valid"] is False
