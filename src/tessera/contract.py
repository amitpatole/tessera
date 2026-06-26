"""Tessera's grounding dimension on top of the shared :mod:`agentsensory` contract.

A Tessera answer is graded the same way every organ grades its dimension: it emits an
``agentsensory`` ``Report`` whose issues are grounded in *this* dimension. For a ledger, the
grounding is a **failure class** — one of the enumerable, orthogonally-checkable ways a generated
SQL answer can be wrong about money. We do not re-run the model's own SQL to "check" it (that is
circular and worthless); each failure class has an independent test that an auditor could perform
by hand.

This module deliberately defines *only* the contract types — the recompute checks, the warehouse,
the receipt signer, and the CLI build on top of it in later phases. Keeping the contract small and
import-light means anything can depend on it without pulling FastAPI/LangGraph/psycopg.
"""

from __future__ import annotations

from enum import Enum

from agentsensory import IssueBase, ReportBase
from pydantic import Field


class FailureClass(str, Enum):
    """The enumerable ways a text-to-SQL answer can be wrong about a General Ledger.

    Each value is an issue ``kind`` carried on a :class:`LedgerIssue`. Every class has a
    corresponding *independent* check (added in later phases) — orthogonal to the model's own SQL,
    so a wrong answer cannot vouch for itself.
    """

    WRONG_PERIOD_GRAIN = "wrong_period_grain"
    """Period-to-date vs as-of, or month/quarter/year grain mismatch vs the question."""

    MISSING_ENTITY_FILTER = "missing_entity_filter"
    """Aggregated across legal entities the question scoped to one of."""

    SIGN_FLIP = "debit_credit_sign_flip"
    """Debit/credit sign convention inverted for the account's normal balance."""

    INTERCOMPANY_DOUBLE_COUNT = "intercompany_double_count"
    """Intercompany legs counted on both sides instead of eliminated on consolidation."""

    DRAFT_OR_REVERSED = "draft_or_reversed_entries"
    """Included unposted/draft journals or both sides of a reversal."""

    WRONG_STATEMENT_ROLLUP = "wrong_statement_line_rollup"
    """Accounts mapped to the wrong financial-statement line in the rollup."""

    FX_MIXING = "fx_mixing"
    """Summed amounts across currencies without translating to a single reporting currency."""

    ASOF_VS_PTD = "asof_vs_ptd"
    """Used a point-in-time balance where a period-flow was asked, or vice versa."""

    OTHER = "other"
    """A discrepancy that does not map to a known class (control total still failed)."""


class LedgerIssue(IssueBase):
    """An ``agentsensory`` issue grounded in Tessera's ledger dimension.

    Narrows ``kind`` to a :class:`FailureClass` so the enum ergonomics survive, while still being a
    plain ``IssueBase`` on the wire.
    """

    kind: FailureClass = Field(description="Which enumerable ledger failure class this is.")
    source: str = Field(
        default="independent_recompute",
        description="Which check raised it (the orthogonal verifier, a control total, ...).",
    )


class LedgerReport(ReportBase):
    """The verdict Tessera attaches to one natural-language answer.

    Carries the question, the SQL that was actually executed against the warehouse, and the scalar
    answer — the three things an auditor needs alongside the verdict and grounded issues. The
    signed receipt (added in a later phase) commits to exactly these fields.
    """

    issues: list[LedgerIssue] = Field(default_factory=list)  # type: ignore[assignment]
    question: str = Field(default="", description="The natural-language question as asked.")
    executed_sql: str | None = Field(
        default=None, description="The exact SQL run against the read-only warehouse role."
    )
    answer: str | None = Field(
        default=None, description="The scalar answer presented to the user, as a string."
    )
