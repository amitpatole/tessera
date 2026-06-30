# Attested inference on PyTorch

Tessera's cost cascade can run its cheap first tier on a **real PyTorch model** — either in-process
(`torch.nn.Module` via 🤗 Transformers) or served by [vLLM](https://github.com/vllm-project/vllm), a
PyTorch Foundation project. This is the demonstrator behind the *attested inference* idea: a small,
cheap, sometimes-wrong PyTorch model is made **safe to put first** because an independent verifier
catches its misses and the cascade escalates, and every accepted answer ships with a signed receipt
you verify offline.

The model never writes SQL. It only resolves a question to a *certified* metric + scope; Tessera
builds the trusted, parameterized SQL. So the model can mis-resolve (caught by the verifier) but can
never inject SQL or invent a metric — that is what makes an unreliable cheap model usable.

## In-process PyTorch (no server, no API key)

```bash
pip install -e '.[pytorch,crypto]'        # torch + transformers + accelerate
python examples/demo_pytorch.py            # first run downloads ~1 GB (Qwen2.5-0.5B-Instruct)
```

By default this loads `Qwen/Qwen2.5-0.5B-Instruct` and generates on CPU. Override the model with
`TESSERA_TORCH_MODEL=<hf-id>`. Real captured output:

```text
PyTorch-backed attested inference
  torch 2.12.1+cpu · device cpu · model Qwen/Qwen2.5-0.5B-Instruct
  (the model only resolves metric+scope; it never writes SQL)

Q: net revenue for ACME Brazil in 2025
  verdict       : PASS
  answer        : 275,557.00 USD
  accepted tier : torch:Qwen/Qwen2.5-0.5B-Instruct  (escalations: 0)
  tiers tried   : torch:Qwen/Qwen2.5-0.5B-Instruct
  cascade cost  : $8.98e-05  vs strong-only $0.00716
  receipt       : signed by d39d4366ba79097f…  offline-verify = OK

Q: What was consolidated net revenue in 2025?
  verdict       : PASS
  answer        : 5,293,985.00 USD
  accepted tier : torch:Qwen/Qwen2.5-0.5B-Instruct  (escalations: 0)
  tiers tried   : torch:Qwen/Qwen2.5-0.5B-Instruct
  cascade cost  : $9.04e-05  vs strong-only $0.0072
  receipt       : signed by d39d4366ba79097f…  offline-verify = OK

Benchmark (this PyTorch tier vs always-routing-to-strong):
  6 questions · accuracy 100.0% · cheap-wins 6/6 · escalations 0/6
  cascade $0.0005422 vs strong-only $0.04304  → 98.74% cheaper, no loss of accuracy
```

A real **0.5B-parameter PyTorch model, generating on CPU**, resolves the whole benchmark correctly —
6/6 cheap wins, 100% accuracy — for **98.74% less** than routing everything to the strong model. Every
answer is signed and verified offline with the public key alone.

**The safety net, made visible.** Swap in a model too weak for the task —
`TESSERA_TORCH_MODEL=HuggingFaceTB/SmolLM2-135M-Instruct` (~270 MB) — and it mis-resolves *every*
question. That is normally a disaster. Here the independent verifier rejects each wrong resolution and
the cascade escalates to the reliable reference tier, so you still get the **correct, signed answer
every time** — you just pay more, which is exactly the signal the cascade is built to read. A cheap
model is never trusted on its own word.

## Serving with vLLM

vLLM exposes an OpenAI-compatible API and runs the model on PyTorch under the hood. Point Tessera at
a running server:

```bash
# Terminal 1 — serve any HF model with vLLM (GPU recommended):
vllm serve Qwen/Qwen2.5-0.5B-Instruct           # listens on http://127.0.0.1:8000/v1

# Terminal 2 — route Tessera's cheap tier through it:
export TESSERA_VLLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct
export TESSERA_VLLM_BASE=http://127.0.0.1:8000/v1
tessera ask "consolidated net revenue in 2025" --route --real --receipt
```

## Using it in the cascade

Set the backend env var and the runtime picks PyTorch automatically (priority order
`torch` → `vllm` → `openai` → `ollama`):

| Backend | Env | Where it runs |
|---|---|---|
| In-process PyTorch | `TESSERA_TORCH_MODEL` | this process, on `torch` |
| vLLM | `TESSERA_VLLM_MODEL` (+ `TESSERA_VLLM_BASE`) | a vLLM server (PyTorch) |
| OpenAI | `OPENAI_API_KEY` | cloud |
| Ollama | `TESSERA_OLLAMA_MODEL` | local Ollama |

On the API server, also set `TESSERA_REAL_MODELS=1` so `/ask?route=true` uses the real tiers. Without
any backend configured, `--real` falls back to the deterministic simulation, so CI and the offline
demo stay reproducible.
