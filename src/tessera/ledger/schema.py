"""The dimensional schema: dim/fact row models, the chart of accounts, and the sqlite3 DDL.

Money is modelled as :class:`decimal.Decimal` in Python but stored as **integer minor units** (cents)
in sqlite, so a SQL ``SUM()`` is exact — no binary-float drift in a number an auditor will check.
``MINOR_UNITS = 100`` (two-decimal currencies are all we mint here).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

MINOR_UNITS = 100
"""Minor units per major unit (cents per dollar). All seeded currencies are 2-decimal."""


def to_minor(amount: Decimal) -> int:
    """Major-unit Decimal → integer minor units, exactly (raises on sub-cent precision)."""
    scaled = amount * MINOR_UNITS
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{amount} has sub-minor-unit precision; cannot store exactly")
    return int(scaled)


def from_minor(minor: int) -> Decimal:
    """Integer minor units → major-unit Decimal."""
    return (Decimal(minor) / MINOR_UNITS).quantize(Decimal("0.01"))


class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class NormalBalance(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class EntryStatus(str, Enum):
    POSTED = "posted"
    DRAFT = "draft"
    REVERSED = "reversed"


class Entity(BaseModel):
    entity_id: int
    code: str
    name: str
    currency: str = Field(description="The entity's transaction/local currency (ISO-4217).")
    functional_currency: str = Field(description="Reporting currency for consolidation (USD).")
    consolidation_group: str
    is_parent: bool = False


class Account(BaseModel):
    account_id: int
    code: str
    name: str
    account_type: AccountType
    normal_balance: NormalBalance
    statement_line: str = Field(description="The P&L / balance-sheet line this account rolls up to.")
    is_intercompany: bool = False


class Period(BaseModel):
    period_id: int
    fiscal_year: int
    quarter: int = Field(ge=1, le=4)
    month: int = Field(ge=1, le=12)
    label: str = Field(description="Human label, e.g. '2025-Q3' is derived; this is '2025-07'.")
    is_closed: bool = True


class Counterparty(BaseModel):
    counterparty_id: int
    name: str
    is_intercompany: bool = False
    entity_id: int | None = Field(
        default=None, description="The internal entity this counterparty *is*, if intercompany."
    )


class JournalEntry(BaseModel):
    entry_id: int
    entity_id: int
    period_id: int
    status: EntryStatus
    is_intercompany: bool = False
    counterparty_id: int | None = None
    fx_rate: Decimal = Field(
        default=Decimal("1"),
        description="Multiplier from the entity's txn currency to the functional currency.",
    )
    reverses_entry_id: int | None = Field(
        default=None, description="If a reversal, the entry it reverses."
    )
    memo: str = ""


class JournalLine(BaseModel):
    line_id: int
    entry_id: int
    account_id: int
    debit_txn: Decimal = Field(default=Decimal("0.00"))
    credit_txn: Decimal = Field(default=Decimal("0.00"))
    fx_rate: Decimal = Field(default=Decimal("1"))

    @property
    def debit_func(self) -> Decimal:
        return (self.debit_txn * self.fx_rate).quantize(Decimal("0.01"))

    @property
    def credit_func(self) -> Decimal:
        return (self.credit_txn * self.fx_rate).quantize(Decimal("0.01"))


class Warehouse(BaseModel):
    """The full generated ledger — the in-memory source of truth behind the sqlite mirror."""

    entities: list[Entity] = Field(default_factory=list)
    accounts: list[Account] = Field(default_factory=list)
    periods: list[Period] = Field(default_factory=list)
    counterparties: list[Counterparty] = Field(default_factory=list)
    entries: list[JournalEntry] = Field(default_factory=list)
    lines: list[JournalLine] = Field(default_factory=list)

    # --- convenience lookups (built on demand; the lists above are authoritative) ---

    def account_by_id(self) -> dict[int, Account]:
        return {a.account_id: a for a in self.accounts}

    def entry_by_id(self) -> dict[int, JournalEntry]:
        return {e.entry_id: e for e in self.entries}

    def period_by_id(self) -> dict[int, Period]:
        return {p.period_id: p for p in self.periods}


# --------------------------------------------------------------------------------------------------
# Chart of accounts — small but realistic, every account mapped to exactly one statement line.
# (account_id, code, name, type, normal_balance, statement_line, is_intercompany)
# --------------------------------------------------------------------------------------------------

CHART_OF_ACCOUNTS: list[Account] = [
    # Assets (debit-normal)
    Account(account_id=1000, code="1000", name="Cash", account_type=AccountType.ASSET,
            normal_balance=NormalBalance.DEBIT, statement_line="cash"),
    Account(account_id=1100, code="1100", name="Accounts Receivable", account_type=AccountType.ASSET,
            normal_balance=NormalBalance.DEBIT, statement_line="accounts_receivable"),
    Account(account_id=1200, code="1200", name="Intercompany Receivable",
            account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT,
            statement_line="intercompany_assets", is_intercompany=True),
    Account(account_id=1500, code="1500", name="Property, Plant & Equipment",
            account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT, statement_line="ppe"),
    # Liabilities (credit-normal)
    Account(account_id=2000, code="2000", name="Accounts Payable",
            account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT,
            statement_line="accounts_payable"),
    Account(account_id=2100, code="2100", name="Intercompany Payable",
            account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT,
            statement_line="intercompany_liabilities", is_intercompany=True),
    Account(account_id=2500, code="2500", name="Long-term Debt",
            account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT,
            statement_line="debt"),
    # Equity (credit-normal)
    Account(account_id=3000, code="3000", name="Common Stock", account_type=AccountType.EQUITY,
            normal_balance=NormalBalance.CREDIT, statement_line="equity"),
    Account(account_id=3900, code="3900", name="Retained Earnings", account_type=AccountType.EQUITY,
            normal_balance=NormalBalance.CREDIT, statement_line="equity"),
    # Revenue (credit-normal)
    Account(account_id=4000, code="4000", name="Product Revenue", account_type=AccountType.REVENUE,
            normal_balance=NormalBalance.CREDIT, statement_line="revenue"),
    Account(account_id=4100, code="4100", name="Service Revenue", account_type=AccountType.REVENUE,
            normal_balance=NormalBalance.CREDIT, statement_line="revenue"),
    Account(account_id=4900, code="4900", name="Intercompany Revenue",
            account_type=AccountType.REVENUE, normal_balance=NormalBalance.CREDIT,
            statement_line="revenue", is_intercompany=True),
    # Expense (debit-normal)
    Account(account_id=5000, code="5000", name="Cost of Goods Sold", account_type=AccountType.EXPENSE,
            normal_balance=NormalBalance.DEBIT, statement_line="cogs"),
    Account(account_id=6000, code="6000", name="Operating Expense (SG&A)",
            account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT,
            statement_line="operating_expenses"),
    Account(account_id=6500, code="6500", name="Depreciation", account_type=AccountType.EXPENSE,
            normal_balance=NormalBalance.DEBIT, statement_line="depreciation"),
    Account(account_id=7000, code="7000", name="Interest Expense", account_type=AccountType.EXPENSE,
            normal_balance=NormalBalance.DEBIT, statement_line="interest_expense"),
]


# --------------------------------------------------------------------------------------------------
# sqlite3 DDL — the queryable star schema. Amounts are INTEGER minor units so SUM() is exact.
# --------------------------------------------------------------------------------------------------

DDL = """
CREATE TABLE dim_entity (
    entity_id            INTEGER PRIMARY KEY,
    code                 TEXT NOT NULL,
    name                 TEXT NOT NULL,
    currency             TEXT NOT NULL,
    functional_currency  TEXT NOT NULL,
    consolidation_group  TEXT NOT NULL,
    is_parent            INTEGER NOT NULL
);
CREATE TABLE dim_account (
    account_id      INTEGER PRIMARY KEY,
    code            TEXT NOT NULL,
    name            TEXT NOT NULL,
    account_type    TEXT NOT NULL,
    normal_balance  TEXT NOT NULL,
    statement_line  TEXT NOT NULL,
    is_intercompany INTEGER NOT NULL
);
CREATE TABLE dim_period (
    period_id    INTEGER PRIMARY KEY,
    fiscal_year  INTEGER NOT NULL,
    quarter      INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    label        TEXT NOT NULL,
    is_closed    INTEGER NOT NULL
);
CREATE TABLE dim_counterparty (
    counterparty_id INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    is_intercompany INTEGER NOT NULL,
    entity_id       INTEGER
);
CREATE TABLE fact_journal_entry (
    entry_id          INTEGER PRIMARY KEY,
    entity_id         INTEGER NOT NULL REFERENCES dim_entity(entity_id),
    period_id         INTEGER NOT NULL REFERENCES dim_period(period_id),
    status            TEXT NOT NULL,
    is_intercompany   INTEGER NOT NULL,
    counterparty_id   INTEGER REFERENCES dim_counterparty(counterparty_id),
    fx_rate           TEXT NOT NULL,
    reverses_entry_id INTEGER,
    memo              TEXT NOT NULL
);
CREATE TABLE fact_journal_line (
    line_id          INTEGER PRIMARY KEY,
    entry_id         INTEGER NOT NULL REFERENCES fact_journal_entry(entry_id),
    account_id       INTEGER NOT NULL REFERENCES dim_account(account_id),
    debit_txn_minor  INTEGER NOT NULL,
    credit_txn_minor INTEGER NOT NULL,
    debit_func_minor INTEGER NOT NULL,
    credit_func_minor INTEGER NOT NULL,
    currency         TEXT NOT NULL
);
CREATE INDEX ix_line_entry   ON fact_journal_line(entry_id);
CREATE INDEX ix_line_account ON fact_journal_line(account_id);
CREATE INDEX ix_entry_period ON fact_journal_entry(period_id);
CREATE INDEX ix_entry_entity ON fact_journal_entry(entity_id);
"""
