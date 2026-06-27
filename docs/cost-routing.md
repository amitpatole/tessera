# Cost-cascade routing

Verified trust, at a lower bill. The verifier makes "cheap model first" **safe** — so you only pay for
the expensive model on the questions that actually need it.

## The policy

```
for tier in cheapest → most expensive:
    answer = tier.plan(question)
    if verifier(answer) is PASS:   accept ✓        # cheap win
    else:                          escalate        # only when wrong
```

Cheap-first is safe *because* the independent verifier gates it: a cheap answer is accepted **only**
when the orthogonal recompute passes it, so cost is traded for nothing — never for correctness.

## The numbers

```bash
tessera bench
```
```
  accuracy: 100%   cheap-wins: 3/6   escalations: 3/6
  cascade cost $0.029910  vs always-strong $0.043040  →  30.5% saved, with no loss of correctness.
```

A single escalated question honestly costs *more* than going straight to the strong model; the win is
**in aggregate**, and correctness is never sacrificed.

## Pluggable model tiers — real, not simulated

`ModelTier` is a one-method interface, and the real tiers are wired in. A model **never writes SQL** —
it only resolves the question to a certified metric + scope, and Tessera builds the trusted,
parameterized SQL. That is what makes a small, cheap, sometimes-wrong model **safe** to put first: it
can mis-resolve (caught by the verifier), but it can't inject SQL or invent a metric.

```bash
# Local, air-gapped — a small Ollama model as the cheap tier, certified reference as the escalation:
TESSERA_OLLAMA_MODEL=qwen2.5:0.5b tessera ask "consolidated net revenue in 2025" --route --real

# Cloud — a real OpenAI cascade (cheap gpt-4o-mini → strong gpt-4o):
OPENAI_API_KEY=sk-… tessera ask "net revenue for ACME Brazil in 2025" --route --real
```

A real run (Ollama `qwen2.5:0.5b`): the model nails the consolidated question (**cheap win**), and
mis-resolves a single-entity one — the verifier catches it and the cascade escalates to the correct
answer. Without a model configured, `--real` falls back to the deterministic simulation, so CI and the
offline demo stay reproducible. On the server, set `TESSERA_REAL_MODELS=1` (plus the model env) to use
real tiers for `/ask?route=true`.

- **Ollama** — local, air-gapped, no egress (`TESSERA_OLLAMA_MODEL`).
- **OpenAI** — cloud (`OPENAI_API_KEY`; `TESSERA_OPENAI_CHEAP` / `TESSERA_OPENAI_STRONG`).
- **AWS Bedrock** — same interface, integration-ready.

The cross-workload optimization that *chooses* the cascade builds on
[*Quantum-Enhanced LLM Cascade Routing: A QAOA Approach to Cost-Optimal Model Selection*](https://doi.org/10.5281/zenodo.19253980);
this executes the cascade per query and measures the saving.

!!! note
    Costs are estimated in USD from token counts; in deployment they are real per-token prices.
