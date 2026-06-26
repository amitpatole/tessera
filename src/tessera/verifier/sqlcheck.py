"""Light, dependency-free SQL-contract heuristics — corroborating evidence, not the primary verdict.

The authoritative check is the orthogonal recompute in :mod:`tessera.verifier.verify`; this module
adds a cheap static read of the generated SQL to (a) ground *why* a wrong number is wrong and (b)
flag a query that returns the right number today but omits a clause the certified metric requires
(fragile — it would drift the moment the data does). These are substring heuristics on purpose: no
SQL parser in the base install. They never upgrade a verdict on their own.
"""

from __future__ import annotations

from ..contract import FailureClass
from ..ledger.controls import Scope
from ..semantic.loader import Metric, PeriodSemantics


def contract_findings(sql: str, metric: Metric, scope: Scope) -> list[tuple[FailureClass, str]]:
    """Return (failure class, message) for each clause the certified metric requires but the SQL lacks."""
    s = sql.lower()
    out: list[tuple[FailureClass, str]] = []

    if "status" not in s:
        out.append((FailureClass.DRAFT_OR_REVERSED,
                    "no status filter in the SQL — draft/reversed entries may be included"))

    if scope.consolidated and metric.eliminate_intercompany and "is_intercompany" not in s:
        out.append((FailureClass.INTERCOMPANY_DOUBLE_COUNT,
                    "consolidated query with no intercompany elimination (is_intercompany)"))

    if not scope.consolidated and scope.entity_id is not None and "entity_id" not in s:
        out.append((FailureClass.MISSING_ENTITY_FILTER,
                    "entity-scoped question but the SQL has no entity_id filter"))

    if metric.period_semantics is PeriodSemantics.FLOW and scope.quarter is not None \
            and "quarter" not in s:
        out.append((FailureClass.WRONG_PERIOD_GRAIN,
                    "a quarter was asked but the SQL has no quarter filter"))

    if metric.currency == "functional" and "func" not in s and "txn" in s:
        out.append((FailureClass.FX_MIXING,
                    "transaction-currency columns summed — currencies mixed without translation"))

    return out
