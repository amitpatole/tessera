"""Signed receipts (Phase 4) — make the verdict auditor-verifiable, offline.

A :class:`Receipt` binds a verified :class:`~tessera.LedgerReport` (verdict + executed SQL + answer +
grounded-issue digest) under an Ed25519 signature from a per-install key (never a default secret;
see :mod:`tessera.receipt.keys`). :func:`verify_receipt` re-checks it with no network and no access
to the warehouse — so trust rests on the receipt, not on the system that issued it.
"""

from __future__ import annotations

from .keys import SigningKeyError, key_id, load_or_create_signing_key, public_key_hex
from .receipt import Receipt, ReceiptPayload, VerifyResult, sign_report, verify_receipt

__all__ = [
    "Receipt",
    "ReceiptPayload",
    "VerifyResult",
    "sign_report",
    "verify_receipt",
    "SigningKeyError",
    "load_or_create_signing_key",
    "public_key_hex",
    "key_id",
]
