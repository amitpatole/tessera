"""The signed receipt: bind the verdict + the result, sign it, verify it offline.

The signature commits to the *actual outcome* — question, metric, scope, the executed SQL, the
answer, the verdict, and a digest of the grounded issues. You cannot alter any of these without
invalidating the signature, so an auditor trusts the receipt rather than the assistant that produced
it. ``verify_receipt`` is offline and side-effect-free; pinning the expected public key turns an
integrity check (the bytes are intact) into an authenticity check (this signer produced them), using
a constant-time comparison.
"""

from __future__ import annotations

import datetime as _dt
import hmac
import secrets

from pydantic import BaseModel, Field

from ..contract import LedgerReport
from ..ledger.controls import Scope
from .canonical import canonical_bytes, sha256_hex
from .keys import key_id, load_or_create_signing_key


def _now_iso() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat()


def _issues_digest(report: LedgerReport) -> str:
    items = [
        {"kind": i.kind.value, "severity": i.severity.value, "message": i.message, "source": i.source}
        for i in report.issues
    ]
    import json

    return sha256_hex(json.dumps(items, sort_keys=True, separators=(",", ":")).encode("utf-8"))


class ReceiptPayload(BaseModel):
    """Exactly what the signature commits to — the bound, attested result."""

    schema_version: str = "1.0"
    receipt_id: str
    issued_at: str
    question: str
    metric: str
    scope: dict
    executed_sql: str
    answer: str
    verdict: str
    issues_digest: str
    dataset_seed: int


class Receipt(BaseModel):
    """A signed attestation: the payload plus everything needed to verify it offline."""

    payload: ReceiptPayload
    algorithm: str = "Ed25519"
    key_id: str
    public_key: str = Field(description="Signer's Ed25519 public key, hex (raw 32 bytes).")
    signature: str = Field(description="Ed25519 signature over the canonical payload, hex.")
    payload_sha256: str


class VerifyResult(BaseModel):
    valid: bool
    reason: str
    key_id: str
    verdict: str
    authenticity_checked: bool = False


def sign_report(
    report: LedgerReport,
    *,
    metric_name: str,
    scope: Scope,
    dataset_seed: int,
    issued_at: str | None = None,
    private_key: object | None = None,
) -> Receipt:
    """Bind a verified report into a signed :class:`Receipt` (resolves the per-install key if needed)."""
    payload = ReceiptPayload(
        receipt_id=secrets.token_hex(16),
        issued_at=issued_at or _now_iso(),
        question=report.question,
        metric=metric_name,
        scope=scope.model_dump(),
        executed_sql=report.executed_sql or "",
        answer=report.answer or "",
        verdict=report.verdict.value,
        issues_digest=_issues_digest(report),
        dataset_seed=dataset_seed,
    )
    priv = private_key if private_key is not None else load_or_create_signing_key()
    message = canonical_bytes(payload)
    signature = priv.sign(message)  # type: ignore[attr-defined]
    public_raw = priv.public_key().public_bytes_raw()  # type: ignore[attr-defined]
    return Receipt(
        payload=payload,
        key_id=key_id(public_raw),
        public_key=public_raw.hex(),
        signature=signature.hex(),
        payload_sha256=sha256_hex(message),
    )


def verify_receipt(receipt: Receipt, *, expected_public_key: str | None = None) -> VerifyResult:
    """Offline-verify a receipt: the signature binds the payload, and (optionally) the signer is the
    one you pinned. No analysis is re-run; this checks the attestation's integrity and authenticity."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    message = canonical_bytes(receipt.payload)

    # Integrity of the convenience digest (cheap, catches gross tampering / transport corruption).
    if sha256_hex(message) != receipt.payload_sha256:
        return VerifyResult(valid=False, reason="payload_sha256 does not match the payload",
                            key_id=receipt.key_id, verdict=receipt.payload.verdict)

    # Authenticity: if the caller pinned a key, the receipt's key must match it (constant-time).
    authenticity_checked = expected_public_key is not None
    if authenticity_checked:
        if not hmac.compare_digest(receipt.public_key.lower(), str(expected_public_key).lower()):
            return VerifyResult(valid=False, reason="signer public key does not match the expected key",
                                key_id=receipt.key_id, verdict=receipt.payload.verdict,
                                authenticity_checked=True)

    # Signature: does the embedded public key actually sign these exact bytes?
    try:
        public = Ed25519PublicKey.from_public_bytes(bytes.fromhex(receipt.public_key))
        public.verify(bytes.fromhex(receipt.signature), message)
    except (InvalidSignature, ValueError):
        return VerifyResult(valid=False, reason="invalid Ed25519 signature over the payload",
                            key_id=receipt.key_id, verdict=receipt.payload.verdict,
                            authenticity_checked=authenticity_checked)

    reason = ("signature valid and signer matches the expected key" if authenticity_checked
              else "signature valid; signer identity not pinned (pass --expect-key to assert it)")
    return VerifyResult(valid=True, reason=reason, key_id=receipt.key_id,
                        verdict=receipt.payload.verdict, authenticity_checked=authenticity_checked)
