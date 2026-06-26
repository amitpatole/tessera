"""The Tessera REST API — the same verified pipeline, over HTTP.

Every ``/ask`` runs resolve → (cheap-first cascade or single call) → **independent verify**, and can
attach a signed receipt — the API never returns an unverified number as if it were trusted. The
warehouse is generated once at startup into a temp sqlite file; each request opens its own
**read-only** connection (`mode=ro`), so concurrent reads are safe and nothing can write the books.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request

from .. import __version__
from .models import (
    AskRequest,
    AskResponse,
    AttemptOut,
    IssueOut,
    MetricOut,
    RoutingOut,
    VerifyRequest,
    VerifyResponse,
)
from .security import BodyLimitMiddleware, check_bind_security, token_ok


def _ro_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


async def require_auth(request: Request) -> None:
    """Enforce the bearer token when one is configured (loopback zero-config leaves it unset)."""
    expected = request.app.state.api_token
    if not expected:
        return
    if not token_ok(request.headers.get("authorization"), expected):
        raise HTTPException(status_code=401, detail="missing or invalid bearer token")


def create_app(
    *, seed: int = 20260626, host: str | None = None, api_token: str | None = None,
    max_body_bytes: int = 16_384,
) -> FastAPI:
    host = host if host is not None else os.environ.get("TESSERA_BIND_HOST", "127.0.0.1")
    api_token = api_token if api_token is not None else os.environ.get("TESSERA_API_TOKEN")
    check_bind_security(host, api_token)  # fail closed before we ever serve

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from ..ledger import GeneratorConfig, generate
        from ..ledger.warehouse import materialize_sqlite
        from ..semantic import load_metrics

        wh = generate(GeneratorConfig(seed=seed))
        tmpdir = tempfile.mkdtemp(prefix="tessera-")
        db_path = str(Path(tmpdir) / "tessera.db")
        conn = materialize_sqlite(wh, db_path)
        conn.close()
        app.state.wh = wh
        app.state.db_path = db_path
        app.state.metrics = load_metrics()
        app.state.seed = seed
        app.state.api_token = api_token
        yield
        try:
            os.remove(db_path)
            os.rmdir(tmpdir)
        except OSError:
            pass

    app = FastAPI(title="Tessera", version=__version__, lifespan=lifespan,
                  description="Attested NL→analytics for regulated finance.")
    app.add_middleware(BodyLimitMiddleware, max_bytes=max_body_bytes)

    @app.get("/health")
    def health(request: Request) -> dict:
        st = request.app.state
        return {"status": "ok", "version": __version__, "dataset_seed": st.seed,
                "entries": len(st.wh.entries)}

    @app.get("/metrics", response_model=list[MetricOut])
    def metrics(request: Request, _: None = Depends(require_auth)) -> list[MetricOut]:
        return [MetricOut(name=n, description=m.description)
                for n, m in request.app.state.metrics.items()]

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest, request: Request, _: None = Depends(require_auth)) -> AskResponse:
        from ..agent.resolver import ResolutionError, resolve_question
        from ..agent.sql import execute_metric
        from ..verifier import verify

        st = request.app.state
        try:
            spec = resolve_question(req.question, st.metrics, st.wh.entities)
        except ResolutionError as exc:
            return AskResponse(question=req.question, verdict="warn", answer=None,
                               summary=f"outside the certified semantic layer: {exc}")

        conn = _ro_conn(st.db_path)
        try:
            if req.route:
                from ..routing import cascade, default_tiers

                routed = cascade(question=req.question, metric_name=spec.metric, scope=spec.scope,
                                 conn=conn, warehouse=st.wh, registry=st.metrics, tiers=default_tiers())
                report = routed.final_report
                routing = RoutingOut(
                    accepted_tier=routed.accepted_tier, escalations=routed.escalations,
                    total_cost_usd=routed.total_cost_usd, baseline_cost_usd=routed.baseline_cost_usd,
                    attempts=[AttemptOut(tier=a.tier, verdict=a.verdict, cost_usd=a.cost_usd)
                              for a in routed.attempts],
                )
            else:
                routing = None
                value, sql = execute_metric(conn, st.metrics, spec.metric, spec.scope)
                report = verify(question=req.question, metric_name=spec.metric, scope=spec.scope,
                                claimed_value=value, generated_sql=sql, warehouse=st.wh,
                                registry=st.metrics)
        finally:
            conn.close()

        receipt = None
        if req.sign:
            from ..receipt import sign_report

            receipt = sign_report(report, metric_name=spec.metric, scope=spec.scope,
                                  dataset_seed=st.seed).model_dump()

        return AskResponse(
            question=req.question, verdict=report.verdict.value, answer=report.answer,
            summary=report.summary, executed_sql=report.executed_sql,
            issues=[IssueOut(kind=i.kind.value, severity=i.severity.value, message=i.message,
                             source=i.source) for i in report.issues],
            routing=routing, receipt=receipt,
        )

    @app.post("/verify", response_model=VerifyResponse)
    def verify_endpoint(req: VerifyRequest, _: None = Depends(require_auth)) -> VerifyResponse:
        from ..receipt import Receipt, verify_receipt

        try:
            receipt = Receipt.model_validate(req.receipt)
        except Exception as exc:  # noqa: BLE001 - malformed receipt is a client error
            raise HTTPException(status_code=422, detail=f"malformed receipt: {exc}") from exc
        result = verify_receipt(receipt, expected_public_key=req.expect_key)
        return VerifyResponse(valid=result.valid, reason=result.reason, key_id=result.key_id,
                              verdict=result.verdict, authenticity_checked=result.authenticity_checked)

    return app
