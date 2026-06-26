"""Tessera — attested natural-language analytics for regulated finance.

Ask a question in plain English over a governed General-Ledger warehouse and get back not just a
number, but the *evidence* it is right: the exact executed SQL, an **independent** runtime verdict
(an orthogonal recompute that catches the enumerable ways text-to-SQL goes wrong on a ledger), and
a signed, auditor-verifiable receipt.

The verdict vocabulary is the shared :mod:`agentsensory` contract — Tessera is a consumer of that
contract, not a redefinition of it.
"""

from __future__ import annotations

from .contract import FailureClass, LedgerIssue, LedgerReport

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "FailureClass",
    "LedgerIssue",
    "LedgerReport",
]
