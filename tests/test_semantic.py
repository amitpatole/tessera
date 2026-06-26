"""The semantic layer loads, validates, and covers the chart of accounts."""

from __future__ import annotations

from tessera.ledger.schema import CHART_OF_ACCOUNTS
from tessera.semantic import PeriodSemantics, Sign, load_metrics


def test_metrics_load_and_validate() -> None:
    metrics = load_metrics()
    assert {"net_revenue", "cogs", "operating_expense", "ebitda", "cash_balance"} <= set(metrics)


def test_net_revenue_contract_is_what_an_auditor_expects() -> None:
    nr = load_metrics()["net_revenue"]
    assert nr.sign is Sign.CREDIT
    assert nr.eliminate_intercompany is True
    assert nr.period_semantics is PeriodSemantics.FLOW
    assert nr.status_filter == ["posted"]


def test_cash_balance_is_a_point_in_time_balance() -> None:
    assert load_metrics()["cash_balance"].period_semantics is PeriodSemantics.BALANCE


def test_derived_metric_resolves_its_components() -> None:
    metrics = load_metrics()
    ebitda = metrics["ebitda"]
    assert {c.metric for c in ebitda.components} == {"net_revenue", "cogs", "operating_expense"}
    assert ebitda.registry is not None and "net_revenue" in ebitda.registry


def test_every_account_statement_line_is_referenced_by_some_metric_or_known() -> None:
    # Every statement line an account maps to should be a real, intentional bucket (no typos).
    known_lines = {
        "cash", "accounts_receivable", "intercompany_assets", "ppe",
        "accounts_payable", "intercompany_liabilities", "debt", "equity",
        "revenue", "cogs", "operating_expenses", "depreciation", "interest_expense",
    }
    for account in CHART_OF_ACCOUNTS:
        assert account.statement_line in known_lines, account.statement_line
