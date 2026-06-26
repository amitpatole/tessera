"""Deterministic canonical serialization — the exact bytes that get signed and re-checked.

Both the signer and any offline verifier must derive *byte-identical* input from the same payload,
or a valid receipt would fail to verify. Canonical form: JSON with sorted keys, no insignificant
whitespace, UTF-8, JSON-native scalars only (Decimals/enums are already strings/ints in the payload).
"""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel


def canonical_bytes(payload: BaseModel) -> bytes:
    """The signed message: a stable, whitespace-free, key-sorted JSON encoding of the payload."""
    data = payload.model_dump(mode="json")
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
