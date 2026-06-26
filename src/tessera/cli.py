"""The ``tessera`` command-line entry point.

Phase 0 shipped ``version`` + ``doctor``. Phase 1 adds the ``dataset`` group: build the governed
sqlite warehouse and ``verify`` its invariants (the first real verdict the project produces). Heavy,
optional deps stay lazy-imported; the dataset path needs only the light base (pydantic + pyyaml).
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .contract import FailureClass


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


def _key() -> int:
    from .receipt import load_or_create_signing_key, public_key_hex
    from .receipt.keys import key_id, key_path

    priv = load_or_create_signing_key()
    pub = public_key_hex(priv)
    print(f"key_id:     {key_id(bytes.fromhex(pub))}")
    print(f"public_key: {pub}")
    print(f"key_file:   {key_path()}")
    print("\nShare the public key with an auditor so they can pin it: tessera verify <receipt> --expect-key <public_key>")
    return 0


def _verify(path: str, expect_key: str | None) -> int:
    from .receipt import Receipt, verify_receipt

    receipt = Receipt.model_validate_json(open(path, encoding="utf-8").read())
    result = verify_receipt(receipt, expected_public_key=expect_key)
    mark = "VALID" if result.valid else "INVALID"
    print(f"  [{mark}] {result.reason}")
    print(f"  attested verdict: {result.verdict.upper()}   signer key_id: {result.key_id}")
    print(f"  question: {receipt.payload.question}")
    print(f"  answer:   {receipt.payload.answer}")
    if not result.authenticity_checked:
        print("  (signer identity not pinned — pass --expect-key <public_key> to assert who signed it)")
    return 0 if result.valid else 1


def _ask(question: str, seed: int, db: str | None, inject: str | None, receipt_path: str | None) -> int:
    from .agent.resolver import ResolutionError, resolve_question
    from .agent.sql import execute_metric
    from .contract import FailureClass
    from .ledger import GeneratorConfig, generate
    from .ledger.warehouse import materialize_sqlite
    from .semantic import load_metrics
    from .verifier import inject_failure, verify

    wh = generate(GeneratorConfig(seed=seed))
    metrics = load_metrics()
    conn = materialize_sqlite(wh, db or ":memory:")
    print(f"Q: {question}\n")
    try:
        try:
            spec = resolve_question(question, metrics, wh.entities)
        except ResolutionError as exc:
            print(f"  verdict: WARN  (outside the certified semantic layer: {exc})")
            print("  no number returned — Tessera will not guess.")
            return 0

        if inject:
            result = inject_failure(conn, metrics, spec.metric, spec.scope, FailureClass(inject))
            if result is None:
                print(f"  (injection '{inject}' does not apply to {spec.metric} at this scope)")
                return 1
            value, sql = result
            print(f"  [injected a '{inject}' SQL mistake]")
        else:
            value, sql = execute_metric(conn, metrics, spec.metric, spec.scope)

        report = verify(
            question=question, metric_name=spec.metric, scope=spec.scope,
            claimed_value=value, generated_sql=sql, warehouse=wh, registry=metrics,
        )
    finally:
        conn.close()

    print(f"  answer:  {report.answer}")
    print(f"  verdict: {report.verdict.value.upper()}  ({report.summary})")
    for issue in report.issues:
        print(f"    - [{issue.kind.value}] {issue.message}")
    if report.executed_sql:
        print("\n  verified SQL:")
        for line in report.executed_sql.splitlines():
            print(f"    {line}")

    if receipt_path:
        from .receipt import sign_report

        signed = sign_report(report, metric_name=spec.metric, scope=spec.scope, dataset_seed=seed)
        with open(receipt_path, "w", encoding="utf-8") as fh:
            fh.write(signed.model_dump_json(indent=2))
        print(f"\n  signed receipt → {receipt_path}  (key_id {signed.key_id})")
        print(f"  verify it offline:  tessera verify {receipt_path}")
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

    ask = sub.add_parser("ask", help="Ask a finance question (answered and independently verified).")
    ask.add_argument("question", help="The natural-language question, in quotes.")
    ask.add_argument("--seed", type=int, default=20260626, help="Generator seed.")
    ask.add_argument("--db", default=None, help="Existing sqlite warehouse (default: in-memory).")
    ask.add_argument(
        "--inject", default=None,
        choices=[fc.value for fc in FailureClass if fc is not FailureClass.OTHER],
        help="Demo: inject a specific SQL mistake and watch the verifier catch it.",
    )
    ask.add_argument("--receipt", default=None, help="Write a signed receipt to this path.")

    sub.add_parser("key", help="Show the signing public key (share it so auditors can pin it).")

    verify = sub.add_parser("verify", help="Offline-verify a signed receipt.")
    verify.add_argument("receipt", help="Path to a receipt JSON file.")
    verify.add_argument("--expect-key", default=None, help="Assert the signer's public key (hex).")

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
        return _ask(args.question, args.seed, args.db, args.inject, args.receipt)
    if args.command == "key":
        return _key()
    if args.command == "verify":
        return _verify(args.receipt, args.expect_key)
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
