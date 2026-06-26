"""The ``tessera`` command-line entry point.

Phase 0 shipped ``version`` + ``doctor``. Phase 1 adds the ``dataset`` group: build the governed
sqlite warehouse and ``verify`` its invariants (the first real verdict the project produces). Heavy,
optional deps stay lazy-imported; the dataset path needs only the light base (pydantic + pyyaml).
"""

from __future__ import annotations

import argparse
import sys

from . import __version__


def _doctor() -> int:
    """Report environment health: Python version and that the shared contract imports."""
    ok = True
    print(f"tessera        {__version__}")
    print(f"python         {sys.version.split()[0]}")
    try:
        import agentsensory

        print(f"agentsensory   {agentsensory.__version__}  (shared verdict contract)")
    except Exception as exc:  # noqa: BLE001 - doctor reports, never raises
        print(f"  ! agentsensory not importable: {exc}")
        ok = False
    print("ok" if ok else "problems found")
    return 0 if ok else 1


def _dataset_build(out: str, seed: int) -> int:
    from .ledger import GeneratorConfig, generate
    from .ledger.warehouse import materialize_sqlite

    wh = generate(GeneratorConfig(seed=seed))
    conn = materialize_sqlite(wh, out)
    conn.close()
    print(f"built {out}")
    print(f"  entities={len(wh.entities)}  accounts={len(wh.accounts)}  periods={len(wh.periods)}")
    print(f"  entries={len(wh.entries)}  lines={len(wh.lines)}  (seed={seed})")
    return 0


def _ask(question: str, seed: int, db: str | None) -> int:
    from .agent import answer_question
    from .ledger import GeneratorConfig, generate
    from .ledger.warehouse import materialize_sqlite
    from .semantic import load_metrics

    wh = generate(GeneratorConfig(seed=seed))
    conn = materialize_sqlite(wh, db or ":memory:")
    try:
        report = answer_question(question, conn, load_metrics(), wh.entities)
    finally:
        conn.close()

    print(f"Q: {question}\n")
    if report.answer is not None:
        print(f"  answer:  {report.answer}")
    print(f"  verdict: {report.verdict.value.upper()}  ({report.summary})")
    if report.executed_sql:
        print("\n  executed SQL:")
        for line in report.executed_sql.splitlines():
            print(f"    {line}")
    print("\n  NB: this number is NOT yet independently verified — that is the Phase 3 verifier's job.")
    return 0


def _dataset_verify(seed: int) -> int:
    from .ledger import GeneratorConfig, generate
    from .ledger.controls import check_invariants

    wh = generate(GeneratorConfig(seed=seed))
    results = check_invariants(wh)
    width = max(len(r.name) for r in results)
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        print(f"  [{mark}] {r.name.ljust(width)}  {r.detail}")
    ok = all(r.ok for r in results)
    print(f"\nverdict: {'PASS — the books are real' if ok else 'FAIL — invariants broken'}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera",
        description="Attested NL→analytics for regulated finance.",
    )
    parser.add_argument("--version", action="version", version=f"tessera {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("version", help="Print the Tessera version.")
    sub.add_parser("doctor", help="Check the local environment is healthy.")

    ask = sub.add_parser("ask", help="Ask a finance question (answered, not yet verified).")
    ask.add_argument("question", help="The natural-language question, in quotes.")
    ask.add_argument("--seed", type=int, default=20260626, help="Generator seed.")
    ask.add_argument("--db", default=None, help="Existing sqlite warehouse (default: in-memory).")

    ds = sub.add_parser("dataset", help="Build or verify the governed GL warehouse.")
    ds_sub = ds.add_subparsers(dest="action")
    build = ds_sub.add_parser("build", help="Generate the warehouse into a sqlite file.")
    build.add_argument("--out", default="tessera.db", help="Output sqlite path (default tessera.db).")
    build.add_argument("--seed", type=int, default=20260626, help="Generator seed.")
    verify = ds_sub.add_parser("verify", help="Run the ledger invariants (the Phase 1 verdict).")
    verify.add_argument("--seed", type=int, default=20260626, help="Generator seed.")

    args = parser.parse_args(argv)

    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "doctor":
        return _doctor()
    if args.command == "ask":
        return _ask(args.question, args.seed, args.db)
    if args.command == "dataset":
        if args.action == "build":
            return _dataset_build(args.out, args.seed)
        if args.action == "verify":
            return _dataset_verify(args.seed)
        ds.print_help()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
