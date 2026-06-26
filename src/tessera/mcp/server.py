"""The Tessera MCP server — `tessera_ask` and `tessera_verify` over the verified pipeline.

The tool *logic* lives in plain functions (:func:`tool_ask`, :func:`tool_verify`) that take a
:class:`~tessera.runtime.Runtime`, so it is unit-testable with no MCP dependency. :func:`build_server`
binds those functions to a FastMCP server (the SDK is imported here, lazily, behind the ``mcp`` extra).
"""

from __future__ import annotations

from typing import Any

from ..runtime import Runtime


def tool_ask(runtime: Runtime, question: str, route: bool = False, sign: bool = False
             ) -> dict[str, Any]:
    """Answer a finance question and return the *verified* result (verdict + evidence)."""
    return runtime.ask(question, route=route, sign=sign)


def tool_verify(runtime: Runtime, receipt: dict, expect_key: str | None = None) -> dict[str, Any]:
    """Offline-verify a signed receipt; optionally assert the signer's public key."""
    return runtime.verify_receipt(receipt, expect_key=expect_key)


def build_server(seed: int = 20260626):
    """Construct the FastMCP server with both tools bound to a shared runtime."""
    from mcp.server.fastmcp import FastMCP

    runtime = Runtime(seed=seed)
    server = FastMCP("tessera")

    @server.tool()
    def tessera_ask(question: str, route: bool = False, sign: bool = False) -> dict:
        """Ask a finance question over the governed ledger. Returns the number, an independent
        verdict (pass/warn/fail), the executed SQL, grounded issues, and — if sign=True — a signed,
        offline-verifiable receipt. route=True runs the cost cascade (cheap model first)."""
        return tool_ask(runtime, question, route=route, sign=sign)

    @server.tool()
    def tessera_verify(receipt: dict, expect_key: str | None = None) -> dict:
        """Verify a Tessera receipt offline. Pass expect_key (hex public key) to assert the signer."""
        return tool_verify(runtime, receipt, expect_key=expect_key)

    return server


def main() -> None:
    """Run the MCP server over stdio (the standard MCP transport)."""
    build_server().run()


if __name__ == "__main__":
    main()
