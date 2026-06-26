"""Cost-cascade routing (Phase 5) — verdict-driven escalation across model tiers.

Try the cheapest tier; accept its answer only if the independent verifier passes it; escalate to a
pricier tier only when it does not. The verifier is what makes cheap-first safe. The cross-workload
optimization that *chooses* the cascade is the QAOA cost-routing work this builds on.
"""

from __future__ import annotations

from .bench import BenchmarkResult, run_benchmark
from .router import Attempt, RoutingResult, cascade
from .tiers import CertifiedTier, HeuristicTier, ModelTier, default_tiers

__all__ = [
    "cascade",
    "Attempt",
    "RoutingResult",
    "run_benchmark",
    "BenchmarkResult",
    "ModelTier",
    "CertifiedTier",
    "HeuristicTier",
    "default_tiers",
]
