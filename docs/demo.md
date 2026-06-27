# The demo

The whole pitch is *trust*, in four beats. The third is the one that sells it. Every block below is
**real captured output** — run it yourself, it's deterministic and key-free.

Try it live at **[tessera.amitinfotech.net](https://tessera.amitinfotech.net)**, or in a terminal:

## Beat 1 — a clean answer, verified

```bash
tessera ask "What was consolidated net revenue in 2025?"
```
```
  answer:  5,293,985.00 USD
  verdict: PASS  (net_revenue = 5,293,985.00 USD reconciles to the certified metric.)

  verified SQL:
    SELECT COALESCE(SUM((l.credit_func_minor - l.debit_func_minor)), 0) AS minor
    FROM fact_journal_line l JOIN ... 
    WHERE a.statement_line IN ('revenue') AND e.status IN ('posted')
      AND e.is_intercompany = 0 AND p.fiscal_year = 2025
```

Plain English in; the number out, **with the SQL that produced it**. Note the `is_intercompany = 0` —
the consolidation elimination is present.

## Beat 2 — catch a wrong number *(the hero moment)*

```bash
tessera ask "What was consolidated net revenue in 2025?" --inject intercompany_double_count
```
```
  [injected a 'intercompany_double_count' SQL mistake]
  answer:  5,439,001.00 USD
  verdict: FAIL  (claimed 5,439,001.00 USD vs certified 5,293,985.00 USD (off by 145,016.00 USD).)
    - [intercompany_double_count] Does not reconcile: claimed 5,439,001.00 USD equals the value
      produced by 'intercompany_double_count'. The certified net_revenue is 5,293,985.00 USD.
```

The injected query genuinely drops the `is_intercompany = 0` clause. A typical assistant would have
shown **$5,439,001 as fact.** Tessera recomputes the truth by an independent path and **names the
mistake** — $145,016 of intercompany that should have been eliminated.

## Beat 3 — the receipt, verified offline

```bash
tessera ask "What was consolidated net revenue in 2025?" --receipt receipt.json
tessera verify receipt.json
```
```
  signed receipt → receipt.json  (key_id 566b5f3f17839212)
  [VALID] signature valid; signer identity not pinned (pass --expect-key to assert it)
  attested verdict: PASS   signer key_id: 566b5f3f17839212
  answer:   5,293,985.00 USD
```

Now forge the answer in the receipt and re-verify:

```
  [INVALID] payload_sha256 does not match the payload
```

An auditor verifies the receipt **without the warehouse and without trusting Tessera.** Tamper with
any bound field and it goes `INVALID`.

## Beat 4 — and it's cheaper

```bash
tessera bench
```
```
  accuracy: 100%   cheap-wins: 3/6   escalations: 3/6
  cascade cost $0.029910  vs always-strong $0.043040  →  30.5% saved, with no loss of correctness.
```

Cheap model first; escalate only when the verifier isn't satisfied. Safe, because every accepted
answer is independently checked.

---

**The pitch in one line:** the assistant answers, an *independent* verifier decides whether to trust
it, and a signed receipt lets someone else check the work later.
