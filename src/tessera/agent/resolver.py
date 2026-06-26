"""Resolve a natural-language question to a certified metric + scope.

This is deterministic and key-free: it matches the question against the *certified* metric registry
and the entity dimension, so a question can never resolve to a metric the semantic layer does not
define. (An LLM understanding step, when configured, produces the same :class:`QuerySpec` shape — it
sharpens phrasing robustness; it does not widen what a metric may mean.)
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from ..ledger.controls import Scope
from ..ledger.schema import Entity
from ..semantic.loader import Metric


class ResolutionError(ValueError):
    """Raised when a question cannot be mapped to a certified metric or a period."""


class QuerySpec(BaseModel):
    """The structured intent behind a question: which metric, over which slice of the ledger."""

    question: str
    metric: str
    scope: Scope


# Metric aliases — the phrasings a user might use for each certified metric.
_METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "net_revenue": ("net revenue", "revenue", "sales", "top line", "turnover"),
    "operating_expense": ("operating expense", "operating expenses", "opex", "sg&a", "overhead"),
    "cogs": ("cogs", "cost of goods sold", "cost of sales", "cost of goods"),
    "ebitda": ("ebitda",),
    "cash_balance": ("cash balance", "cash on hand", "cash position", "cash"),
}

_QUARTER_WORDS = {
    "first quarter": 1, "second quarter": 2, "third quarter": 3, "fourth quarter": 4,
    "q1": 1, "q2": 2, "q3": 3, "q4": 4,
}
_CONSOLIDATED_WORDS = ("consolidated", "consolidate", "group", "all entities", "company-wide",
                       "companywide", "total company", "across all")


def _match_metric(text: str, metrics: dict[str, Metric]) -> str:
    """Pick the certified metric whose alias has the longest match in the text (most specific wins)."""
    best: tuple[int, str] | None = None
    for name in metrics:
        for alias in _METRIC_ALIASES.get(name, (name.replace("_", " "),)):
            if alias in text:
                score = len(alias)
                if best is None or score > best[0]:
                    best = (score, name)
    if best is None:
        raise ResolutionError("no certified metric matches the question")
    return best[1]


def _match_year(text: str) -> int:
    years = re.findall(r"\b(20\d{2})\b", text)
    if not years:
        raise ResolutionError("no fiscal year found in the question")
    return int(years[0])


def _match_quarter(text: str) -> int | None:
    for word, q in _QUARTER_WORDS.items():
        if word in text:
            return q
    return None


def _match_entity(text: str, entities: list[Entity]) -> int | None:
    for e in entities:
        if e.is_parent:
            continue
        # Match the distinctive part of the name ("brazil", "europe", "us") or the code.
        needle = e.name.lower().replace("acme", "").strip()
        if needle and needle in text:
            return e.entity_id
        if re.search(rf"\bacme {re.escape(e.code.lower())}\b", text):
            return e.entity_id
    return None


def resolve_question(
    question: str, metrics: dict[str, Metric], entities: list[Entity]
) -> QuerySpec:
    """Map a question to a :class:`QuerySpec`, or raise :class:`ResolutionError`."""
    text = question.lower()
    metric = _match_metric(text, metrics)
    year = _match_year(text)
    quarter = _match_quarter(text)
    entity_id = _match_entity(text, entities)
    consolidated = any(w in text for w in _CONSOLIDATED_WORDS)
    # Default scope: if a single entity is named, scope to it; otherwise consolidated.
    if entity_id is None:
        consolidated = True
    scope = Scope(
        fiscal_year=year,
        quarter=quarter,
        entity_id=entity_id if not consolidated else None,
        consolidated=consolidated,
    )
    return QuerySpec(question=question, metric=metric, scope=scope)
