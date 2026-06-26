"""Load and validate the certified-metric YAML into typed :class:`Metric` objects."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

_METRICS_YAML = Path(__file__).with_name("metrics.yaml")


class Sign(str, Enum):
    """The natural direction in which a metric's accounts accumulate value."""

    CREDIT = "credit"  # revenue, liabilities, equity — value = Σ(credit - debit)
    DEBIT = "debit"    # expenses, assets — value = Σ(debit - credit)


class PeriodSemantics(str, Enum):
    FLOW = "flow"        # period-to-date activity (revenue, expense)
    BALANCE = "balance"  # as-of point-in-time balance (cash, receivables)


class MetricComponent(BaseModel):
    """One term of a derived metric: ``coefficient * <another metric>``."""

    metric: str
    coefficient: Decimal = Decimal("1")


class Metric(BaseModel):
    name: str
    description: str = ""
    # Base-metric selectors (ignored when `components` is set):
    statement_lines: list[str] = Field(default_factory=list)
    account_codes: list[str] = Field(default_factory=list)
    sign: Sign = Sign.CREDIT
    status_filter: list[str] = Field(default_factory=lambda: ["posted"])
    eliminate_intercompany: bool = False
    period_semantics: PeriodSemantics = PeriodSemantics.FLOW
    currency: str = "functional"
    # Derived-metric definition (a linear combination of other metrics):
    components: list[MetricComponent] = Field(default_factory=list)
    # Back-reference to the whole registry, attached at load time so derived metrics can resolve.
    registry: dict[str, Metric] | None = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="after")
    def _check_definition(self) -> Metric:
        if self.currency not in ("functional", "transaction"):
            raise ValueError(f"{self.name}: currency must be 'functional' or 'transaction'")
        if not self.components and not self.statement_lines and not self.account_codes:
            raise ValueError(f"{self.name}: a base metric must select accounts (statement_lines or codes)")
        return self


def load_metrics(path: Path | str | None = None) -> dict[str, Metric]:
    """Parse the metric YAML into a name→:class:`Metric` registry (every metric back-linked to it)."""
    src = Path(path) if path is not None else _METRICS_YAML
    raw: dict[str, Any] = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    registry: dict[str, Metric] = {}
    for name, spec in raw.items():
        registry[name] = Metric(name=name, **(spec or {}))
    # Resolve derived-metric references and attach the registry back-pointer.
    for metric in registry.values():
        metric.registry = registry
        for comp in metric.components:
            if comp.metric not in registry:
                raise ValueError(f"{metric.name}: unknown component metric '{comp.metric}'")
    return registry


Metric.model_rebuild()
