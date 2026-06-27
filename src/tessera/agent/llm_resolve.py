"""Resolve a question to a certified metric + scope **with a model** — safely.

The model never writes SQL. It only chooses, from the *certified* set, which metric and scope the
question means; Tessera then builds the trusted, parameterized SQL itself (see
:mod:`tessera.agent.sql`). So a model — however small or wrong — can pick the wrong metric or scope
(which the independent verifier catches), but it can never inject SQL or invent a metric. That is what
makes a cheap, unreliable model *safe* to put first in the cost cascade.
"""

from __future__ import annotations

import json
import re

from ..ledger.controls import Scope
from ..ledger.schema import Entity
from ..semantic.loader import Metric
from .llm import LLMClient
from .resolver import QuerySpec, ResolutionError


def _prompt(question: str, metrics: dict[str, Metric], entities: list[Entity]) -> str:
    metric_names = ", ".join(metrics)
    entity_lines = "; ".join(f"{e.code}={e.name}" for e in entities if not e.is_parent)
    return (
        "You convert a finance question into a strict JSON object and nothing else.\n"
        f"Allowed metrics: {metric_names}.\n"
        f"Entities (code=name): {entity_lines}. Use \"consolidated\" for the whole group.\n"
        "Output ONLY this JSON, no prose:\n"
        '{"metric": <one allowed metric>, "fiscal_year": <int>, '
        '"quarter": <1-4 or null>, "entity": <entity code or "consolidated">}\n\n'
        f"Question: {question}\n"
    )


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ResolutionError("model did not return JSON")
    try:
        value = json.loads(match.group(0))
    except ValueError as exc:
        raise ResolutionError(f"model JSON invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ResolutionError("model JSON is not an object")
    return value


def _match_entity_token(raw: str, entities: list[Entity]) -> int | None:
    """Match a model's entity string by code, full name, or the distinctive token (e.g. 'brazil')."""
    for e in entities:
        if e.is_parent:
            continue
        token = e.name.lower().replace("acme", "").strip()
        if raw == e.code.lower() or raw == e.name.lower() or (token and token in raw):
            return e.entity_id
    return None


def resolve_with_llm(
    question: str, client: LLMClient, metrics: dict[str, Metric], entities: list[Entity]
) -> QuerySpec:
    """Use a model to map a question to a certified :class:`QuerySpec`, validating its choices."""
    data = _extract_json(client.complete(_prompt(question, metrics, entities)))

    metric = str(data.get("metric", "")).strip()
    if metric not in metrics:
        raise ResolutionError(f"model chose an unknown metric: {metric!r}")

    try:
        year = int(data["fiscal_year"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ResolutionError("model did not return a fiscal_year") from exc

    quarter_raw = data.get("quarter")
    quarter = None if quarter_raw in (None, "", "null") else int(str(quarter_raw))
    if quarter is not None and quarter not in (1, 2, 3, 4):
        raise ResolutionError(f"model returned an invalid quarter: {quarter}")

    entity_raw = str(data.get("entity", "consolidated")).strip().lower()
    if entity_raw in ("", "consolidated", "group", "all", "none", "null"):
        scope = Scope(fiscal_year=year, quarter=quarter, consolidated=True)
    else:
        entity_id = _match_entity_token(entity_raw, entities)
        if entity_id is None:
            raise ResolutionError(f"model chose an unknown entity: {entity_raw!r}")
        scope = Scope(fiscal_year=year, quarter=quarter, entity_id=entity_id, consolidated=False)

    return QuerySpec(question=question, metric=metric, scope=scope)
