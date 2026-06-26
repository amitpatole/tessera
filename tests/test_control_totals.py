"""Control totals: the orthogonal rollup is correct, agrees with SQL, and is deterministic."""

from __future__ import annotations

from decimal import Decimal

from tessera.ledger import generate
from tessera.ledger.controls import Scope, compute_metric, standard_control_totals
from tessera.ledger.schema import from_minor
from tessera.ledger.warehouse import materialize_sqlite
from tessera.semantic import load_metrics

YEAR = 2025


def test_flow_metric_is_additive_over_quarters() -> None:
    wh = generate()
    nr = load_metrics()["net_revenue"]
    full_year = compute_metric(wh, nr, Scope(fiscal_year=YEAR, consolidated=True))
    by_quarter = sum(
        (compute_metric(wh, nr, Scope(fiscal_year=YEAR, quarter=q, consolidated=True))
         for q in (1, 2, 3, 4)),
        Decimal("0.00"),
    )
    assert full_year == by_quarter


def test_intercompany_elimination_moves_the_consolidated_number() -> None:
    """The core of failure class #4: eliminating intercompany must change net revenue."""
    wh = generate()
    nr = load_metrics()["net_revenue"]
    nr_naive = nr.model_copy(update={"eliminate_intercompany": False})

    eliminated = compute_metric(wh, nr, Scope(fiscal_year=YEAR, consolidated=True))
    naive = compute_metric(wh, nr_naive, Scope(fiscal_year=YEAR, consolidated=True))

    # Independently total the intercompany revenue that elimination is supposed to remove.
    accounts = wh.account_by_id()
    entries = wh.entry_by_id()
    periods = wh.period_by_id()
    intercompany_rev = Decimal("0.00")
    for line in wh.lines:
        entry = entries[line.entry_id]
        if (entry.is_intercompany and entry.status.value == "posted"
                and accounts[line.account_id].statement_line == "revenue"
                and periods[entry.period_id].fiscal_year == YEAR):
            intercompany_rev += line.credit_func - line.debit_func

    assert intercompany_rev > 0, "no intercompany revenue in the data — class #4 untestable"
    assert naive > eliminated, "naive (un-eliminated) revenue should be inflated"
    assert naive - eliminated == intercompany_rev


def test_orthogonal_rollup_agrees_with_direct_sql() -> None:
    """The verifier's premise: the Python rollup and a SQL SUM must reconcile."""
    wh = generate()
    nr = load_metrics()["net_revenue"]
    entity = wh.entities[1]  # a single entity → no consolidation/elimination in play
    scope = Scope(fiscal_year=YEAR, entity_id=entity.entity_id)
    python_value = compute_metric(wh, nr, scope)

    conn = materialize_sqlite(wh, ":memory:")
    try:
        row = conn.execute(
            """
            SELECT SUM(l.credit_func_minor - l.debit_func_minor) AS v
            FROM fact_journal_line l
            JOIN fact_journal_entry e ON e.entry_id = l.entry_id
            JOIN dim_account a ON a.account_id = l.account_id
            JOIN dim_period p ON p.period_id = e.period_id
            WHERE e.status = 'posted' AND a.statement_line = 'revenue'
              AND e.entity_id = ? AND p.fiscal_year = ?
            """,
            (entity.entity_id, YEAR),
        ).fetchone()
        sql_value = from_minor(row["v"])
    finally:
        conn.close()

    assert python_value == sql_value


def test_control_totals_are_deterministic_and_self_consistent() -> None:
    wh = generate()
    metrics = load_metrics()
    totals_a = standard_control_totals(wh, metrics)
    totals_b = standard_control_totals(wh, metrics)
    assert [t.model_dump() for t in totals_a] == [t.model_dump() for t in totals_b]
    # Every stored total recomputes to itself.
    for t in totals_a:
        assert compute_metric(wh, metrics[t.metric], t.scope) == t.value
