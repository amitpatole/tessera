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

## The intent — why this exists

> **Goal: make a natural-language finance answer something you can *act on without re-checking* — by
> shipping the proof of correctness with the number itself.**

Plenty of chatbots already answer questions over financial data. They are not the problem. The
problem is that **none of them can prove a *specific* answer is correct at the moment they give it to
you** — and in regulated finance that proof *is* the job. A "95%-accurate" assistant means 5% of a
board deck or a regulatory filing is wrong and you don't know which 5%; the cost of that 5% is a
restatement or an audit finding, not a shrug. So today finance teams either distrust the assistant or
pay an analyst to re-check every number — which destroys the value of self-service.

Tessera's intent is to remove that blocker: turn an answer into a **verified, attested artifact** so
finance and audit can actually sign off on AI-driven self-service.

## Why this isn't just another chatbot

|  | Generic LLM copilot | Text-to-SQL assistant *(Cortex Analyst, Genie, Wren, Vanna)* | **Tessera** |
|---|---|---|---|
| Runs real SQL on governed data | ✗ (RAG / docs) | ✓ | ✓ |
| Proves *this* answer correct, at runtime | ✗ | ✗ — trust is offline/statistical | **✓ independent verdict per answer** |
| Catches *named* finance mistakes (intercompany, FX, grain…) | ✗ | ✗ | **✓ 8 enumerable failure classes** |
| Auditor-verifiable evidence trail | ✗ | ✗ | **✓ signed receipt, verified offline** |
| Fails honest (no number vs. a confident wrong one) | ✗ | partial | **✓ `WARN`, never fabricates** |
| Runs fully air-gapped (regulated reality) | rarely | rarely | **✓** |

The differentiator is **structural, not cosmetic**: an *independent* verifier (re-running the model's
own SQL to "check" it is circular and worthless), a *per-answer runtime* verdict, and a *cryptographic
receipt*. That combination is the gap every incumbent leaves open.

**What it is honestly not.** Tessera proves a number *reconciles to the **certified** metric
definition* — not metaphysical truth. If the semantic layer is defined wrong, agent and verifier agree
on a wrong-but-consistent number; governing those definitions is a human responsibility (and building
them with the customer is the real consulting work). It is built for **enumerable, structured
analytics** (GL / financial metrics), not open-ended document reasoning — the failure-class approach
works precisely because finance math has *nameable* ways to be wrong.

---

## See it in 90 seconds (the demo)

The story is *trust*, told in four beats — the third is the one that matters.

```bash
# 1) A clean answer — verified PASS, with the SQL that produced it.
tessera ask "What was consolidated net revenue in 2025?"
#   → PASS  5,293,985.00 USD   (reconciles to the certified metric)

# 2) THE HERO MOMENT — a wrong number, caught by name, before it reaches a report.
tessera ask "What was consolidated net revenue in 2025?" --inject intercompany_double_count
#   → FAIL  claimed 5,439,001.00 vs certified 5,293,985.00 (off by 145,016.00)
#           [intercompany_double_count] the query forgot to eliminate intercompany on consolidation
#   This is the moment a typical assistant would have shown 5,439,001 as fact.

# 3) The receipt — an auditor verifies the answer offline, without trusting Tessera.
tessera ask "What was consolidated net revenue in 2025?" --receipt r.json && tessera verify r.json
#   → VALID   (tamper with any field and it goes INVALID)

# 4) The economics — cheap model first, escalate only when the verifier isn't satisfied.
tessera bench
#   → 30.5% cheaper than always-strong, at 100% accuracy
```

The whole pitch in one line: **the assistant answers, an *independent* verifier decides whether to
trust it, and a signed receipt lets someone else check the work later.** (Full per-feature commands are
below; the same flow runs in the [web UI](web/), over MCP (`tessera mcp`), and over
[REST](deploy/README.md).)

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

- **Phase 0 ✅** — repository scaffold and the shared-contract foundation (the 8 `FailureClass`
  values, `LedgerIssue`, `LedgerReport`).
- **Phase 1 ✅** — the governed General-Ledger warehouse. A deterministic, balanced, multi-entity,
  multi-currency ledger (`tessera.ledger`) plus the certified-metric semantic layer
  (`tessera.semantic`). The books *balance* — `tessera dataset verify` runs the structural invariants
  and returns a PASS/FAIL verdict, and the orthogonal metric rollup agrees with direct SQL.
- **Phase 2 ✅** — the NL→SQL agent (`tessera.agent`). A plain-English question resolves to a
  *certified* metric + scope, generates **parameterized** SQL (structure from the trusted semantic
  layer, values bound as params — never string-built), executes it against the read-only warehouse,
  and returns the number with the SQL. A question outside the semantic layer returns an honest `WARN`,
  never a guessed number.
- **Phase 3 ✅** — the **independent verifier** (`tessera.verifier`), the core. It recomputes the
  answer by an **orthogonal path** (rolls the certified metric up directly from the warehouse — a
  different engine than the agent's SQL, and never derived from it), reconciles the claim against it,
  and on a divergence **diagnoses which of the 8 failure classes** produced the wrong number, showing
  both figures. Verified: it catches **8/8** injected failure classes and passes correct answers with
  no false positives.
- **Phase 4 ✅** — the **signed receipt** (`tessera.receipt`). The verdict + executed SQL + answer +
  issue digest are bound under an **Ed25519** signature from a per-install key, and `tessera verify`
  re-checks it **offline** — so an auditor trusts the receipt, not the assistant. Built to the
  security non-negotiables: no default secret (key resolves `env → ~/.config/tessera/signing_key
  (0600) → create → fail closed`), constant-time signer-identity check, tamper-evident binding.
- **Phase 5 ✅** — **cost-cascade routing** (`tessera.routing`). Try the cheapest model tier first;
  accept its answer **only if the independent verifier passes it**; escalate to a pricier tier only
  when it doesn't. The verifier is what makes cheap-first safe. On a mixed question set the cascade
  saves **~30% at 100% accuracy** vs always using the strong model. Builds on
  [*Quantum-Enhanced LLM Cascade Routing* (QAOA)](https://doi.org/10.5281/zenodo.19253980), which
  chooses the cascade; this executes it and measures the saving.
- **Phase 6 ✅** (deployable) — the **REST API** (`tessera.api`) over the verified pipeline, plus a
  container and both deploy targets. Fail-closed posture: a non-loopback bind without
  `TESSERA_API_TOKEN` refuses to start; with a token, every request needs a constant-time-checked
  bearer; the API takes natural-language questions, never SQL. One image runs **Cloud Run** (cloud
  demo) or fully **air-gapped** (Compose/k3s + Ollama, no egress). See [`deploy/`](deploy/README.md).
- **Phase 7 ✅** — the **minimal UI** ([`web/`](web/README.md), Next.js, 3 components: ask /
  answer+verdict / evidence drawer; reuses the "Warm Paper" design system) and an **MCP server**
  (`tessera.mcp`) exposing `tessera_ask` / `tessera_verify`. The browser only calls a same-origin
  proxy, so the API token never reaches the client. UI graded **PASS** by AgentVision (desktop +
  mobile, zero defects).

## Try the warehouse

```bash
pip install -e ".[dev]"
tessera dataset verify          # the Phase 1 verdict: do the books balance?
tessera dataset build --out tessera.db
sqlite3 tessera.db "SELECT name FROM sqlite_master WHERE type='table';"
```

`dataset verify` prints, for the seeded ledger:

```
  [PASS] account_mapping             all accounts map to a statement line with a consistent normal balance
  [PASS] entry_balanced              all 1425 entries balance
  [PASS] trial_balance_per_entity    posted trial balance balances for every entity
  [PASS] trial_balance_consolidated  consolidated posted debits == credits == 16876188.60
  [PASS] accounting_equation         Assets == Liabilities + Equity + Net income (statements roll up)

verdict: PASS — the books are real
```

## Ask a question

```bash
tessera ask "What was consolidated net revenue in 2025?"
```
```
  answer:  5,293,985.00 USD
  verdict: WARN  (net_revenue (consolidated, 2025) = 5,293,985.00 USD — unverified.)

  executed SQL:
    SELECT COALESCE(SUM((l.credit_func_minor - l.debit_func_minor)), 0) AS minor
    FROM fact_journal_line l JOIN fact_journal_entry e ON ... JOIN dim_period p ON ...
    WHERE a.statement_line IN ('revenue') AND e.status IN ('posted')
      AND e.is_intercompany = 0 AND p.fiscal_year = 2025

  verdict: PASS  (net_revenue = 5,293,985.00 USD reconciles to the certified metric.)
```

## Catch a wrong number

The verifier is independent — it never re-runs the model's SQL to "check" it. Inject any of the 8
failure classes and watch it get caught, by name, with both numbers:

```bash
tessera ask "What was consolidated net revenue in 2025?" --inject intercompany_double_count
```
```
  answer:  5,439,001.00 USD
  verdict: FAIL  (claimed 5,439,001.00 USD vs certified 5,293,985.00 USD (off by 145,016.00 USD).)
    - [intercompany_double_count] Does not reconcile: claimed 5,439,001.00 USD equals the value
      produced by 'intercompany_double_count'. The certified net_revenue is 5,293,985.00 USD.
```

The injected SQL is a genuinely different query (it drops the `is_intercompany = 0` elimination); the
verifier recomputes the truth orthogonally and names the mistake. The eight classes: `wrong_period_grain`,
`missing_entity_filter`, `debit_credit_sign_flip`, `intercompany_double_count`, `draft_or_reversed_entries`,
`wrong_statement_line_rollup`, `fx_mixing`, `asof_vs_ptd`.

## Sign and verify a receipt

```bash
tessera ask "What was consolidated net revenue in 2025?" --receipt receipt.json
tessera verify receipt.json --expect-key <public_key_from: tessera key>
```

`verify` is offline and needs no warehouse access. Tampering with any bound field (answer, verdict,
SQL, …) invalidates the signature.

**Trust model (honest).** A receipt proves *"these independent checks ran and this number reconciles
to the certified metric, signed by this key"* — not metaphysical truth. Verifying **with** a pinned
key (`--expect-key`) gives authenticity (a specific signer produced it). Verifying **without** one
gives integrity only (the bytes are internally consistent) — anyone can mint a self-signed receipt,
so always pin the key out-of-band. Residual risks no signature removes: a wrong *certified metric
definition* (governance), replay of a genuine receipt (consumers should track `receipt_id`),
dependencies / OS, and questions outside the modelled metrics (which return `WARN`, not false
confidence).

## Spend less without trusting the cheap model

```bash
tessera ask "net revenue for ACME Brazil in 2025" --route   # cheap tier passes verification → cheap win
tessera ask "What was consolidated net revenue in 2025?" --route  # cheap fails → escalate to strong
tessera bench                                                # cost vs always-strong, across a mix
```
```
  accuracy: 100%   cheap-wins: 3/6   escalations: 3/6
  cascade cost $0.029910  vs always-strong $0.043040  →  30.5% saved, with no loss of correctness.
```

Cheap-first is only safe because the verifier is the gate: a cheap answer is accepted *only* when the
orthogonal recompute passes it, so the cascade trades cost for nothing. (Costs are estimated in USD
from token counts; in deployment they are real per-token prices. The cross-workload optimization that
*chooses* the cascade is the QAOA cost-routing work above.)

## Run the API

```bash
pip install -e ".[api,crypto]"
tessera serve                       # http://127.0.0.1:8080 — loopback is zero-config
curl -s localhost:8080/health
curl -s -X POST localhost:8080/ask -H 'Content-Type: application/json' \
  -d '{"question":"What was consolidated net revenue in 2025?","sign":true}'
```

Binding a routable interface **fails closed** without a token: `TESSERA_API_TOKEN=$(openssl rand -hex
16) tessera serve --host 0.0.0.0` then send `Authorization: Bearer <token>`. One image runs Cloud Run
or fully air-gapped — see [`deploy/README.md`](deploy/README.md).

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
