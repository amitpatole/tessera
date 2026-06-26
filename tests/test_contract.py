"""The contract foundation: Tessera issues/reports are valid agentsensory artifacts."""

from __future__ import annotations

from agentsensory import Severity, Verdict, verdict_from_issues

from tessera import FailureClass, LedgerIssue, LedgerReport


def test_ledger_issue_is_grounded_in_a_failure_class() -> None:
    issue = LedgerIssue.make(
        FailureClass.INTERCOMPANY_DOUBLE_COUNT,
        Severity.CRITICAL,
        "Intercompany revenue counted on both legs; consolidation elimination missing.",
        source="independent_recompute",
    )
    assert issue.kind is FailureClass.INTERCOMPANY_DOUBLE_COUNT
    assert verdict_from_issues([issue]) is Verdict.FAIL


def test_clean_answer_is_a_pass_report() -> None:
    report = LedgerReport(
        verdict=Verdict.PASS,
        summary="Q2-2026 net revenue for entity ACME-US reconciles to the control total.",
        question="What was ACME-US net revenue in Q2 2026?",
        executed_sql="SELECT ... -- parameterized, read-only role",
        answer="12,480,300.00 USD",
    )
    assert report.is_ok()
    assert report.issues == []


def test_report_round_trips_through_the_shared_contract() -> None:
    report = LedgerReport(
        verdict=Verdict.FAIL,
        summary="Answer mixed currencies.",
        issues=[
            LedgerIssue.make(
                FailureClass.FX_MIXING,
                Severity.ERROR,
                "Summed EUR and USD lines without translation.",
            )
        ],
        question="Total expenses across all entities in 2026?",
    )
    handoff = report.to_handoff()
    assert handoff.perceived is Verdict.FAIL
    assert any("fx_mixing" in item for item in handoff.todo)
