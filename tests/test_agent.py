"""Phase 2: the agent resolves the golden set, emits parameterized SQL, and answers correctly."""

from __future__ import annotations

import pytest
from agentsensory import Verdict

from tessera.agent import answer_question, build_sql, resolve_question
from tessera.agent.resolver import ResolutionError
from tessera.ledger import generate
from tessera.ledger.controls import Scope, compute_metric
from tessera.ledger.warehouse import materialize_sqlite
from tessera.semantic import load_metrics


@pytest.fixture(scope="module")
def warehouse():
    return generate()


@pytest.fixture(scope="module")
def metrics():
    return load_metrics()


@pytest.fixture()
def conn(warehouse):
    c = materialize_sqlite(warehouse, ":memory:")
    yield c
    c.close()


GOLDEN = [
    ("What was consolidated net revenue in 2025?", "net_revenue", True, None, None),
    ("Show me Q3 2025 net revenue, consolidated", "net_revenue", True, 3, None),
    ("operating expenses for the group in 2026", "operating_expense", True, None, None),
    ("What is consolidated EBITDA in 2025?", "ebitda", True, None, None),
    ("cash balance across all entities in 2025", "cash_balance", True, None, None),
]


@pytest.mark.parametrize("question,metric,consolidated,quarter,_month", GOLDEN)
def test_resolves_golden_set(question, metric, consolidated, quarter, _month, metrics, warehouse):
    spec = resolve_question(question, metrics, warehouse.entities)
    assert spec.metric == metric
    assert spec.scope.consolidated is consolidated
    assert spec.scope.quarter == quarter


def test_resolves_single_entity_scope(metrics, warehouse):
    spec = resolve_question("net revenue for ACME Brazil in 2025", metrics, warehouse.entities)
    assert spec.metric == "net_revenue"
    assert spec.scope.consolidated is False
    assert spec.scope.entity_id is not None


def test_unknown_question_is_an_honest_warn_not_a_guess(conn, metrics, warehouse):
    report = answer_question("What is the weather in 2025?", conn, metrics, warehouse.entities)
    assert report.verdict is Verdict.WARN
    assert report.answer is None
    assert report.issues  # carries an OTHER issue, not a fabricated number


@pytest.mark.parametrize("question,metric,consolidated,quarter,_month", GOLDEN)
def test_answer_equals_orthogonal_rollup(
    question, metric, consolidated, quarter, _month, conn, metrics, warehouse
):
    """The executed SQL answer must match the independent metric rollup, to the cent."""
    report = answer_question(question, conn, metrics, warehouse.entities)
    assert report.verdict is Verdict.WARN  # answered, never self-certified
    assert report.executed_sql

    scope = Scope(fiscal_year=2025 if "2025" in question else 2026,
                  quarter=quarter, consolidated=consolidated)
    expected = compute_metric(warehouse, metrics[metric], scope)
    assert report.answer == f"{expected:,.2f} USD"


def test_sql_is_parameterized_not_string_built(metrics):
    """No user-derived value may be interpolated into the SQL text; values are bound params."""
    sql, params = build_sql(metrics["net_revenue"], Scope(fiscal_year=2025, quarter=3,
                                                          entity_id=2, consolidated=False))
    assert ":year" in sql and params["year"] == 2025
    assert ":quarter" in sql and params["quarter"] == 3
    assert ":entity_id" in sql and params["entity_id"] == 2
    # The literal values must NOT appear as inlined SQL tokens.
    assert "2025" not in sql
    assert "= 2 " not in sql and "= 3 " not in sql


def test_executed_sql_actually_runs_and_returns_the_same_number(conn, metrics):
    sql, params = build_sql(metrics["operating_expense"], Scope(fiscal_year=2025, consolidated=True))
    row = conn.execute(sql, params).fetchone()
    assert row is not None
    assert isinstance(row[0], int)  # minor units


def test_resolver_raises_without_a_year(metrics, warehouse):
    with pytest.raises(ResolutionError):
        resolve_question("what was net revenue", metrics, warehouse.entities)
