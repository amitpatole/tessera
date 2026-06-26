"""The independent verifier — turns the agent's unverified answer into a grounded PASS/WARN/FAIL.

The verdict comes from an **orthogonal recompute**: the certified metric is rolled up directly from
the warehouse (a different engine than the agent's SQL, and never derived from that SQL), then the
claim is reconciled against it. A divergence is *diagnosed* by matching the claim to the
counterfactual value of each reachable failure class, so the report names the mistake and shows both
numbers. SQL-contract heuristics corroborate but never decide.

Honesty (per the spec): the receipt this enables proves *"these independent checks ran and the number
reconciles to the certified metric / control total,"* not metaphysical truth. A question outside the
modelled metrics returns WARN, not false confidence — that path lives in the agent's resolver.
"""

from __future__ import annotations

from decimal import Decimal

from agentsensory import Confidence, Severity, Verdict, verdict_from_issues

from ..contract import FailureClass, LedgerIssue, LedgerReport
from ..ledger.controls import Scope, compute_metric
from ..ledger.schema import Warehouse
from ..semantic.loader import Metric
from .counterfactuals import counterfactual_value
from .sqlcheck import contract_findings

_DIAGNOSABLE = [fc for fc in FailureClass if fc is not FailureClass.OTHER]


def _money(value: Decimal) -> str:
    return f"{value:,.2f} USD"


def verify(
    *,
    question: str,
    metric_name: str,
    scope: Scope,
    claimed_value: Decimal,
    generated_sql: str,
    warehouse: Warehouse,
    registry: dict[str, Metric],
    tolerance: Decimal = Decimal("0.01"),
) -> LedgerReport:
    """Reconcile a claimed answer against the certified metric and return a grounded report."""
    metric = registry[metric_name]
    truth = compute_metric(warehouse, metric, scope)
    delta = claimed_value - truth
    contract = contract_findings(generated_sql, metric, scope)
    issues: list[LedgerIssue] = []

    if abs(delta) <= tolerance:
        # The number reconciles. A missing required clause makes it fragile, not wrong → WARN.
        for fc, msg in contract:
            issues.append(LedgerIssue.make(
                fc, Severity.WARNING,
                f"Answer reconciles to {_money(truth)}, but the query is fragile: {msg}.",
                source="sql_contract", confidence=Confidence.MEDIUM,
            ))
        summary = (
            f"{metric_name} = {_money(truth)} reconciles to the certified metric"
            + (" — but with query-contract warnings." if contract else ".")
        )
    else:
        # The number is wrong. Diagnose which failure class reproduces the claim.
        matched: list[FailureClass] = []
        for fc in _DIAGNOSABLE:
            cf = counterfactual_value(warehouse, registry, metric_name, scope, fc)
            if cf is not None and cf != truth and abs(claimed_value - cf) <= tolerance:
                matched.append(fc)

        if matched:
            for fc in matched:
                issues.append(LedgerIssue.make(
                    fc, Severity.CRITICAL,
                    f"Does not reconcile: claimed {_money(claimed_value)} equals the value produced "
                    f"by '{fc.value}'. The certified {metric_name} is {_money(truth)} "
                    f"(off by {_money(delta)}).",
                    source="orthogonal_recompute", confidence=Confidence.HIGH,
                    detail={"claimed": str(claimed_value), "certified": str(truth),
                            "delta": str(delta), "failure_class": fc.value},
                ))
        else:
            issues.append(LedgerIssue.make(
                FailureClass.OTHER, Severity.CRITICAL,
                f"Does not reconcile: claimed {_money(claimed_value)} vs certified {metric_name} "
                f"{_money(truth)} (off by {_money(delta)}), and matches no known failure class.",
                source="orthogonal_recompute", confidence=Confidence.HIGH,
                detail={"claimed": str(claimed_value), "certified": str(truth), "delta": str(delta)},
            ))

        # Corroborating SQL-contract findings (supporting, not the basis of the verdict).
        for fc, msg in contract:
            if fc not in matched:
                issues.append(LedgerIssue.make(
                    fc, Severity.ERROR, f"Corroborating SQL-contract signal: {msg}.",
                    source="sql_contract", confidence=Confidence.MEDIUM,
                ))
        summary = (
            f"{metric_name} FAILS verification: claimed {_money(claimed_value)} "
            f"vs certified {_money(truth)} (off by {_money(delta)})."
        )

    verdict = verdict_from_issues(list(issues)) if issues else Verdict.PASS  # type: ignore[arg-type]
    return LedgerReport(
        verdict=verdict,
        summary=summary,
        issues=issues,
        question=question,
        executed_sql=generated_sql,
        answer=_money(claimed_value),
        backend="orthogonal_recompute",
    )
