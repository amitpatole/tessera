# Quickstart

Tessera runs entirely offline and key-free against a synthetic, deterministically-generated General
Ledger — no warehouse to provision, no API key to ask a question.

## Install

```bash
git clone https://github.com/amitpatole/tessera
cd tessera
pip install -e ".[dev]"
```

## Verify the books (the Phase-1 verdict)

```bash
tessera dataset verify
```
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
  verdict: PASS  (net_revenue = 5,293,985.00 USD reconciles to the certified metric.)
```

## Catch a wrong number

Inject any of the [eight failure classes](failure-classes.md) and watch the independent verifier catch
it, by name:

```bash
tessera ask "What was consolidated net revenue in 2025?" --inject intercompany_double_count
```
```
  verdict: FAIL  (claimed 5,439,001.00 USD vs certified 5,293,985.00 USD (off by 145,016.00 USD).)
    - [intercompany_double_count] … equals the value produced by 'intercompany_double_count'.
```

## Sign and verify a receipt

```bash
tessera ask "What was consolidated net revenue in 2025?" --receipt receipt.json
tessera verify receipt.json --expect-key "$(tessera key | sed -n 's/public_key: //p')"
```

## The commands

| Command | What it does |
|---|---|
| `tessera dataset build\|verify` | build the sqlite warehouse / run the book invariants |
| `tessera ask "…" [--route] [--inject CLASS] [--receipt PATH]` | ask, verify, optionally route/sign |
| `tessera verify <receipt> [--expect-key HEX]` | offline-verify a signed receipt |
| `tessera key` | show the signing public key (share it so auditors can pin it) |
| `tessera bench` | benchmark the cost cascade vs an always-strong baseline |
| `tessera serve` | run the REST API (needs the `api` extra) |
| `tessera mcp` | run the MCP server (needs the `mcp` extra) |
