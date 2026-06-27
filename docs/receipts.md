# Signed receipts & the trust model

A verdict you can't take with you isn't worth much. Tessera binds every answer into an **Ed25519
receipt** that an auditor verifies **offline** — no warehouse, no network, no trust in Tessera.

## What the signature commits to

The receipt binds the *actual outcome*: the question, the certified metric, the scope, the **executed
SQL**, the **answer**, the **verdict**, a digest of the grounded issues, and the dataset identity.
Change any one of them and verification fails.

```bash
tessera ask "What was consolidated net revenue in 2025?" --receipt receipt.json
tessera verify receipt.json
```
```
  [VALID] signature valid; signer identity not pinned (pass --expect-key to assert it)
  attested verdict: PASS   signer key_id: e1bcdef0b7e4ca53
```

Pin the signer to turn an integrity check into an authenticity one (constant-time):

```bash
tessera verify receipt.json --expect-key <public-key-from: tessera key>
```

## The key model — no default secret

The per-install Ed25519 signing key resolves:

1. `TESSERA_SIGNING_KEY` (env), else
2. a persisted key at `~/.config/tessera/signing_key` (created `0600` in a `0700` dir, atomically with
   `O_NOFOLLOW`), else
3. **fail closed.**

There is no hardcoded or default signing secret anywhere — a public default key would let anyone forge
receipts. The key is never logged and never committed.

## The trust model, stated honestly

A receipt proves *"these independent checks ran and this number reconciles to the certified metric,
signed by this key"* — **not** metaphysical truth.

- **With** a pinned key (`--expect-key`): authenticity — a specific signer produced it.
- **Without** one: integrity only — the bytes are internally consistent. Anyone can mint a self-signed
  receipt, so **always pin the key out-of-band.**

Residual risks no signature removes: a wrong *certified metric definition* (governance), replay of a
genuine receipt (consumers should track `receipt_id`), dependencies / OS, and questions outside the
modelled metrics (which return `WARN`, not false confidence).

## Security cadence

The signing/key path went through the project's security cadence — audit → fix → empirically proved
(a CLI forgery of the answer returns `INVALID`) → regression pins (tamper, wrong-key, fail-closed,
per-install randomness, `0600` perms, env-key-not-persisted) → red-team rounds (added `O_NOFOLLOW`).
