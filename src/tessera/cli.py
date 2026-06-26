"""The ``tessera`` command-line entry point.

Phase 0 ships the two commands every tool in this family carries — ``version`` and ``doctor`` —
using only the standard library so the base install stays light. The customer-facing surface
(``ask``, ``verify``, ``demo``, ``serve``) lands in later phases and lazy-imports its heavy deps.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera",
        description="Attested NL→analytics for regulated finance.",
    )
    parser.add_argument("--version", action="version", version=f"tessera {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("version", help="Print the Tessera version.")
    sub.add_parser("doctor", help="Check the local environment is healthy.")

    args = parser.parse_args(argv)

    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "doctor":
        return _doctor()

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
