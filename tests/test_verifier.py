"""Phase 3 gate: the independent verifier catches 8/8 injected classes, and passes correct answers.

Each injection builds *genuinely wrong SQL* (a different query than the correct one), executes it
against the warehouse to get a real wrong number, and asserts the verifier — which recomputes the
truth by an orthogonal path and never sees the correct SQL — both FAILS and names the right class.
"""

from __future__ import annotations

import pytest
from agentsensory import Verdict

from tessera.agent.sql import execute_metric
from tessera.contract import FailureClass
from tessera.ledger import generate
from tessera.ledger.controls import Scope
from tessera.ledger.warehouse import materialize_sqlite
from tessera.semantic import load_metrics
from tessera.verifier import inject_failure, verify

YEAR = 2025

# (failure class, metric, scope) — a reachable injection point for every one of the eight classes.
INJECTIONS = [
    (FailureClass.INTERCOMPANY_DOUBLE_COUNT, "net_revenue", Scope(fiscal_year=YEAR, consolidated=True)),
    (FailureClass.DRAFT_OR_REVERSED, "net_revenue", Scope(fiscal_year=YEAR, consolidated=True)),
    (FailureClass.SIGN_FLIP, "net_revenue", Scope(fiscal_year=YEAR, consolidated=True)),
    (FailureClass.FX_MIXING, "net_revenue", Scope(fiscal_year=YEAR, consolidated=True)),
    (FailureClass.WRONG_STATEMENT_ROLLUP, "net_revenue", Scope(fiscal_year=YEAR, consolidated=True)),
    (FailureClass.WRONG_PERIOD_GRAIN, "net_revenue", Scope(fiscal_year=YEAR, quarter=3, consolidated=True)),
    (FailureClass.ASOF_VS_PTD, "net_revenue", Scope(fiscal_year=YEAR, quarter=3, consolidated=True)),
    (FailureClass.MISSING_ENTITY_FILTER, "net_revenue", Scope(fiscal_year=YEAR, entity_id=4)),
]


@pytest.fixture(scope="module")
def ctx():
    wh = generate()
    metrics = load_metrics()
    conn = materialize_sqlite(wh, ":memory:")
    yield wh, metrics, conn
    conn.close()


def test_all_eight_failure_classes_are_injectable_and_caught(ctx):
    wh, metrics, conn = ctx
    assert {fc for fc, _, _ in INJECTIONS} == {
        fc for fc in FailureClass if fc is not FailureClass.OTHER
    }, "an injection point must exist for every failure class"

    for fc, metric_name, scope in INJECTIONS:
        injected = inject_failure(conn, metrics, metric_name, scope, fc)
        assert injected is not None, f"{fc.value} should be injectable for {metric_name}"
        wrong_value, wrong_sql = injected

        report = verify(
            question=f"({fc.value} probe)", metric_name=metric_name, scope=scope,
            claimed_value=wrong_value, generated_sql=wrong_sql, warehouse=wh, registry=metrics,
        )
        assert report.verdict is Verdict.FAIL, f"{fc.value}: expected FAIL, got {report.verdict}"
        caught = {i.kind for i in report.issues}
        assert fc in caught, f"{fc.value}: not named; caught {[k.value for k in caught]}"


def test_correct_answer_passes_no_false_positive(ctx):
    wh, metrics, conn = ctx
    scope = Scope(fiscal_year=YEAR, consolidated=True)
    for metric_name in ("net_revenue", "operating_expense", "cogs", "cash_balance"):
        value, sql = execute_metric(conn, metrics, metric_name, scope)
        report = verify(
            question=f"correct {metric_name}", metric_name=metric_name, scope=scope,
            claimed_value=value, generated_sql=sql, warehouse=wh, registry=metrics,
        )
        assert report.verdict is Verdict.PASS, f"{metric_name}: {report.summary} / {report.issues}"
        assert not report.issues


def test_quarterly_correct_answer_passes(ctx):
    wh, metrics, conn = ctx
    scope = Scope(fiscal_year=YEAR, quarter=2, consolidated=True)
    value, sql = execute_metric(conn, metrics, "net_revenue", scope)
    report = verify(
        question="Q2 net revenue", metric_name="net_revenue", scope=scope,
        claimed_value=value, generated_sql=sql, warehouse=wh, registry=metrics,
    )
    assert report.verdict is Verdict.PASS


def test_right_number_but_fragile_sql_is_a_warn(ctx):
    """A correct number from SQL missing a required clause is fragile → WARN, not silent PASS."""
    wh, metrics, conn = ctx
    scope = Scope(fiscal_year=YEAR, consolidated=True)
    value, _good_sql = execute_metric(conn, metrics, "net_revenue", scope)
    fragile_sql = "SELECT SUM(credit_func_minor - debit_func_minor) FROM fact_journal_line"
    report = verify(
        question="fragile", metric_name="net_revenue", scope=scope,
        claimed_value=value, generated_sql=fragile_sql, warehouse=wh, registry=metrics,
    )
    assert report.verdict is Verdict.WARN
    assert report.issues


def test_unreconciled_unknown_number_fails_as_other(ctx):
    wh, metrics, conn = ctx
    scope = Scope(fiscal_year=YEAR, consolidated=True)
    from decimal import Decimal

    report = verify(
        question="garbage", metric_name="net_revenue", scope=scope,
        claimed_value=Decimal("999999999.99"), generated_sql="SELECT 1 WHERE status='posted'",
        warehouse=wh, registry=metrics,
    )
    assert report.verdict is Verdict.FAIL
    assert any(i.kind is FailureClass.OTHER for i in report.issues)
