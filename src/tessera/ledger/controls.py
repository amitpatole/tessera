"""Invariants and control totals — the *independent* arithmetic the verifier trusts.

Nothing here ever looks at a model-generated SQL string. These functions roll the answer up directly
from ``fact_journal_line`` via the certified metric definition, which is exactly what makes the later
runtime verdict orthogonal: a generated query is judged against numbers computed by a different path.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from ..semantic.loader import Metric, PeriodSemantics, Sign
from .schema import Account, AccountType, EntryStatus, NormalBalance, Warehouse


class CheckResult(BaseModel):
    name: str
    ok: bool
    detail: str = ""


# --------------------------------------------------------------------------------------------------
# Scope — which slice of the ledger a question is about.
# --------------------------------------------------------------------------------------------------


class Scope(BaseModel):
    fiscal_year: int
    quarter: int | None = None
    month: int | None = None
    entity_id: int | None = None
    consolidated: bool = False

    def asof_ordinal(self) -> int:
        """Period ordinal (year*12 + month) at the *end* of this scope, for as-of balances."""
        month = self.month if self.month is not None else (self.quarter * 3 if self.quarter else 12)
        return self.fiscal_year * 12 + month


def _period_ordinal(fiscal_year: int, month: int) -> int:
    return fiscal_year * 12 + month


# --------------------------------------------------------------------------------------------------
# Invariants — the Phase 1 gate. If any of these fail, the generated books are not real books.
# --------------------------------------------------------------------------------------------------


def _natural(account: Account, debit: Decimal, credit: Decimal) -> Decimal:
    """Signed amount in the account's natural direction (positive = a normal increase)."""
    if account.normal_balance is NormalBalance.DEBIT:
        return debit - credit
    return credit - debit


def check_invariants(wh: Warehouse) -> list[CheckResult]:
    """Run every structural invariant; the books are valid iff all results are ``ok``."""
    results: list[CheckResult] = []
    accounts = wh.account_by_id()
    entries = wh.entry_by_id()

    # 1. Every account maps to a statement line, with a normal balance consistent with its type.
    debit_types = {AccountType.ASSET, AccountType.EXPENSE}
    bad_map = [
        a.code for a in wh.accounts
        if not a.statement_line
        or (a.normal_balance is NormalBalance.DEBIT) != (a.account_type in debit_types)
    ]
    results.append(CheckResult(
        name="account_mapping",
        ok=not bad_map,
        detail="all accounts map to a statement line with a consistent normal balance"
        if not bad_map else f"inconsistent accounts: {bad_map}",
    ))

    # 2. Every journal entry is internally balanced (Σ debit == Σ credit) in transaction currency.
    per_entry: dict[int, tuple[Decimal, Decimal]] = {}
    for line in wh.lines:
        d, c = per_entry.get(line.entry_id, (Decimal("0"), Decimal("0")))
        per_entry[line.entry_id] = (d + line.debit_txn, c + line.credit_txn)
    unbalanced = [eid for eid, (d, c) in per_entry.items() if d != c]
    results.append(CheckResult(
        name="entry_balanced",
        ok=not unbalanced,
        detail=f"all {len(per_entry)} entries balance"
        if not unbalanced else f"unbalanced entries: {unbalanced[:10]}",
    ))

    # 3. Trial balance: posted Σ debit == Σ credit in functional currency, per entity and consolidated.
    by_entity: dict[int, tuple[Decimal, Decimal]] = {}
    total_d = total_c = Decimal("0")
    for line in wh.lines:
        entry = entries[line.entry_id]
        if entry.status is not EntryStatus.POSTED:
            continue
        d, c = by_entity.get(entry.entity_id, (Decimal("0"), Decimal("0")))
        by_entity[entry.entity_id] = (d + line.debit_func, c + line.credit_func)
        total_d += line.debit_func
        total_c += line.credit_func
    entity_off = {eid: str(d - c) for eid, (d, c) in by_entity.items() if d != c}
    results.append(CheckResult(
        name="trial_balance_per_entity",
        ok=not entity_off,
        detail="posted trial balance balances for every entity"
        if not entity_off else f"out of balance: {entity_off}",
    ))
    results.append(CheckResult(
        name="trial_balance_consolidated",
        ok=total_d == total_c,
        detail=f"consolidated posted debits == credits == {total_d}"
        if total_d == total_c else f"off by {total_d - total_c}",
    ))

    # 4. Statements roll up: Assets == Liabilities + Equity + (Revenue - Expense), posted, functional.
    buckets = {t: Decimal("0") for t in AccountType}
    for line in wh.lines:
        entry = entries[line.entry_id]
        if entry.status is not EntryStatus.POSTED:
            continue
        acct = accounts[line.account_id]
        buckets[acct.account_type] += _natural(acct, line.debit_func, line.credit_func)
    net_income = buckets[AccountType.REVENUE] - buckets[AccountType.EXPENSE]
    residual = buckets[AccountType.ASSET] - (
        buckets[AccountType.LIABILITY] + buckets[AccountType.EQUITY] + net_income
    )
    results.append(CheckResult(
        name="accounting_equation",
        ok=residual == 0,
        detail="Assets == Liabilities + Equity + Net income (statements roll up)"
        if residual == 0 else f"equation residual {residual}",
    ))

    return results


def invariants_hold(wh: Warehouse) -> bool:
    return all(r.ok for r in check_invariants(wh))


# --------------------------------------------------------------------------------------------------
# Metric computation — the orthogonal rollup the verifier compares a generated query against.
# --------------------------------------------------------------------------------------------------


def _entities_in_scope(wh: Warehouse, scope: Scope) -> set[int]:
    if scope.consolidated:
        return {e.entity_id for e in wh.entities}
    if scope.entity_id is not None:
        return {scope.entity_id}
    return {e.entity_id for e in wh.entities}


def compute_metric(wh: Warehouse, metric: Metric, scope: Scope) -> Decimal:
    """Compute a certified metric for a scope by direct rollup — the verifier's ground truth.

    Derived metrics (``components``) recurse and combine; base metrics select accounts by statement
    line / code, apply the status filter, the period semantics (flow vs as-of balance), the entity
    scope, optional intercompany elimination on consolidation, and the metric's natural sign.
    """
    if metric.components:
        total = Decimal("0.00")
        registry = metric.registry or {}
        for comp in metric.components:
            sub = registry[comp.metric]
            total += comp.coefficient * compute_metric(wh, sub, scope)
        return total.quantize(Decimal("0.01"))

    entries = wh.entry_by_id()
    periods = wh.period_by_id()
    in_scope = _entities_in_scope(wh, scope)
    selected = {
        a.account_id for a in wh.accounts
        if (not metric.statement_lines or a.statement_line in metric.statement_lines)
        and (not metric.account_codes or a.code in metric.account_codes)
    }
    statuses = {EntryStatus(s) for s in metric.status_filter}
    asof = scope.asof_ordinal()

    total = Decimal("0.00")
    for line in wh.lines:
        if line.account_id not in selected:
            continue
        entry = entries[line.entry_id]
        if entry.entity_id not in in_scope:
            continue
        if entry.status not in statuses:
            continue
        if scope.consolidated and metric.eliminate_intercompany and entry.is_intercompany:
            continue
        period = periods[entry.period_id]
        ordinal = _period_ordinal(period.fiscal_year, period.month)
        if metric.period_semantics is PeriodSemantics.BALANCE:
            if ordinal > asof:
                continue
        else:  # FLOW — must fall inside the requested period window
            if period.fiscal_year != scope.fiscal_year:
                continue
            if scope.quarter is not None and period.quarter != scope.quarter:
                continue
            if scope.month is not None and period.month != scope.month:
                continue

        debit, credit = (line.debit_func, line.credit_func)
        if metric.currency == "transaction":
            debit, credit = (line.debit_txn, line.credit_txn)
        total += credit - debit if metric.sign is Sign.CREDIT else debit - credit

    return total.quantize(Decimal("0.01"))


class ControlTotal(BaseModel):
    key: str
    metric: str
    scope: Scope
    value: Decimal


def standard_control_totals(wh: Warehouse, metrics: dict[str, Metric]) -> list[ControlTotal]:
    """A battery of precomputed known-correct answers — eval ground truth + the verifier cross-check."""
    totals: list[ControlTotal] = []
    year = wh.periods[0].fiscal_year

    def add(key: str, metric_name: str, scope: Scope) -> None:
        totals.append(ControlTotal(
            key=key, metric=metric_name, scope=scope,
            value=compute_metric(wh, metrics[metric_name], scope),
        ))

    for metric_name in ("net_revenue", "operating_expense", "cogs", "ebitda"):
        add(f"{metric_name}.{year}.consolidated", metric_name,
            Scope(fiscal_year=year, consolidated=True))
        for q in (1, 2, 3, 4):
            add(f"{metric_name}.{year}.Q{q}.consolidated", metric_name,
                Scope(fiscal_year=year, quarter=q, consolidated=True))
    for entity in wh.entities:
        add(f"net_revenue.{year}.entity-{entity.code}", "net_revenue",
            Scope(fiscal_year=year, entity_id=entity.entity_id))
    add(f"cash_balance.{year}.consolidated", "cash_balance",
        Scope(fiscal_year=year, consolidated=True))
    return totals
