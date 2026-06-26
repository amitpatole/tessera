"""Benchmark the cascade over a mixed question set: cost vs an always-strong baseline.

The point is a number an interviewer can hold: *the cascade answered every question correctly while
spending X% less than routing everything to the expensive model* — because the cheap tier handled the
easy questions and the verifier forced an escalation exactly when (and only when) it was wrong.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..agent.resolver import ResolutionError, resolve_question
from ..ledger import GeneratorConfig, generate
from ..ledger.warehouse import materialize_sqlite
from ..semantic import load_metrics
from .router import RoutingResult, cascade
from .tiers import ModelTier, default_tiers

# A deliberate mix: single-entity questions a cheap model handles, and consolidations where it slips.
DEFAULT_QUESTIONS = [
    "net revenue for ACME Brazil in 2025",
    "net revenue for ACME US in 2025",
    "operating expenses for ACME Europe in 2025",
    "What was consolidated net revenue in 2025?",
    "consolidated operating expenses in 2025",
    "consolidated net revenue in Q3 2025",
]


class BenchmarkResult(BaseModel):
    results: list[RoutingResult]
    n: int
    cheap_wins: int
    escalations: int
    accuracy_pct: float
    total_cost_usd: float
    baseline_cost_usd: float
    pct_saved: float


def run_benchmark(
    questions: list[str] | None = None, *, seed: int = 20260626,
    tiers: list[ModelTier] | None = None,
) -> BenchmarkResult:
    """Run the cascade over the question set and aggregate cost/quality."""
    qs = questions if questions is not None else DEFAULT_QUESTIONS
    tiers = tiers or default_tiers()
    wh = generate(GeneratorConfig(seed=seed))
    metrics = load_metrics()
    conn = materialize_sqlite(wh, ":memory:")
    results: list[RoutingResult] = []
    try:
        for q in qs:
            try:
                spec = resolve_question(q, metrics, wh.entities)
            except ResolutionError:
                continue
            results.append(cascade(
                question=q, metric_name=spec.metric, scope=spec.scope, conn=conn,
                warehouse=wh, registry=metrics, tiers=tiers,
            ))
    finally:
        conn.close()

    n = len(results)
    total = round(sum(r.total_cost_usd for r in results), 8)
    baseline = round(sum(r.baseline_cost_usd for r in results), 8)
    cheap_wins = sum(1 for r in results if r.accepted and r.escalations == 0)
    escalations = sum(1 for r in results if r.escalations > 0)
    accepted = sum(1 for r in results if r.final_verdict == "pass")
    pct_saved = round((baseline - total) / baseline * 100, 2) if baseline else 0.0
    accuracy = round(accepted / n * 100, 2) if n else 0.0
    return BenchmarkResult(
        results=results, n=n, cheap_wins=cheap_wins, escalations=escalations,
        accuracy_pct=accuracy, total_cost_usd=total, baseline_cost_usd=baseline, pct_saved=pct_saved,
    )
