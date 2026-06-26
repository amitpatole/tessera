"""The Phase 1 gate: the generated books are real books."""

from __future__ import annotations

from tessera.ledger import GeneratorConfig, generate
from tessera.ledger.controls import check_invariants, invariants_hold
from tessera.ledger.warehouse import materialize_sqlite


def test_all_invariants_hold() -> None:
    wh = generate()
    results = check_invariants(wh)
    failed = [r for r in results if not r.ok]
    assert not failed, [f"{r.name}: {r.detail}" for r in failed]
    assert invariants_hold(wh)


def test_invariants_hold_across_several_seeds() -> None:
    for seed in (1, 7, 42, 20260626):
        assert invariants_hold(generate(GeneratorConfig(seed=seed))), f"seed {seed} broke the books"


def test_dataset_is_non_trivial() -> None:
    wh = generate()
    assert len(wh.entries) > 500
    assert len(wh.lines) > len(wh.entries)
    # The data must actually contain the structures the failure classes need.
    assert any(e.is_intercompany for e in wh.entries), "no intercompany entries"
    assert any(e.status.value == "draft" for e in wh.entries), "no draft entries"
    assert any(e.status.value == "reversed" for e in wh.entries), "no reversed entries"
    assert len({e.currency for e in wh.entities}) >= 2, "single currency — FX class is untestable"


def test_sqlite_trial_balance_matches_python() -> None:
    wh = generate()
    conn = materialize_sqlite(wh, ":memory:")
    try:
        row = conn.execute(
            "SELECT SUM(debit_func_minor) AS d, SUM(credit_func_minor) AS c "
            "FROM fact_journal_line l JOIN fact_journal_entry e ON e.entry_id = l.entry_id "
            "WHERE e.status = 'posted'"
        ).fetchone()
        assert row["d"] == row["c"], "sqlite posted trial balance does not balance"
        assert row["d"] > 0
    finally:
        conn.close()
