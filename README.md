# Tessera

**Attested natural-language analytics for regulated finance.**

Ask a finance question in plain English over a governed General-Ledger warehouse and get back not
just a number — but the evidence it is right: the exact executed SQL, an **independent** runtime
verdict, and a signed, auditor-verifiable receipt.

Text-to-SQL is a solved demo and an unsolved product. The reason it has not displaced the analyst
in regulated finance is not fluency — it is **trust**: a confidently wrong number is worse than no
number. Every incumbent proves trust *offline* (benchmark accuracy, sample audits). Tessera proves
it *per answer, at runtime*, and hands you a receipt you can verify after the fact without trusting
the system that produced it.

---

## How it works

1. **Ask** — a natural-language question is planned into SQL and run against a **read-only** role on
   a governed warehouse (parameterized; never string-built).
2. **Verify — independently.** The answer is checked by an orthogonal recompute, not by re-running
   the model's own SQL (that would be circular). Each of the enumerable ways a ledger answer goes
   wrong has its own check and a pinned regression test:

   | Failure class | What it catches |
   |---|---|
   | Wrong period grain | as-of vs period-to-date, month/quarter/year mismatch |
   | Missing entity filter | aggregated across legal entities the question scoped to one |
   | Debit/credit sign flip | inverted sign vs the account's normal balance |
   | Intercompany double-count | both legs counted instead of eliminated on consolidation |
   | Draft / reversed entries | unposted journals or both sides of a reversal included |
   | Wrong statement-line rollup | accounts mapped to the wrong financial-statement line |
   | FX mixing | currencies summed without translation to a reporting currency |
   | As-of vs PTD | a point-in-time balance used where a period-flow was asked |

3. **Attest** — the verdict, the SQL, and the answer are bound into an **Ed25519-signed receipt**.
   `tessera verify` re-checks the signature and the bound result offline, so an auditor trusts the
   receipt, not the assistant.

The verdict vocabulary is the shared [`agentsensory`](https://github.com/amitpatole/agentsensory)
contract: a `Report` is `verdict + grounded issues + signed Handoff`. Tessera consumes that
contract; it does not redefine it.

## Deploy anywhere

The same build runs two ways:

- **Cloud** — AWS (ECS/Lambda) with Bedrock for inference.
- **Air-gapped** — fully self-hosted on k3s/Podman with vLLM or Ollama, no dependence on any public
  AI service. This is the deployment reality regulated finance actually requires.

Model selection is a verdict-driven cost cascade (cheap model first; escalate only when the
independent verifier is not satisfied), building on
[*Quantum-Enhanced LLM Cascade Routing*](https://doi.org/10.5281/zenodo.19253980).

## Status

Phase 0 — repository scaffold and the shared-contract foundation. The warehouse generator, the
independent verifier, the signed-receipt path, the API, and the minimal UI land in subsequent
phases. Nothing here is "done" until it returns a verdict.

## Develop

```bash
pip install -e ".[dev]"
ruff check src tests
mypy src
pytest -q
tessera doctor
```

## License

MIT © 2026 Amit Patole — *built forward-deployed.*
