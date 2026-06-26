"""Each failure class, expressed as the *broken* metric/scope variant that produces it.

This module is the hinge of the verifier. One definition per failure class serves two jobs:

- **Diagnose** — when a claimed number does not reconcile, recompute what each broken variant would
  yield; the variant whose value matches the claim *names the mistake* (with both numbers).
- **Inject** — for the demo and the regression suite, build the genuinely-wrong SQL for a class,
  execute it against the warehouse, and get a real wrong number produced by real wrong SQL.

Both jobs share one source of truth, so a class the verifier can catch is exactly a class the suite
can inject — there is no gap between "what we test" and "what we diagnose".
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from ..contract import FailureClass
from ..ledger.controls import Scope, compute_metric
from ..ledger.schema import Warehouse, from_minor
from ..semantic.loader import Metric, PeriodSemantics, Sign

# Class #6 (wrong statement-line rollup): a plausible mis-mapping per metric — folding in an
# adjacent line an analyst might wrongly include.
_WRONG_ROLLUP: dict[str, list[str]] = {
    "net_revenue": ["revenue", "cogs"],
    "operating_expense": ["operating_expenses", "depreciation"],
    "cogs": ["cogs", "operating_expenses"],
    "cash_balance": ["cash", "accounts_receivable"],
}


def _variant(metric: Metric, **changes: object) -> Metric:
    v = metric.model_copy(update=changes)
    v.registry = metric.registry
    return v


def counterfactual_spec(
    registry: dict[str, Metric], metric_name: str, scope: Scope, fc: FailureClass
) -> tuple[Metric, Scope] | None:
    """The (metric, scope) that *commits* failure class ``fc`` — or ``None`` if it cannot apply here.

    Returning ``None`` is meaningful: e.g. intercompany double-count cannot occur on a single-entity
    query, and FX mixing cannot occur on a single-currency one. The verifier only diagnoses classes
    that are actually reachable for the question asked.
    """
    metric = registry[metric_name]
    if metric.components:
        return None  # derived metrics are diagnosed by recompute, not class-level injection

    if fc is FailureClass.INTERCOMPANY_DOUBLE_COUNT:
        if not (scope.consolidated and metric.eliminate_intercompany):
            return None
        return _variant(metric, eliminate_intercompany=False), scope

    if fc is FailureClass.DRAFT_OR_REVERSED:
        statuses = list(dict.fromkeys([*metric.status_filter, "draft", "reversed"]))
        if statuses == metric.status_filter:
            return None
        return _variant(metric, status_filter=statuses), scope

    if fc is FailureClass.SIGN_FLIP:
        flipped = Sign.DEBIT if metric.sign is Sign.CREDIT else Sign.CREDIT
        return _variant(metric, sign=flipped), scope

    if fc is FailureClass.FX_MIXING:
        if metric.currency != "functional":
            return None
        return _variant(metric, currency="transaction"), scope

    if fc is FailureClass.WRONG_PERIOD_GRAIN:
        if scope.quarter is None:
            return None  # no finer grain to confuse with
        return metric, scope.model_copy(update={"quarter": None})  # summed the whole year

    if fc is FailureClass.ASOF_VS_PTD:
        flipped_semantics = (PeriodSemantics.BALANCE if metric.period_semantics is PeriodSemantics.FLOW
                             else PeriodSemantics.FLOW)
        return _variant(metric, period_semantics=flipped_semantics), scope

    if fc is FailureClass.MISSING_ENTITY_FILTER:
        if scope.consolidated or scope.entity_id is None:
            return None
        return metric, scope.model_copy(update={"entity_id": None, "consolidated": False})

    if fc is FailureClass.WRONG_STATEMENT_ROLLUP:
        wrong = _WRONG_ROLLUP.get(metric_name)
        if not wrong or wrong == metric.statement_lines:
            return None
        return _variant(metric, statement_lines=wrong), scope

    return None


def counterfactual_value(
    wh: Warehouse, registry: dict[str, Metric], metric_name: str, scope: Scope, fc: FailureClass
) -> Decimal | None:
    """What the answer would be if failure class ``fc`` were committed — computed orthogonally."""
    spec = counterfactual_spec(registry, metric_name, scope, fc)
    if spec is None:
        return None
    metric_v, scope_v = spec
    return compute_metric(wh, metric_v, scope_v)


def inject_failure(
    conn: sqlite3.Connection, registry: dict[str, Metric], metric_name: str, scope: Scope,
    fc: FailureClass,
) -> tuple[Decimal, str] | None:
    """Build the genuinely-wrong SQL for class ``fc``, run it, and return ``(value, display_sql)``."""
    from ..agent.sql import build_sql, inline_params

    spec = counterfactual_spec(registry, metric_name, scope, fc)
    if spec is None:
        return None
    metric_v, scope_v = spec
    sql, params = build_sql(metric_v, scope_v)
    row = conn.execute(sql, params).fetchone()
    minor = row[0] if row is not None else 0
    return from_minor(int(minor)), inline_params(sql, params)
