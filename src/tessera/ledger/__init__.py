"""The governed General-Ledger warehouse — Tessera's synthetic, shareable, balanced books.

Nothing here is anyone's real data. The point is a multi-entity ledger rich enough that an LLM's
generated SQL goes wrong in *nameable* ways (the eight :class:`~tessera.FailureClass` values), while
the books genuinely balance — so the verifier's invariants are real, not decorative.

Public surface:

- :func:`~tessera.ledger.generator.generate` — build the in-memory warehouse from a seed.
- :class:`~tessera.ledger.schema.Warehouse` — the generated tables.
- :func:`~tessera.ledger.warehouse.materialize_sqlite` — write the star schema to a sqlite3 file.
- :mod:`~tessera.ledger.controls` — the invariants and precomputed control totals.
"""

from __future__ import annotations

from .generator import GeneratorConfig, generate
from .schema import (
    Account,
    AccountType,
    Counterparty,
    Entity,
    EntryStatus,
    JournalEntry,
    JournalLine,
    NormalBalance,
    Period,
    Warehouse,
)

__all__ = [
    "GeneratorConfig",
    "generate",
    "Account",
    "AccountType",
    "Counterparty",
    "Entity",
    "EntryStatus",
    "JournalEntry",
    "JournalLine",
    "NormalBalance",
    "Period",
    "Warehouse",
]
