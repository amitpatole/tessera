# Tessera — repo working notes

This repo is governed by the global cadence and non-negotiables in **`~/.claude/CLAUDE.md`** (read
it; it overrides defaults) and the organism context in **`~/.claude/ORGANISM.md`**. This stub only
records what is specific to Tessera.

## What Tessera is

Tessera is **Amit's flagship Forward Deployed Engineer (FDE) showcase**, not a Verel organ. It is a
*consumer* of the `agentsensory` contract (`Report = verdict + grounded issues + signed Handoff`),
applied to one hard problem: **attested NL→analytics over a governed General Ledger**. Every numeric
answer ships with the executed SQL, an **independent** runtime verdict, and an Ed25519-signed,
auditor-verifiable receipt.

Full spec (decision trail, prior-art positioning, the 8 failure classes, receipt design, phased
build plan, demo script): **`~/Resume/FDE_Prep/02_TESSERA_FLAGSHIP.md`**.

## Non-negotiables specific to this repo

- **The verifier MUST be independent / orthogonal.** Re-running the model's own SQL to "check" it is
  circular and counts as fraud. Each failure class has a check an auditor could perform by hand, and
  a pinned regression test.
- **No string-built SQL, ever.** Parameterized queries only, executed under a **read-only** warehouse
  role. Validate any identifier/shape before it reaches the query.
- **No default/hardcoded signing secret.** The per-install Ed25519 signing key resolves
  env → persisted key at `~/.config/tessera/signing_key` (chmod 600) → fail closed. Never commit a
  key; `*.key`/`signing_key` are git-ignored.
- **Constant-time comparison** (`hmac.compare_digest`) for any signature/token check.
- **Keep the base wheel light** — FastAPI/LangGraph/psycopg/cryptography live behind extras (`api`,
  `llm`, `crypto`) and are lazy-imported.
- **Verification-first:** nothing is "done" until the verifier returns a verdict and the gate (ruff +
  mypy + pytest, the way CI runs them) is green.

## Hosting (free)

- **Frontend** (minimal Next.js) → **Cloudflare Pages** at `tessera.amitinfotech.net`.
- **Backend + Postgres + verifier** → **Oracle Cloud Always Free** ARM VM (persistent, free), fronted
  by Cloudflare DNS/TLS at `api.tessera.amitinfotech.net`. Doubles as live proof of the self-hosted
  story. Alternative: Google Cloud Run (scale-to-zero) + Neon free Postgres.
- No PyPI / Hugging Face for this project (per owner).
