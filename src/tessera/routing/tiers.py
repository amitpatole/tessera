"""Model tiers for the cost cascade — a cheap tier, a strong tier, one interface.

A *tier* turns a resolved (metric, scope) into a candidate ``(value, sql)``. Tiers differ in price
and in reliability. The router (see :mod:`tessera.routing.router`) tries them cheapest-first and
escalates only when the independent verifier rejects a candidate — so the expensive tier is paid for
only on the questions that actually need it.

For an offline, deterministic demo, :class:`HeuristicTier` models a cheap model's unreliability by
committing the failure class it is "blind" to when the question is susceptible (reusing the Phase-3
injection), and answering correctly otherwise. Real model tiers (a local Ollama, a cloud Bedrock
model) implement the same :class:`ModelTier` interface and slot straight in at deploy time.
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from typing import Protocol, runtime_checkable

from ..contract import FailureClass
from ..ledger.controls import Scope
from ..semantic.loader import Metric


@runtime_checkable
class ModelTier(Protocol):
    name: str
    price_per_1k: float  # estimated USD per 1k tokens (input+output), illustrative

    def plan(
        self, conn: sqlite3.Connection, registry: dict[str, Metric], metric_name: str, scope: Scope
    ) -> tuple[Decimal, str]: ...


class CertifiedTier:
    """A strong, reliable (and pricier) tier — always emits the correct query for the metric."""

    def __init__(self, name: str = "strong", price_per_1k: float = 0.02) -> None:
        self.name = name
        self.price_per_1k = price_per_1k

    def plan(
        self, conn: sqlite3.Connection, registry: dict[str, Metric], metric_name: str, scope: Scope
    ) -> tuple[Decimal, str]:
        from ..agent.sql import execute_metric

        return execute_metric(conn, registry, metric_name, scope)


# A cheap model's signature blind spot: it forgets the intercompany elimination on a *consolidated*
# view (the classic audit failure), while handling simpler single-entity questions fine. More classes
# can be configured; this one gives the cleanest cheap-wins-vs-escalations split for the demo.
DEFAULT_BLIND_SPOTS = (FailureClass.INTERCOMPANY_DOUBLE_COUNT,)


class HeuristicTier:
    """A cheap, fast, less-reliable tier. Correct on simple questions; commits a blind-spot class on
    the hard ones (consolidations, multi-currency) — exactly where a low-cost model tends to slip."""

    def __init__(
        self, name: str = "cheap", price_per_1k: float = 0.001,
        blind_spots: tuple[FailureClass, ...] = DEFAULT_BLIND_SPOTS,
    ) -> None:
        self.name = name
        self.price_per_1k = price_per_1k
        self.blind_spots = blind_spots

    def plan(
        self, conn: sqlite3.Connection, registry: dict[str, Metric], metric_name: str, scope: Scope
    ) -> tuple[Decimal, str]:
        from ..agent.sql import execute_metric
        from ..verifier import inject_failure

        for fc in self.blind_spots:
            injected = inject_failure(conn, registry, metric_name, scope, fc)
            if injected is not None:
                return injected  # committed the mistake it is blind to
        return execute_metric(conn, registry, metric_name, scope)  # nothing to slip on → correct


def default_tiers() -> list[ModelTier]:
    """The standard cheap→strong cascade used by the CLI and the benchmark."""
    return [HeuristicTier(), CertifiedTier()]
