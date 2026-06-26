"""Phase 5: the cost cascade escalates only when the verifier rejects the cheap answer."""

from __future__ import annotations

import pytest
from agentsensory import Verdict

from tessera.ledger import generate
from tessera.ledger.controls import Scope
from tessera.ledger.warehouse import materialize_sqlite
from tessera.routing import CertifiedTier, HeuristicTier, cascade, default_tiers, run_benchmark
from tessera.semantic import load_metrics


@pytest.fixture(scope="module")
def ctx():
    wh = generate()
    metrics = load_metrics()
    conn = materialize_sqlite(wh, ":memory:")
    yield wh, metrics, conn
    conn.close()


def test_single_entity_question_is_a_cheap_win(ctx):
    wh, metrics, conn = ctx
    scope = Scope(fiscal_year=2025, entity_id=4)  # ACME Brazil — cheap tier handles it
    result = cascade(question="net revenue for ACME Brazil in 2025", metric_name="net_revenue",
                     scope=scope, conn=conn, warehouse=wh, registry=metrics, tiers=default_tiers())
    assert result.final_verdict == "pass"
    assert result.accepted_tier == "cheap"
    assert result.escalations == 0


def test_consolidated_question_escalates_to_strong(ctx):
    wh, metrics, conn = ctx
    scope = Scope(fiscal_year=2025, consolidated=True)  # cheap tier slips on intercompany here
    result = cascade(question="consolidated net revenue in 2025", metric_name="net_revenue",
                     scope=scope, conn=conn, warehouse=wh, registry=metrics, tiers=default_tiers())
    assert result.final_verdict == "pass"
    assert result.accepted_tier == "strong"
    assert result.escalations == 1
    # The cheap attempt was tried and rejected by the verifier before escalating.
    assert result.attempts[0].tier == "cheap"
    assert result.attempts[0].verdict == Verdict.FAIL.value


def test_escalation_costs_more_than_a_cheap_win_but_stays_correct(ctx):
    wh, metrics, conn = ctx
    cheap = cascade(question="net revenue for ACME US in 2025", metric_name="net_revenue",
                    scope=Scope(fiscal_year=2025, entity_id=2), conn=conn, warehouse=wh,
                    registry=metrics, tiers=default_tiers())
    escalated = cascade(question="consolidated net revenue in 2025", metric_name="net_revenue",
                        scope=Scope(fiscal_year=2025, consolidated=True), conn=conn, warehouse=wh,
                        registry=metrics, tiers=default_tiers())
    assert cheap.total_cost_usd < escalated.total_cost_usd
    assert cheap.final_verdict == "pass" and escalated.final_verdict == "pass"


def test_all_tiers_failing_yields_a_fail_not_a_false_pass(ctx):
    wh, metrics, conn = ctx
    # Two cheap tiers that both commit the same blind spot → nothing passes verification.
    blind = HeuristicTier(name="cheapA", price_per_1k=0.001)
    blind2 = HeuristicTier(name="cheapB", price_per_1k=0.002)
    result = cascade(question="consolidated net revenue in 2025", metric_name="net_revenue",
                     scope=Scope(fiscal_year=2025, consolidated=True), conn=conn, warehouse=wh,
                     registry=metrics, tiers=[blind, blind2])
    assert result.accepted is False
    assert result.final_verdict == Verdict.FAIL.value


def test_strong_only_always_passes_but_is_the_costly_baseline(ctx):
    wh, metrics, conn = ctx
    result = cascade(question="consolidated net revenue in 2025", metric_name="net_revenue",
                     scope=Scope(fiscal_year=2025, consolidated=True), conn=conn, warehouse=wh,
                     registry=metrics, tiers=[CertifiedTier()])
    assert result.final_verdict == "pass"
    assert result.escalations == 0


def test_benchmark_saves_money_with_no_correctness_loss():
    bench = run_benchmark()
    assert bench.n == 6
    assert bench.accuracy_pct == 100.0  # the verifier guarantees every accepted answer is correct
    assert bench.cheap_wins >= 1 and bench.escalations >= 1
    assert bench.total_cost_usd < bench.baseline_cost_usd
    assert bench.pct_saved > 0
