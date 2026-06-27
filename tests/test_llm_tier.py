"""Real-model tiers, tested with a fake client (no network): the model resolves, Tessera builds SQL,
the verifier grades — a mis-resolving cheap model is caught and the cascade escalates."""

from __future__ import annotations

import pytest

from tessera.agent.llm_resolve import resolve_with_llm
from tessera.agent.resolver import ResolutionError
from tessera.ledger import generate
from tessera.ledger.controls import Scope
from tessera.ledger.warehouse import materialize_sqlite
from tessera.routing import CertifiedTier, LLMTier, cascade
from tessera.semantic import load_metrics


class FakeClient:
    """A deterministic stand-in for Ollama/OpenAI — returns a canned completion."""

    def __init__(self, response: str) -> None:
        self.response = response

    def complete(self, prompt: str) -> str:
        return self.response


@pytest.fixture(scope="module")
def ctx():
    wh = generate()
    metrics = load_metrics()
    conn = materialize_sqlite(wh, ":memory:")
    yield wh, metrics, conn
    conn.close()


def test_resolver_parses_clean_json(ctx):
    wh, metrics, _ = ctx
    c = FakeClient('{"metric":"net_revenue","fiscal_year":2025,"quarter":null,"entity":"consolidated"}')
    spec = resolve_with_llm("q", c, metrics, wh.entities)
    assert spec.metric == "net_revenue"
    assert spec.scope.consolidated and spec.scope.fiscal_year == 2025


def test_resolver_tolerates_a_chatty_model(ctx):
    wh, metrics, _ = ctx
    c = FakeClient('Sure! {"metric":"cogs","fiscal_year":2026,"quarter":3,"entity":"BR"} — hope it helps')
    spec = resolve_with_llm("q", c, metrics, wh.entities)
    assert spec.metric == "cogs" and spec.scope.quarter == 3
    assert spec.scope.entity_id is not None and not spec.scope.consolidated


def test_resolver_rejects_unknown_metric(ctx):
    wh, metrics, _ = ctx
    with pytest.raises(ResolutionError):
        resolve_with_llm("q", FakeClient('{"metric":"share_price","fiscal_year":2025}'), metrics, wh.entities)


def test_resolver_rejects_non_json(ctx):
    wh, metrics, _ = ctx
    with pytest.raises(ResolutionError):
        resolve_with_llm("q", FakeClient("I can't help with that."), metrics, wh.entities)


def test_correct_model_is_a_cheap_win(ctx):
    wh, metrics, conn = ctx
    good = FakeClient('{"metric":"net_revenue","fiscal_year":2025,"entity":"consolidated"}')
    r = cascade(question="What was consolidated net revenue in 2025?", metric_name="net_revenue",
                scope=Scope(fiscal_year=2025, consolidated=True), conn=conn, warehouse=wh,
                registry=metrics, tiers=[LLMTier("cheap", 0.0002, good), CertifiedTier()])
    assert r.final_verdict == "pass" and r.accepted_tier == "cheap" and r.escalations == 0


def test_misresolving_model_is_caught_and_escalates(ctx):
    wh, metrics, conn = ctx
    # The cheap model resolves the wrong year; the verifier catches it against the certified intent.
    wrong = FakeClient('{"metric":"net_revenue","fiscal_year":2026,"entity":"consolidated"}')
    r = cascade(question="What was consolidated net revenue in 2025?", metric_name="net_revenue",
                scope=Scope(fiscal_year=2025, consolidated=True), conn=conn, warehouse=wh,
                registry=metrics, tiers=[LLMTier("cheap", 0.0002, wrong), CertifiedTier()])
    assert r.attempts[0].tier == "cheap" and r.attempts[0].verdict == "fail"
    assert r.accepted_tier == "strong" and r.escalations == 1 and r.final_verdict == "pass"


def test_garbage_model_output_escalates_not_crashes(ctx):
    wh, metrics, conn = ctx
    bad = FakeClient("no idea, sorry")
    r = cascade(question="What was consolidated net revenue in 2025?", metric_name="net_revenue",
                scope=Scope(fiscal_year=2025, consolidated=True), conn=conn, warehouse=wh,
                registry=metrics, tiers=[LLMTier("cheap", 0.0002, bad), CertifiedTier()])
    assert r.attempts[0].verdict == "fail"  # resolution failed → recorded, not crashed
    assert r.accepted_tier == "strong" and r.final_verdict == "pass"


def test_openai_and_ollama_clients_construct():
    from tessera.agent.llm import OllamaClient, OpenAIClient

    assert OllamaClient(model="x").model == "x"
    assert OpenAIClient(model="gpt-4o-mini", api_key="sk-test").model == "gpt-4o-mini"
