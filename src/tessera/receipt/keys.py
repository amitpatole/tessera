"""Per-install Ed25519 signing-key resolution — the secret-handling boundary.

Resolution order, per the non-negotiables (CLAUDE.md): an explicit env key, else a persisted
per-installation random key under ``~/.config/tessera/``, else **create** one, else **fail closed**.
There is no hardcoded or default signing secret anywhere — a public default key would let anyone
forge receipts.

The key never touches the repo and is never logged. The private file is created `0600` inside a
`0700` directory via an atomic ``os.open`` (so it is never briefly world-readable), and an existing
file with looser permissions is re-tightened with a loud warning.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_ENV_KEY = "TESSERA_SIGNING_KEY"
_ENV_CONFIG_DIR = "TESSERA_CONFIG_DIR"
_KEY_FILENAME = "signing_key"


class SigningKeyError(RuntimeError):
    """Raised when a signing key cannot be resolved and creation is not permitted (fail closed)."""


def _require_cryptography():
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise SigningKeyError(
            "signing requires the 'crypto' extra: pip install 'tessera-analytics[crypto]'"
        ) from exc
    return ed25519


def config_dir() -> Path:
    """The directory holding the per-install key (override via ``TESSERA_CONFIG_DIR`` for tests)."""
    override = os.environ.get(_ENV_CONFIG_DIR)
    return Path(override) if override else Path.home() / ".config" / "tessera"


def key_path() -> Path:
    return config_dir() / _KEY_FILENAME


def key_id(public_raw: bytes) -> str:
    """A short, stable identifier for a public key — the first 16 hex chars of its SHA-256."""
    return hashlib.sha256(public_raw).hexdigest()[:16]


def _seed_from_env(ed25519) -> Ed25519PrivateKey | None:
    raw = os.environ.get(_ENV_KEY)
    if not raw:
        return None
    try:
        seed = bytes.fromhex(raw.strip())
    except ValueError as exc:
        raise SigningKeyError(f"{_ENV_KEY} is not valid hex") from exc
    if len(seed) != 32:
        raise SigningKeyError(f"{_ENV_KEY} must be 32 bytes (64 hex chars), got {len(seed)}")
    return ed25519.Ed25519PrivateKey.from_private_bytes(seed)


def _load_from_file(ed25519) -> Ed25519PrivateKey | None:
    path = key_path()
    if not path.exists():
        return None
    # Re-tighten permissions if something loosened them.
    mode = path.stat().st_mode & 0o777
    if mode != 0o600:
        print(f"tessera: WARNING — {path} had mode {mode:o}; re-securing to 600.", file=sys.stderr)
        os.chmod(path, 0o600)
    seed = path.read_bytes()
    if len(seed) != 32:
        raise SigningKeyError(f"{path} is corrupt: expected 32 bytes, got {len(seed)}")
    return ed25519.Ed25519PrivateKey.from_private_bytes(seed)


def _create_and_persist(ed25519) -> Ed25519PrivateKey:
    priv = ed25519.Ed25519PrivateKey.generate()
    seed = priv.private_bytes_raw()
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    path = key_path()
    # Atomic create with 0600 so the file is never momentarily world-readable. O_NOFOLLOW refuses
    # to follow a symlink planted at the key path (symlink-redirection hardening).
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, seed)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)
    print(
        f"tessera: created a new per-install signing key at {path} (keep it secret; never commit it).",
        file=sys.stderr,
    )
    return priv


def load_or_create_signing_key(*, create: bool = True) -> Ed25519PrivateKey:
    """Resolve the signing key: env → persisted file → create (if allowed) → fail closed."""
    ed25519 = _require_cryptography()
    priv = _seed_from_env(ed25519)
    if priv is not None:
        return priv
    priv = _load_from_file(ed25519)
    if priv is not None:
        return priv
    if not create:
        raise SigningKeyError("no signing key found and creation disabled (fail closed)")
    return _create_and_persist(ed25519)


def public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes_raw().hex()
