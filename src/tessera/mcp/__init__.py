"""MCP adapter (Phase 7) — expose Tessera's verified pipeline as MCP tools.

Two tools, `tessera_ask` and `tessera_verify`, wrap the same :class:`~tessera.runtime.Runtime` the
REST API uses, so an MCP client (Claude, an agent framework) gets the *verified* answer plus its
evidence — verdict, executed SQL, grounded issues, and an optional signed receipt. Lives behind the
``mcp`` extra (``pip install 'tessera-analytics[mcp]'``); the SDK is imported only when the server
runs, so the rest of the package — and the tests of the tool logic — never need it.
"""

from __future__ import annotations

from .server import build_server, main

__all__ = ["build_server", "main"]
