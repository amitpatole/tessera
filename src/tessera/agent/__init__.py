"""The NL→SQL agent — turns a plain-English finance question into an executed, sourced answer.

The pipeline is deliberately split so the trust boundary is obvious:

1. **Understand + resolve** (``resolver``) — map the question to a *certified* metric and a
   :class:`~tessera.ledger.controls.Scope`. Deterministic and key-free by default; an LLM can sharpen
   the understanding step but never invents a metric outside the semantic layer.
2. **Generate SQL** (``sql``) — the query *structure* comes from the trusted metric definition (a
   whitelist); only user-derived *values* (year, quarter, entity) are bound as parameters. No
   string-built SQL, executed against a read-only connection.
3. **Answer** (``pipeline``) — execute, format, and return a :class:`~tessera.LedgerReport`.

Crucially, the agent **does not certify its own answer**: every report comes back ``WARN`` /
"unverified". Turning that into a PASS is the independent verifier's job (Phase 3). That separation
*is* the product.
"""

from __future__ import annotations

from .pipeline import answer_question
from .resolver import QuerySpec, ResolutionError, resolve_question
from .sql import build_sql, execute_metric

__all__ = [
    "answer_question",
    "QuerySpec",
    "ResolutionError",
    "resolve_question",
    "build_sql",
    "execute_metric",
]
