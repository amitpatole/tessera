"""Request/response models for the REST API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    route: bool = Field(default=False, description="Run the cost cascade instead of a single call.")
    sign: bool = Field(default=False, description="Attach a signed receipt to the response.")


class IssueOut(BaseModel):
    kind: str
    severity: str
    message: str
    source: str


class AttemptOut(BaseModel):
    tier: str
    verdict: str
    cost_usd: float


class RoutingOut(BaseModel):
    accepted_tier: str | None
    escalations: int
    total_cost_usd: float
    baseline_cost_usd: float
    attempts: list[AttemptOut]


class AskResponse(BaseModel):
    question: str
    verdict: str
    answer: str | None
    summary: str
    executed_sql: str | None = None
    issues: list[IssueOut] = []
    routing: RoutingOut | None = None
    receipt: dict | None = None


class VerifyRequest(BaseModel):
    receipt: dict
    expect_key: str | None = None


class VerifyResponse(BaseModel):
    valid: bool
    reason: str
    key_id: str
    verdict: str
    authenticity_checked: bool


class MetricOut(BaseModel):
    name: str
    description: str
