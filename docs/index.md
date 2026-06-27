# Tessera

**Every number, proven — not promised.**

Tessera is attested natural-language analytics for regulated finance. Ask a question in plain English
over a governed General-Ledger warehouse and get back not just a number, but **the evidence it is
right**: the exact executed SQL, an **independent** runtime verdict, and a signed, auditor-verifiable
receipt.

- **Live demo:** [tessera.amitinfotech.net](https://tessera.amitinfotech.net)
- **Source:** [github.com/amitpatole/tessera](https://github.com/amitpatole/tessera)

---

## The problem this solves

Finance already has chatbots. It doesn't have **trust**. Every text-to-SQL assistant proves itself
*offline* — "95% accurate on a benchmark." In a regulated report that means **5% is wrong and you
don't know which 5%**, and the cost of that 5% is a restatement or an audit finding — not a shrug. So
finance teams either distrust the tool or pay an analyst to re-check every number, which kills
self-service.

Tessera removes the blocker: it proves **each answer, at runtime**, and hands you a receipt your
auditors verify offline — without trusting the system that produced it.

## Why it's not just another chatbot

| | Generic copilot | Text-to-SQL assistant | **Tessera** |
|---|---|---|---|
| Runs real SQL on governed data | ✗ | ✓ | ✓ |
| Proves *this* answer correct, at runtime | ✗ | ✗ (offline only) | **✓ per answer** |
| Catches named finance mistakes | ✗ | ✗ | **✓ 8 failure classes** |
| Auditor-verifiable evidence | ✗ | ✗ | **✓ signed receipt** |
| Fails honest (no number vs. a wrong one) | ✗ | partial | **✓ WARN, never fabricates** |
| Runs fully air-gapped | rarely | rarely | **✓** |

The differentiator is **structural**: an *independent* verifier (re-running the model's own SQL to
"check" it is circular and worthless), a *per-answer runtime* verdict, and a *cryptographic receipt*.

!!! note "What it honestly is not"
    Tessera proves a number *reconciles to the **certified** metric definition* — not metaphysical
    truth. If the semantic layer is defined wrong, agent and verifier agree on a wrong-but-consistent
    number; governing those definitions is a human responsibility (and building them with the customer
    is the real consulting work). It is for **enumerable, structured analytics** (GL / financial
    metrics), not open-ended document reasoning.

## Start here

- [Quickstart](quickstart.md) — install, ask, verify.
- [How it works](how-it-works.md) — ask → verify independently → attest.
- [The 8 failure classes](failure-classes.md) — the verifier's reason to exist.
- [The demo](demo.md) — watch it catch a wrong number.
- [Why I built this](why.md) — telecom → finance, and the trust problem in both.
