"""The end-to-end answer pipeline: question → resolved spec → SQL → executed answer → report.

The returned :class:`~tessera.LedgerReport` is deliberately **unverified** (``WARN``): the agent has
answered, not proven. Converting that WARN into a PASS/FAIL is the independent verifier's job
(Phase 3). Keeping the answer and its certification in separate steps is the whole point of Tessera.

This is a plain, explicit pipeline (understand → resolve → generate → execute → narrate). The
LangGraph orchestration wraps these same nodes once the LLM SQL-generation backend lands; it is kept
out of the base install so the dependency footprint stays light.
"""

from __future__ import annotations

import sqlite3

from agentsensory import Severity, Verdict

from ..contract import FailureClass, LedgerIssue, LedgerReport
from ..ledger.controls import compute_metric
from ..ledger.schema import Entity
from ..semantic.loader import Metric
from .resolver import ResolutionError, resolve_question
from .sql import execute_metric


def _format_money(value: object) -> str:
    return f"{value:,.2f} USD"


def answer_question(
    question: str,
    conn: sqlite3.Connection,
    metrics: dict[str, Metric],
    entities: list[Entity],
) -> LedgerReport:
    """Answer one NL question against the warehouse, returning an **unverified** report.

    A question that cannot be mapped to a certified metric returns a ``WARN`` report carrying an
    ``OTHER`` issue — the honest "I don't have a certified definition for that", never a guessed
    number.
    """
    try:
        spec = resolve_question(question, metrics, entities)
    except ResolutionError as exc:
        return LedgerReport(
            verdict=Verdict.WARN,
            summary=f"Could not map the question to a certified metric: {exc}",
            question=question,
            issues=[LedgerIssue.make(
                FailureClass.OTHER, Severity.WARNING,
                f"Out of the certified semantic layer: {exc}",
                source="resolver",
            )],
        )

    value, display_sql = execute_metric(conn, metrics, spec.metric, spec.scope)
    scope = spec.scope
    where = "consolidated" if scope.consolidated else f"entity {scope.entity_id}"
    grain = f"{scope.fiscal_year}" + (f" Q{scope.quarter}" if scope.quarter else "")
    return LedgerReport(
        verdict=Verdict.WARN,  # answered, NOT yet independently verified — that is Phase 3.
        summary=f"{spec.metric} ({where}, {grain}) = {_format_money(value)} — unverified.",
        question=question,
        executed_sql=display_sql,
        answer=_format_money(value),
    )


# compute_metric is re-exported so the eval harness / Phase 3 verifier can get the orthogonal
# ground-truth number directly from this module.
__all__ = ["answer_question", "compute_metric"]
