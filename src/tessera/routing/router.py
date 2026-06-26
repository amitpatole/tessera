"""The cost cascade — cheapest tier first, escalate only when the verifier is not satisfied.

This is the runtime policy. The per-query rule is simple and safe *because* the verifier is
independent: a cheap answer is accepted only if the orthogonal recompute passes it, so cost is saved
without trading away correctness. The broader optimization — assigning tiers across a whole workload
under a budget — is the contribution of *Quantum-Enhanced LLM Cascade Routing* (QAOA), which sits
above this loop and chooses the cascade; here we execute it and measure what it saves.
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from agentsensory import Verdict
from pydantic import BaseModel

from ..ledger.controls import Scope
from ..ledger.schema import Warehouse
from ..semantic.loader import Metric
from ..verifier import verify
from .tiers import ModelTier

# Estimated prompt overhead (schema + instructions) in tokens, for cost accounting only.
_PROMPT_BASE_TOKENS = 350


def _estimate_tokens(question: str, sql: str) -> int:
    """A coarse token estimate (≈4 chars/token) for cost accounting — labelled estimated everywhere."""
    return _PROMPT_BASE_TOKENS + (len(question) + len(sql)) // 4


class Attempt(BaseModel):
    tier: str
    verdict: str
    answer: str | None
    est_tokens: int
    cost_usd: float


class RoutingResult(BaseModel):
    question: str
    accepted: bool
    accepted_tier: str | None
    final_verdict: str
    answer: str | None
    attempts: list[Attempt]
    escalations: int
    total_cost_usd: float
    # The cost had we gone straight to the most expensive tier (the no-cascade baseline).
    baseline_cost_usd: float

    @property
    def saved_usd(self) -> float:
        return round(self.baseline_cost_usd - self.total_cost_usd, 8)


def cascade(
    *,
    question: str,
    metric_name: str,
    scope: Scope,
    conn: sqlite3.Connection,
    warehouse: Warehouse,
    registry: dict[str, Metric],
    tiers: list[ModelTier],
    tolerance: Decimal = Decimal("0.01"),
) -> RoutingResult:
    """Run the cascade for one question. Accept the first tier the verifier passes; else escalate."""
    ordered = sorted(tiers, key=lambda t: t.price_per_1k)
    attempts: list[Attempt] = []
    total_cost = 0.0
    final = None
    accepted_tier: str | None = None

    for tier in ordered:
        value, sql = tier.plan(conn, registry, metric_name, scope)
        tokens = _estimate_tokens(question, sql)
        cost = round(tier.price_per_1k * tokens / 1000, 8)
        total_cost = round(total_cost + cost, 8)
        report = verify(
            question=question, metric_name=metric_name, scope=scope, claimed_value=value,
            generated_sql=sql, warehouse=warehouse, registry=registry, tolerance=tolerance,
        )
        attempts.append(Attempt(tier=tier.name, verdict=report.verdict.value, answer=report.answer,
                                est_tokens=tokens, cost_usd=cost))
        final = report
        if report.verdict is Verdict.PASS:
            accepted_tier = tier.name
            break

    # Baseline: one call to the most expensive tier (what you'd pay with no cascade).
    strongest = max(ordered, key=lambda t: t.price_per_1k)
    baseline_tokens = _estimate_tokens(question, "")  # comparable order of magnitude
    baseline_cost = round(strongest.price_per_1k * baseline_tokens / 1000, 8)

    assert final is not None
    return RoutingResult(
        question=question,
        accepted=accepted_tier is not None,
        accepted_tier=accepted_tier,
        final_verdict=final.verdict.value,
        answer=final.answer,
        attempts=attempts,
        escalations=max(0, len(attempts) - 1),
        total_cost_usd=total_cost,
        baseline_cost_usd=baseline_cost,
    )
