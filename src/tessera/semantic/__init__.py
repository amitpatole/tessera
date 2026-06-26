"""The semantic layer — certified metric definitions, the governance artifact.

A metric is not a SQL snippet; it is a *contract*: which accounts, which sign, which status filter,
which period grain, which entity scope, whether intercompany is eliminated. It is simultaneously the
model's grounding (what ``net_revenue`` is allowed to mean) and the verifier's source of truth (what
the number must reconcile to).
"""

from __future__ import annotations

from .loader import Metric, MetricComponent, PeriodSemantics, Sign, load_metrics

__all__ = ["Metric", "MetricComponent", "PeriodSemantics", "Sign", "load_metrics"]
