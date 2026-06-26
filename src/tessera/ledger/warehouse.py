"""Materialize the in-memory :class:`~tessera.ledger.schema.Warehouse` into sqlite3.

Why sqlite: a real, queryable star schema with zero external services and no API key — the NL→SQL
agent (Phase 2) and the air-gapped demo run entirely offline against a single file. Amounts land as
INTEGER minor units so ``SUM(debit_func_minor)`` is exact.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .schema import DDL, Warehouse, to_minor


def materialize_sqlite(wh: Warehouse, path: str | Path = ":memory:") -> sqlite3.Connection:
    """Create the schema and load every row. Returns an open connection (caller closes it)."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL)

    conn.executemany(
        "INSERT INTO dim_entity VALUES (?,?,?,?,?,?,?)",
        [(e.entity_id, e.code, e.name, e.currency, e.functional_currency,
          e.consolidation_group, int(e.is_parent)) for e in wh.entities],
    )
    conn.executemany(
        "INSERT INTO dim_account VALUES (?,?,?,?,?,?,?)",
        [(a.account_id, a.code, a.name, a.account_type.value, a.normal_balance.value,
          a.statement_line, int(a.is_intercompany)) for a in wh.accounts],
    )
    conn.executemany(
        "INSERT INTO dim_period VALUES (?,?,?,?,?,?)",
        [(p.period_id, p.fiscal_year, p.quarter, p.month, p.label, int(p.is_closed))
         for p in wh.periods],
    )
    conn.executemany(
        "INSERT INTO dim_counterparty VALUES (?,?,?,?)",
        [(c.counterparty_id, c.name, int(c.is_intercompany), c.entity_id)
         for c in wh.counterparties],
    )
    conn.executemany(
        "INSERT INTO fact_journal_entry VALUES (?,?,?,?,?,?,?,?,?)",
        [(e.entry_id, e.entity_id, e.period_id, e.status.value, int(e.is_intercompany),
          e.counterparty_id, str(e.fx_rate), e.reverses_entry_id, e.memo) for e in wh.entries],
    )

    currency = {e.entity_id: e.currency for e in wh.entities}
    entry_entity = {e.entry_id: e.entity_id for e in wh.entries}
    conn.executemany(
        "INSERT INTO fact_journal_line VALUES (?,?,?,?,?,?,?,?)",
        [(ln.line_id, ln.entry_id, ln.account_id,
          to_minor(ln.debit_txn), to_minor(ln.credit_txn),
          to_minor(ln.debit_func), to_minor(ln.credit_func),
          currency[entry_entity[ln.entry_id]]) for ln in wh.lines],
    )
    conn.commit()
    return conn
