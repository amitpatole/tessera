# How it works

Three steps, and the second is the product.

## 1. Ask

A natural-language question resolves to a **certified metric** and a scope (period grain, entity,
consolidated or not). The query is built from the trusted semantic layer and run as **parameterized,
read-only SQL** — never string-built, never free-form. The agent answers; it does **not** certify.

```
question → resolve to a certified metric + scope → parameterized SQL → execute (read-only) → answer
```

A question outside the certified definitions returns `WARN` — an honest "I don't have a certified
definition for that," never a fabricated number.

## 2. Verify — independently

This is the core. Given the answer, Tessera **recomputes it by an orthogonal path**: it rolls the
certified metric up directly from the warehouse — a *different engine* than the agent's SQL, and
**never derived from that SQL**. Re-running the model's own query to "check" it would be circular and
worthless; Tessera never does that.

If the claim and the orthogonal truth diverge, the verifier **diagnoses which failure class** produced
the wrong number by matching it against the counterfactual value of each
[failure class](failure-classes.md), and reports both figures.

```
truth = rollup(certified metric)        # orthogonal — not the agent's SQL
if |claim − truth| > tolerance:
    name the failure class whose counterfactual == claim   → FAIL
elif required SQL clause missing:
    fragile query, right answer          → WARN
else:                                    → PASS
```

Light SQL-contract heuristics corroborate the diagnosis but never decide the verdict on their own.

## 3. Attest

The verdict, the executed SQL, and the answer are bound into an **Ed25519-signed receipt**. Anyone
re-checks it [offline](receipts.md) — they trust the receipt, not the assistant.

## The shared contract

Internally, every verdict is an [`agentsensory`](https://github.com/amitpatole/agentsensory) `Report`
= **verdict + grounded issues + signed handoff**. Tessera consumes that contract; it does not redefine
it. Issues are grounded in Tessera's dimension — the failure class.

## Architecture

```
                ┌──────────────┐     ┌────────────────────┐     ┌──────────────────┐
  question ───▶ │  agent       │ ──▶ │  independent       │ ──▶ │  receipt         │
                │  (resolve +  │ SQL │  verifier          │     │  (Ed25519 sign)  │
                │   exec SQL)  │     │  (orthogonal       │     │                  │
                └──────────────┘     │   recompute +      │     └──────────────────┘
                       │             │   8 failure checks)│              │
                       ▼             └────────────────────┘              ▼
              governed GL warehouse          ▲                   tessera verify
              (sqlite / Postgres)            │                   (offline)
                       └──────── certified metric semantic layer ┘
```

The same pipeline is exposed over a [CLI](quickstart.md), a [REST API](deploy.md), and an MCP server,
and runs [cloud or fully air-gapped](deploy.md).
