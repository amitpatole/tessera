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

## Pluggable model tiers

`ModelTier` is a one-method interface. Run it the way your security team allows:

- **Ollama** — local, air-gapped, no egress.
- **OpenAI** / **AWS Bedrock** — cloud.

The cross-workload optimization that *chooses* the cascade builds on
[*Quantum-Enhanced LLM Cascade Routing: A QAOA Approach to Cost-Optimal Model Selection*](https://doi.org/10.5281/zenodo.19253980);
this executes the cascade per query and measures the saving.

!!! note
    Costs are estimated in USD from token counts; in deployment they are real per-token prices.
