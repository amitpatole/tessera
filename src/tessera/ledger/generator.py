"""The deterministic, seeded General-Ledger generator.

Every journal entry is internally balanced (Σ debit == Σ credit, in both transaction and functional
currency), so the trial balance balances for *any* subset of entries — which is what makes the
verifier's invariants real. The seed fully determines the output: same seed ⇒ identical bytes, no
global-``random`` drift.

The data is shaped so the eight failure classes are *demonstrable*, not hypothetical:

- multiple legal entities in different currencies (USD/EUR/BRL) → FX mixing has teeth;
- matched **intercompany** revenue/receivable pairs → consolidation must eliminate them;
- some **draft** and **reversed** entries → a posted-only filter actually matters;
- a chart where every account rolls to exactly one statement line → rollup errors are catchable.
"""

from __future__ import annotations

import random
from decimal import Decimal

from pydantic import BaseModel, Field

from .schema import (
    CHART_OF_ACCOUNTS,
    Counterparty,
    Entity,
    EntryStatus,
    JournalEntry,
    JournalLine,
    Period,
    Warehouse,
)

# Entities: a parent + three subsidiaries, three currencies, one consolidation group.
# fx_rate is the constant multiplier from the entity's currency to USD (the functional currency).
_ENTITIES = [
    Entity(entity_id=1, code="GLB", name="ACME Global (Parent)", currency="USD",
           functional_currency="USD", consolidation_group="ACME", is_parent=True),
    Entity(entity_id=2, code="US", name="ACME US", currency="USD",
           functional_currency="USD", consolidation_group="ACME"),
    Entity(entity_id=3, code="EU", name="ACME Europe", currency="EUR",
           functional_currency="USD", consolidation_group="ACME"),
    Entity(entity_id=4, code="BR", name="ACME Brazil", currency="BRL",
           functional_currency="USD", consolidation_group="ACME"),
]
_FX_TO_USD = {"USD": Decimal("1"), "EUR": Decimal("1.08"), "BRL": Decimal("0.19")}


class GeneratorConfig(BaseModel):
    seed: int = 20260626
    fiscal_years: list[int] = Field(default_factory=lambda: [2025, 2026])
    revenue_entries_per_month: int = 6
    expense_entries_per_month: int = 4
    intercompany_prob: float = 0.5
    draft_prob: float = 0.1
    reversed_prob: float = 0.08


def _quarter(month: int) -> int:
    return (month - 1) // 3 + 1


class _Builder:
    """Mutable scratch state for one generation run — keeps the id counters in one place."""

    def __init__(self, cfg: GeneratorConfig) -> None:
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.wh = Warehouse(
            entities=list(_ENTITIES),
            accounts=list(CHART_OF_ACCOUNTS),
        )
        self._entry_id = 0
        self._line_id = 0
        self._build_periods()
        self._build_counterparties()

    # -- dimensions -------------------------------------------------------------------------------

    def _build_periods(self) -> None:
        pid = 0
        for year in self.cfg.fiscal_years:
            for month in range(1, 13):
                pid += 1
                self.wh.periods.append(Period(
                    period_id=pid, fiscal_year=year, quarter=_quarter(month), month=month,
                    label=f"{year}-{month:02d}", is_closed=True,
                ))

    def _build_counterparties(self) -> None:
        self.wh.counterparties.append(
            Counterparty(counterparty_id=1, name="External Customers", is_intercompany=False)
        )
        self.wh.counterparties.append(
            Counterparty(counterparty_id=2, name="External Vendors", is_intercompany=False)
        )
        # Each entity is also an intercompany counterparty (counterparty_id = 100 + entity_id).
        for e in self.wh.entities:
            self.wh.counterparties.append(Counterparty(
                counterparty_id=100 + e.entity_id, name=f"Intercompany: {e.name}",
                is_intercompany=True, entity_id=e.entity_id,
            ))

    # -- fact builders ----------------------------------------------------------------------------

    def _add_entry(self, entity: Entity, period: Period, lines: list[tuple[int, Decimal, Decimal]],
                   *, status: EntryStatus, is_ic: bool = False, counterparty_id: int | None = None,
                   memo: str = "") -> JournalEntry:
        """Append one balanced entry. ``lines`` are (account_id, debit_txn, credit_txn) tuples."""
        debit = sum((d for _, d, _ in lines), Decimal("0"))
        credit = sum((c for _, _, c in lines), Decimal("0"))
        if debit != credit:
            raise AssertionError(f"unbalanced entry built: {debit} != {credit}")
        fx = _FX_TO_USD[entity.currency]
        self._entry_id += 1
        entry = JournalEntry(
            entry_id=self._entry_id, entity_id=entity.entity_id, period_id=period.period_id,
            status=status, is_intercompany=is_ic, counterparty_id=counterparty_id, fx_rate=fx,
            memo=memo,
        )
        self.wh.entries.append(entry)
        for account_id, d, c in lines:
            self._line_id += 1
            self.wh.lines.append(JournalLine(
                line_id=self._line_id, entry_id=entry.entry_id, account_id=account_id,
                debit_txn=d, credit_txn=c, fx_rate=fx,
            ))
        return entry

    def _amount(self, lo: int, hi: int) -> Decimal:
        """A clean 2-decimal amount (whole currency units) — exact in minor units."""
        return Decimal(self.rng.randrange(lo, hi)) * Decimal("100.00")

    def _status(self) -> EntryStatus:
        r = self.rng.random()
        if r < self.cfg.reversed_prob:
            return EntryStatus.REVERSED
        if r < self.cfg.reversed_prob + self.cfg.draft_prob:
            return EntryStatus.DRAFT
        return EntryStatus.POSTED

    def _generate_month(self, entity: Entity, period: Period) -> None:
        # Revenue: Dr Cash/AR, Cr Product/Service Revenue.
        for _ in range(self.cfg.revenue_entries_per_month):
            amt = self._amount(50, 500)
            debit_acct = self.rng.choice([1000, 1100])         # Cash or AR
            revenue_acct = self.rng.choice([4000, 4100])        # Product or Service Revenue
            self._add_entry(entity, period,
                            [(debit_acct, amt, Decimal("0.00")), (revenue_acct, Decimal("0.00"), amt)],
                            status=self._status(), counterparty_id=1, memo="external sale")
            # Matching COGS for ~70% of sales: Dr COGS, Cr AP.
            if self.rng.random() < 0.7:
                cogs = (amt * Decimal("0.6")).quantize(Decimal("1")) * Decimal("1.00")
                self._add_entry(entity, period,
                                [(5000, cogs, Decimal("0.00")), (2000, Decimal("0.00"), cogs)],
                                status=self._status(), counterparty_id=2, memo="cost of sale")

        # Operating expenses, depreciation, interest.
        for _ in range(self.cfg.expense_entries_per_month):
            amt = self._amount(10, 120)
            expense_acct = self.rng.choice([6000, 6000, 6500, 7000])  # weight SG&A
            credit_acct = 1000 if expense_acct in (6500, 7000) else 2000
            if expense_acct == 6500:
                credit_acct = 1500  # depreciation reduces PP&E
            self._add_entry(entity, period,
                            [(expense_acct, amt, Decimal("0.00")), (credit_acct, Decimal("0.00"), amt)],
                            status=self._status(), counterparty_id=2, memo="operating expense")

        # Intercompany: a subsidiary sells to the parent. Both legs flagged; eliminated on consol.
        if not entity.is_parent and self.rng.random() < self.cfg.intercompany_prob:
            amt = self._amount(40, 200)
            parent = self.wh.entities[0]
            # Seller (this entity): Dr Intercompany Receivable, Cr Intercompany Revenue.
            self._add_entry(entity, period,
                            [(1200, amt, Decimal("0.00")), (4900, Decimal("0.00"), amt)],
                            status=EntryStatus.POSTED, is_ic=True,
                            counterparty_id=100 + parent.entity_id, memo="intercompany sale")
            # Buyer (parent): Dr Operating Expense, Cr Intercompany Payable — in the PARENT's currency.
            amt_parent = (amt * _FX_TO_USD[entity.currency] / _FX_TO_USD[parent.currency]).quantize(
                Decimal("0.01"))
            self._add_entry(parent, period,
                            [(6000, amt_parent, Decimal("0.00")), (2100, Decimal("0.00"), amt_parent)],
                            status=EntryStatus.POSTED, is_ic=True,
                            counterparty_id=100 + entity.entity_id, memo="intercompany purchase")

    def build(self) -> Warehouse:
        for entity in self.wh.entities:
            for period in self.wh.periods:
                self._generate_month(entity, period)
        return self.wh


def generate(config: GeneratorConfig | None = None) -> Warehouse:
    """Build the full in-memory warehouse from a config (deterministic in ``config.seed``)."""
    return _Builder(config or GeneratorConfig()).build()
