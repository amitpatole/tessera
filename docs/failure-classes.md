# The 8 failure classes

The verifier exists because a General-Ledger answer goes wrong in *nameable* ways. Each class has
(a) how a generated query gets it wrong, and (b) the **independent** check that catches it —
orthogonal to the model's own SQL, with a pinned regression test.

| # | Failure class | How the SQL goes wrong | Independent check |
|---|---|---|---|
| 1 | **Wrong period grain** | sums a fiscal year when asked for Q3 | recompute at the asked grain; compare to the control total |
| 2 | **Missing entity filter** | returns consolidated when asked for one subsidiary | cross-check entity scope vs. the certified metric |
| 3 | **Debit/credit sign flip** | treats a credit-normal account as debit-normal | re-derive using `normal_balance`; sign invariant |
| 4 | **Intercompany double-count** | forgets to eliminate intercompany on consolidation | consolidated vs. Σ(entities) − Σ(intercompany) |
| 5 | **Draft / reversed included** | counts `status != 'posted'` rows | recompute posted-only; any delta ⇒ flag |
| 6 | **Wrong statement-line rollup** | maps an account to the wrong P&L line | verify membership against `statement_line` |
| 7 | **FX / currency mixing** | sums transaction-currency across currencies | recompute in functional currency; currency-consistency invariant |
| 8 | **As-of vs. period-to-date** | point-in-time balance vs. cumulative flow | re-derive both; check which the question requires |

## How a catch works

Each class is defined once, as the **broken metric/scope variant** that commits it. That single
definition does two jobs:

- **Diagnose** — when a claimed number doesn't reconcile, the verifier recomputes what each broken
  variant *would* yield; the variant whose value matches the claim **names the mistake**.
- **Inject** — the same definition builds genuinely-wrong SQL for the test suite, so there is no gap
  between "what we test" and "what we catch."

!!! example "Live catch — intercompany double-count"
    ```
    tessera ask "What was consolidated net revenue in 2025?" --inject intercompany_double_count
    → FAIL  claimed 5,439,001.00 vs certified 5,293,985.00  (off by 145,016.00)
            [intercompany_double_count] equals the value produced by that mistake
    ```
    The injected query genuinely drops the `is_intercompany = 0` elimination; the verifier recomputes
    the truth orthogonally and names it.

## The gate

The verifier **catches 8/8 injected classes** (each from genuinely-wrong SQL executed for real) and
**passes correct answers with zero false positives** — regression-pinned, green on CI. A wrong number
that matches no known class still fails (`OTHER`): *"does not reconcile, and matches no known failure
mode."*
