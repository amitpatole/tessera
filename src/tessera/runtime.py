"""A small in-process runtime that ties the pipeline together for the API, MCP, and tests.

Builds the warehouse once, then answers questions end-to-end — resolve → (optional cheap-first
cascade) → **independent verify** → (optional signed receipt) — returning plain dicts. Like the REST
layer, it never returns an unverified number as if it were trusted, and a question outside the
certified semantic layer comes back ``warn`` with no fabricated answer.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from .agent.resolver import ResolutionError, resolve_question
from .agent.sql import execute_metric
from .ledger import GeneratorConfig, generate
from .ledger.warehouse import materialize_sqlite
from .semantic import load_metrics
from .verifier import verify


def _ro_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


class Runtime:
    """Holds the generated warehouse + certified metrics; answers and verifies."""

    def __init__(self, seed: int = 20260626) -> None:
        self.seed = seed
        self.warehouse = generate(GeneratorConfig(seed=seed))
        self.metrics = load_metrics()
        self._dir = tempfile.mkdtemp(prefix="tessera-rt-")
        self.db_path = str(Path(self._dir) / "tessera.db")
        materialize_sqlite(self.warehouse, self.db_path).close()

    def close(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)

    def ask(self, question: str, *, route: bool = False, sign: bool = False,
            real: bool = False) -> dict[str, Any]:
        try:
            spec = resolve_question(question, self.metrics, self.warehouse.entities)
        except ResolutionError as exc:
            return {"question": question, "verdict": "warn", "answer": None,
                    "summary": f"outside the certified semantic layer: {exc}",
                    "executed_sql": None, "issues": [], "routing": None, "receipt": None}

        routing: dict[str, Any] | None = None
        conn = _ro_conn(self.db_path)
        try:
            if route:
                import os

                from .routing import cascade, cascade_tiers, default_tiers

                use_real = real or bool(os.environ.get("TESSERA_REAL_MODELS"))
                tiers = cascade_tiers() if use_real else default_tiers()
                routed = cascade(question=question, metric_name=spec.metric, scope=spec.scope,
                                 conn=conn, warehouse=self.warehouse, registry=self.metrics,
                                 tiers=tiers)
                report = routed.final_report
                routing = {"accepted_tier": routed.accepted_tier, "escalations": routed.escalations,
                           "total_cost_usd": routed.total_cost_usd,
                           "baseline_cost_usd": routed.baseline_cost_usd,
                           "attempts": [a.model_dump() for a in routed.attempts]}
            else:
                value, sql = execute_metric(conn, self.metrics, spec.metric, spec.scope)
                report = verify(question=question, metric_name=spec.metric, scope=spec.scope,
                                claimed_value=value, generated_sql=sql, warehouse=self.warehouse,
                                registry=self.metrics)
        finally:
            conn.close()

        receipt = None
        if sign:
            from .receipt import sign_report

            receipt = sign_report(report, metric_name=spec.metric, scope=spec.scope,
                                  dataset_seed=self.seed).model_dump()

        return {
            "question": question, "verdict": report.verdict.value, "answer": report.answer,
            "summary": report.summary, "executed_sql": report.executed_sql,
            "issues": [{"kind": i.kind.value, "severity": i.severity.value, "message": i.message,
                        "source": i.source} for i in report.issues],
            "routing": routing, "receipt": receipt,
        }

    def verify_receipt(self, receipt: dict, *, expect_key: str | None = None) -> dict[str, Any]:
        from .receipt import Receipt, verify_receipt

        result = verify_receipt(Receipt.model_validate(receipt), expected_public_key=expect_key)
        return result.model_dump()
