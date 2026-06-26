"""Phase 4 + security cadence: signed receipts bind the result, and the key model is sound.

These tests double as the regression pins for the signing/key security review: tamper detection,
authenticity (constant-time, pinned key), fail-closed key resolution, per-install randomness, and
file permissions.
"""

from __future__ import annotations

import os
import stat

import pytest
from agentsensory import Severity, Verdict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tessera.contract import FailureClass, LedgerIssue, LedgerReport
from tessera.ledger.controls import Scope
from tessera.receipt import (
    SigningKeyError,
    load_or_create_signing_key,
    public_key_hex,
    sign_report,
    verify_receipt,
)
from tessera.receipt.keys import key_path

SCOPE = Scope(fiscal_year=2025, consolidated=True)


@pytest.fixture()
def isolated_config(monkeypatch, tmp_path):
    """Point key storage at a temp dir and clear any ambient env key."""
    monkeypatch.setenv("TESSERA_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("TESSERA_SIGNING_KEY", raising=False)
    return tmp_path


def _report(answer: str = "5,293,985.00 USD", verdict: Verdict = Verdict.PASS) -> LedgerReport:
    return LedgerReport(
        verdict=verdict, summary="ok", question="What was consolidated net revenue in 2025?",
        executed_sql="SELECT ... WHERE status='posted' AND is_intercompany=0", answer=answer,
    )


# ---- round trip & binding -------------------------------------------------------------------------


def test_sign_then_verify_round_trips(isolated_config):
    receipt = sign_report(_report(), metric_name="net_revenue", scope=SCOPE, dataset_seed=1)
    result = verify_receipt(receipt)
    assert result.valid
    assert result.verdict == "pass"


def test_signature_binds_the_answer_tampering_is_caught(isolated_config):
    receipt = sign_report(_report(), metric_name="net_revenue", scope=SCOPE, dataset_seed=1)
    receipt.payload.answer = "9,999,999.00 USD"  # forge a better number
    result = verify_receipt(receipt)
    assert not result.valid


def test_signature_binds_the_verdict(isolated_config):
    receipt = sign_report(_report(verdict=Verdict.FAIL), metric_name="net_revenue", scope=SCOPE,
                          dataset_seed=1)
    receipt.payload.verdict = "pass"  # forge a passing verdict
    assert not verify_receipt(receipt).valid


def test_signature_binds_the_issues_digest(isolated_config):
    report = _report(verdict=Verdict.FAIL)
    report.issues = [LedgerIssue.make(FailureClass.FX_MIXING, Severity.ERROR, "currencies mixed")]
    receipt = sign_report(report, metric_name="net_revenue", scope=SCOPE, dataset_seed=1)
    receipt.payload.issues_digest = "0" * 64
    assert not verify_receipt(receipt).valid


# ---- authenticity (pinned key, constant-time) -----------------------------------------------------


def test_pinned_key_authenticates_the_signer():
    signer = Ed25519PrivateKey.generate()
    receipt = sign_report(_report(), metric_name="net_revenue", scope=SCOPE, dataset_seed=1,
                          private_key=signer)
    good = verify_receipt(receipt, expected_public_key=public_key_hex(signer))
    assert good.valid and good.authenticity_checked


def test_wrong_pinned_key_is_rejected():
    signer = Ed25519PrivateKey.generate()
    attacker = Ed25519PrivateKey.generate()
    receipt = sign_report(_report(), metric_name="net_revenue", scope=SCOPE, dataset_seed=1,
                          private_key=signer)
    bad = verify_receipt(receipt, expected_public_key=public_key_hex(attacker))
    assert not bad.valid and bad.authenticity_checked


def test_resigned_payload_with_attacker_key_fails_pinning():
    """An attacker who alters the payload must re-sign with their own key — pinning catches it."""
    signer = Ed25519PrivateKey.generate()
    attacker = Ed25519PrivateKey.generate()
    receipt = sign_report(_report(), metric_name="net_revenue", scope=SCOPE, dataset_seed=1,
                          private_key=signer)
    # Attacker forges the answer and re-signs with their key, swapping in their public key.
    receipt.payload.answer = "9,999,999.00 USD"
    from tessera.receipt.canonical import canonical_bytes, sha256_hex
    from tessera.receipt.keys import key_id

    msg = canonical_bytes(receipt.payload)
    receipt.signature = attacker.sign(msg).hex()
    receipt.public_key = attacker.public_key().public_bytes_raw().hex()
    receipt.payload_sha256 = sha256_hex(msg)
    receipt.key_id = key_id(bytes.fromhex(receipt.public_key))
    # Self-consistent now, but it is NOT the pinned signer → rejected.
    assert not verify_receipt(receipt, expected_public_key=public_key_hex(signer)).valid


# ---- key model: no default secret, fail closed, per-install, perms --------------------------------


def test_fail_closed_when_no_key_and_no_creation(isolated_config):
    with pytest.raises(SigningKeyError):
        load_or_create_signing_key(create=False)


def test_per_install_keys_are_random_and_distinct(monkeypatch, tmp_path):
    monkeypatch.delenv("TESSERA_SIGNING_KEY", raising=False)
    monkeypatch.setenv("TESSERA_CONFIG_DIR", str(tmp_path / "a"))
    pub_a = public_key_hex(load_or_create_signing_key())
    monkeypatch.setenv("TESSERA_CONFIG_DIR", str(tmp_path / "b"))
    pub_b = public_key_hex(load_or_create_signing_key())
    assert pub_a != pub_b  # no shared/default secret


def test_created_key_file_is_0600_in_a_0700_dir(isolated_config):
    load_or_create_signing_key()
    path = key_path()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_loosened_key_permissions_are_self_healed(isolated_config):
    load_or_create_signing_key()
    path = key_path()
    os.chmod(path, 0o644)
    load_or_create_signing_key()  # reload
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_env_key_is_used_and_deterministic(monkeypatch, tmp_path):
    seed = "11" * 32  # 32 bytes of 0x11
    monkeypatch.setenv("TESSERA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("TESSERA_SIGNING_KEY", seed)
    pub1 = public_key_hex(load_or_create_signing_key())
    pub2 = public_key_hex(load_or_create_signing_key())
    assert pub1 == pub2
    assert not key_path().exists()  # env key must not be persisted to disk


def test_bad_env_key_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("TESSERA_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("TESSERA_SIGNING_KEY", "not-hex")
    with pytest.raises(SigningKeyError):
        load_or_create_signing_key()


def test_receipt_ids_are_unique_per_signing(isolated_config):
    r1 = sign_report(_report(), metric_name="net_revenue", scope=SCOPE, dataset_seed=1)
    r2 = sign_report(_report(), metric_name="net_revenue", scope=SCOPE, dataset_seed=1)
    assert r1.payload.receipt_id != r2.payload.receipt_id
