#!/usr/bin/env python3
"""Attested inference on a **real PyTorch model** — the cheap tier of the cost cascade.

This runs a small language model *in-process on PyTorch* (a ``torch.nn.Module`` loaded with 🤗
Transformers, generating on CPU) as the cheap first tier of Tessera's cost cascade. The model only
resolves a finance question to a *certified* metric + scope — it never writes SQL. Tessera builds the
trusted, parameterized SQL, an **independent verifier** recomputes the answer by an orthogonal path,
and the final answer ships with an **Ed25519-signed receipt** you verify fully offline.

The point the poster makes, demonstrated live: a small PyTorch model is *cheap but fallible* — it
sometimes mis-resolves a hard (consolidation) question. That is normally unsafe. Here it is safe,
because the verifier catches the miss and the cascade escalates to the reliable reference tier. You
trade cost for nothing; never for correctness.

Run (no API key, fully local):

    pip install -e '.[pytorch,crypto]'
    python examples/demo_pytorch.py

The first run downloads ~1 GB for the default model (Qwen/Qwen2.5-0.5B-Instruct). Override with
TESSERA_TORCH_MODEL=<hf-id> — e.g. the lighter HuggingFaceTB/SmolLM2-135M-Instruct (~270 MB), which
is too weak to resolve these questions, so every one escalates: the verifier still catches every miss
and you get correct, signed answers — the safety net the cascade is built on.
"""

from __future__ import annotations

import os

# Route the cascade through the in-process PyTorch tier (see tessera.routing.tiers.cascade_tiers).
os.environ.setdefault("TESSERA_TORCH_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")

import torch  # noqa: E402 — imported after env so the message below reflects the real device

from tessera.runtime import Runtime  # noqa: E402

QUESTIONS = [
    "net revenue for ACME Brazil in 2025",      # single entity — the small model usually nails it
    "What was consolidated net revenue in 2025?",  # consolidation — where a small model tends to slip
]


def main() -> None:
    print("PyTorch-backed attested inference")
    print(f"  torch {torch.__version__} · device "
          f"{'cuda' if torch.cuda.is_available() else 'cpu'} · "
          f"model {os.environ['TESSERA_TORCH_MODEL']}")
    print("  (the model only resolves metric+scope; it never writes SQL)\n")

    rt = Runtime()
    try:
        for q in QUESTIONS:
            out = rt.ask(q, route=True, real=True, sign=True)
            routing = out["routing"] or {}
            tiers_tried = " → ".join(a["tier"] for a in routing.get("attempts", []))
            print(f"Q: {q}")
            print(f"  verdict       : {out['verdict'].upper()}")
            print(f"  answer        : {out['answer']}")
            print(f"  accepted tier : {routing.get('accepted_tier')}  "
                  f"(escalations: {routing.get('escalations')})")
            print(f"  tiers tried   : {tiers_tried}")
            print(f"  cascade cost  : ${routing.get('total_cost_usd')}  "
                  f"vs strong-only ${routing.get('baseline_cost_usd')}")

            # The receipt is signed over the verified result; verify it offline (public key only).
            receipt = out["receipt"]
            verified = rt.verify_receipt(receipt)
            print(f"  receipt       : signed by {receipt['public_key'][:16]}…  "
                  f"offline-verify = {'OK' if verified['valid'] else 'INVALID'}\n")
    finally:
        rt.close()

    # The money KPI: the whole benchmark through this same PyTorch tier vs always-strong.
    from tessera.routing.bench import run_benchmark
    from tessera.routing.tiers import cascade_tiers

    bench = run_benchmark(tiers=cascade_tiers())
    print("Benchmark (this PyTorch tier vs always-routing-to-strong):")
    print(f"  {bench.n} questions · accuracy {bench.accuracy_pct}% · "
          f"cheap-wins {bench.cheap_wins}/{bench.n} · escalations {bench.escalations}/{bench.n}")
    print(f"  cascade ${bench.total_cost_usd} vs strong-only ${bench.baseline_cost_usd}  "
          f"→ {bench.pct_saved}% cheaper, no loss of accuracy")


if __name__ == "__main__":
    main()
