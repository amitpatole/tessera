"""Build and execute parameterized SQL for a certified metric + scope.

Security posture (see CLAUDE.md): the query *structure* is derived entirely from the trusted metric
definition and the fixed schema — never from user text. Only user-derived *values* (year, quarter,
entity id, the status/line whitelists) are bound as named parameters. The connection is opened
read-only by the caller. There is no string interpolation of untrusted input into SQL.
"""

from __future__ import annotations

import re
import sqlite3
from decimal import Decimal

from ..ledger.controls import Scope
from ..ledger.schema import from_minor
from ..semantic.loader import Metric, PeriodSemantics, Sign

_BASE_FROM = (
    "FROM fact_journal_line l "
    "JOIN fact_journal_entry e ON e.entry_id = l.entry_id "
    "JOIN dim_account a ON a.account_id = l.account_id "
    "JOIN dim_period p ON p.period_id = e.period_id"
)


def build_sql(metric: Metric, scope: Scope) -> tuple[str, dict[str, object]]:
    """Return ``(sql, params)`` for a **base** metric. Raises on a derived metric."""
    if metric.components:
        raise ValueError(f"{metric.name} is a derived metric; use execute_metric()")

    func = metric.currency == "functional"
    debit_col = "l.debit_func_minor" if func else "l.debit_txn_minor"
    credit_col = "l.credit_func_minor" if func else "l.credit_txn_minor"
    value_expr = (
        f"({credit_col} - {debit_col})" if metric.sign is Sign.CREDIT
        else f"({debit_col} - {credit_col})"
    )

    params: dict[str, object] = {}
    where: list[str] = []

    # Account selection — from the trusted metric, bound as parameters anyway.
    if metric.account_codes:
        keys = [f":ac{i}" for i in range(len(metric.account_codes))]
        where.append(f"a.code IN ({','.join(keys)})")
        params.update({f"ac{i}": code for i, code in enumerate(metric.account_codes)})
    else:
        keys = [f":sl{i}" for i in range(len(metric.statement_lines))]
        where.append(f"a.statement_line IN ({','.join(keys)})")
        params.update({f"sl{i}": line for i, line in enumerate(metric.statement_lines)})

    # Status filter.
    st_keys = [f":st{i}" for i in range(len(metric.status_filter))]
    where.append(f"e.status IN ({','.join(st_keys)})")
    params.update({f"st{i}": s for i, s in enumerate(metric.status_filter)})

    # Intercompany elimination (only on a consolidated view).
    if scope.consolidated and metric.eliminate_intercompany:
        where.append("e.is_intercompany = 0")

    # Entity scope.
    if not scope.consolidated and scope.entity_id is not None:
        where.append("e.entity_id = :entity_id")
        params["entity_id"] = scope.entity_id

    # Period semantics.
    if metric.period_semantics is PeriodSemantics.BALANCE:
        where.append("(p.fiscal_year * 12 + p.month) <= :asof")
        params["asof"] = scope.asof_ordinal()
    else:
        where.append("p.fiscal_year = :year")
        params["year"] = scope.fiscal_year
        if scope.quarter is not None:
            where.append("p.quarter = :quarter")
            params["quarter"] = scope.quarter
        if scope.month is not None:
            where.append("p.month = :month")
            params["month"] = scope.month

    sql = (
        f"SELECT COALESCE(SUM({value_expr}), 0) AS minor\n{_BASE_FROM}\n"
        f"WHERE {' AND '.join(where)}"
    )
    return sql, params


def _inline_for_display(sql: str, params: dict[str, object]) -> str:
    """A copy of the SQL with params substituted — for *display only*, never executed."""
    out = sql
    for key in sorted(params, key=len, reverse=True):
        value = params[key]
        literal = str(value) if isinstance(value, int) else f"'{value}'"
        out = re.sub(rf":{key}\b", literal, out)
    return out


def execute_metric(
    conn: sqlite3.Connection, registry: dict[str, Metric], metric_name: str, scope: Scope
) -> tuple[Decimal, str]:
    """Execute a metric (base or derived) against the warehouse. Returns ``(value, display_sql)``."""
    metric = registry[metric_name]
    if metric.components:
        total = Decimal("0.00")
        parts: list[str] = []
        for comp in metric.components:
            value, sql = execute_metric(conn, registry, comp.metric, scope)
            total += comp.coefficient * value
            sign = "+" if comp.coefficient >= 0 else "-"
            parts.append(f"-- {sign}{abs(comp.coefficient)} * {comp.metric}\n{sql}")
        return total.quantize(Decimal("0.01")), "\n\n".join(parts)

    sql, params = build_sql(metric, scope)
    row = conn.execute(sql, params).fetchone()
    minor = row[0] if row is not None else 0
    return from_minor(int(minor)), _inline_for_display(sql, params)
