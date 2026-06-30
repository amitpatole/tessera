"""Model tiers for the cost cascade — deterministic *and* real (Ollama / OpenAI), one interface.

A *tier* turns a question into a candidate answer ``(value, sql)``. The cascade tries tiers
cheapest-first and escalates only when the independent verifier rejects a candidate, so the expensive
tier is paid for only on the questions that actually need it.

Three kinds implement the same :class:`ModelTier`:

- :class:`CertifiedTier` — always emits the correct query for the certified metric (a deterministic,
  reliable "strong" reference).
- :class:`HeuristicTier` — an *offline simulation* of a cheap model's unreliability: it commits the
  failure class it is "blind" to on hard questions and is correct otherwise.
- :class:`LLMTier` — a **real** model (local Ollama or OpenAI). The model only resolves the question
  to a certified metric + scope (it never writes SQL); Tessera builds the trusted SQL. A small/cheap
  model genuinely mis-resolves sometimes — the verifier catches it and the cascade escalates.

Every tier receives the *certified* ``metric``/``scope`` too (the ground-truth intent the verifier
grades against); a deterministic tier uses it directly, while :class:`LLMTier` ignores it and resolves
the question on its own.
"""

from __future__ import annotations

import os
import sqlite3
from decimal import Decimal
from typing import Protocol, runtime_checkable

from ..contract import FailureClass
from ..ledger.controls import Scope
from ..ledger.schema import Entity
from ..semantic.loader import Metric


@runtime_checkable
class ModelTier(Protocol):
    name: str
    price_per_1k: float  # estimated USD per 1k tokens (input+output), illustrative

    def plan(
        self, question: str, conn: sqlite3.Connection, registry: dict[str, Metric],
        entities: list[Entity], metric: str, scope: Scope,
    ) -> tuple[Decimal, str]: ...


class CertifiedTier:
    """A strong, reliable (and pricier) reference tier — always the correct query for the metric."""

    def __init__(self, name: str = "strong", price_per_1k: float = 0.02) -> None:
        self.name = name
        self.price_per_1k = price_per_1k

    def plan(self, question, conn, registry, entities, metric, scope):
        from ..agent.sql import execute_metric

        return execute_metric(conn, registry, metric, scope)


DEFAULT_BLIND_SPOTS = (FailureClass.INTERCOMPANY_DOUBLE_COUNT,)


class HeuristicTier:
    """Offline simulation of a cheap model: correct on simple questions, commits a blind-spot class
    on the hard ones (consolidations). Used when no real model is configured (keeps CI deterministic)."""

    def __init__(
        self, name: str = "cheap", price_per_1k: float = 0.001,
        blind_spots: tuple[FailureClass, ...] = DEFAULT_BLIND_SPOTS,
    ) -> None:
        self.name = name
        self.price_per_1k = price_per_1k
        self.blind_spots = blind_spots

    def plan(self, question, conn, registry, entities, metric, scope):
        from ..agent.sql import execute_metric
        from ..verifier import inject_failure

        for fc in self.blind_spots:
            injected = inject_failure(conn, registry, metric, scope, fc)
            if injected is not None:
                return injected
        return execute_metric(conn, registry, metric, scope)


class LLMTier:
    """A real model tier (Ollama or OpenAI). The model resolves the question to a certified metric +
    scope; Tessera builds the parameterized SQL and executes it. Mis-resolution → the verifier catches
    it. Raises on a model/resolution failure so the cascade escalates to the next tier."""

    def __init__(self, name: str, price_per_1k: float, client) -> None:
        self.name = name
        self.price_per_1k = price_per_1k
        self.client = client

    def plan(self, question, conn, registry, entities, metric, scope):
        from ..agent.llm_resolve import resolve_with_llm
        from ..agent.sql import build_sql, inline_params
        from ..ledger.schema import from_minor

        spec = resolve_with_llm(question, self.client, registry, entities)
        if registry[spec.metric].components:
            from ..agent.sql import execute_metric  # derived metrics: compose component SQL

            return execute_metric(conn, registry, spec.metric, spec.scope)
        sql, params = build_sql(registry[spec.metric], spec.scope)
        row = conn.execute(sql, params).fetchone()
        return from_minor(int(row[0] if row else 0)), inline_params(sql, params)


def default_tiers() -> list[ModelTier]:
    """The deterministic cheap→strong cascade (CI-safe; no network)."""
    return [HeuristicTier(), CertifiedTier()]


def real_tiers_available() -> str | None:
    """Which real backend is configured, in priority order: 'torch', 'vllm', 'openai', 'ollama', or
    None (→ use the deterministic simulation). The PyTorch-native tiers come first so a configured
    local model is preferred for the air-gapped, no-egress story."""
    if os.environ.get("TESSERA_TORCH_MODEL"):
        return "torch"
    if os.environ.get("TESSERA_VLLM_MODEL"):
        return "vllm"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("TESSERA_OLLAMA_MODEL"):
        return "ollama"
    return None


def cascade_tiers(prefer_real: bool = True) -> list[ModelTier]:
    """Build the cascade: real model tiers when configured, otherwise the deterministic simulation.

    Backends (cheap tier → reliable escalation):

    - **torch** (``TESSERA_TORCH_MODEL``) — a model run in-process on PyTorch via Transformers; the
      certified reference is the escalation target. The most literally PyTorch-native cascade.
    - **vllm** (``TESSERA_VLLM_MODEL``) — a model served by vLLM (PyTorch under the hood) over its
      OpenAI-compatible API; certified reference escalation.
    - **openai** (``OPENAI_API_KEY``) — cheap=gpt-4o-mini → strong=gpt-4o.
    - **ollama** (``TESSERA_OLLAMA_MODEL``) — a local Ollama model → certified reference escalation.
    """
    backend = real_tiers_available() if prefer_real else None
    if backend == "torch":
        from ..agent.llm import TorchTransformersClient

        model = os.environ["TESSERA_TORCH_MODEL"]
        # One in-process PyTorch model + the certified reference as the reliable escalation target.
        return [
            LLMTier(f"torch:{model}", 0.0002, TorchTransformersClient(model=model)),
            CertifiedTier(),
        ]
    if backend == "vllm":
        from ..agent.llm import VLLMClient

        model = os.environ["TESSERA_VLLM_MODEL"]
        base = os.environ.get("TESSERA_VLLM_BASE", "http://127.0.0.1:8000/v1")
        return [
            LLMTier(f"vllm:{model}", 0.0002, VLLMClient(model=model, base_url=base)),
            CertifiedTier(),
        ]
    if backend == "openai":
        from ..agent.llm import OpenAIClient

        cheap = os.environ.get("TESSERA_OPENAI_CHEAP", "gpt-4o-mini")
        strong = os.environ.get("TESSERA_OPENAI_STRONG", "gpt-4o")
        return [
            LLMTier(f"openai:{cheap}", 0.001, OpenAIClient(model=cheap)),
            LLMTier(f"openai:{strong}", 0.02, OpenAIClient(model=strong)),
        ]
    if backend == "ollama":
        from ..agent.llm import OllamaClient

        model = os.environ["TESSERA_OLLAMA_MODEL"]
        # One local model + the certified reference as the reliable escalation target.
        return [LLMTier(f"ollama:{model}", 0.0002, OllamaClient(model=model)), CertifiedTier()]
    return default_tiers()
