"""The independent verifier (Phase 3) — Tessera's core.

Given a question, the certified metric + scope it resolved to, the agent's generated SQL, and the
claimed number, :func:`verify` recomputes the answer by an orthogonal path and returns an
``agentsensory`` Report (PASS / WARN / FAIL) whose issues are grounded in the eight
:class:`~tessera.FailureClass` values. It never re-runs the model's own SQL to "check" it — that
would be circular. The same failure-class definitions both *diagnose* a wrong answer and *inject*
one for the regression suite (see :mod:`~tessera.verifier.counterfactuals`).
"""

from __future__ import annotations

from .counterfactuals import counterfactual_value, inject_failure
from .verify import verify

__all__ = ["verify", "counterfactual_value", "inject_failure"]
