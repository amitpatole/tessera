"""The Tessera REST API (Phase 6) — the verified pipeline over HTTP.

``create_app()`` builds a FastAPI app that generates the warehouse once at startup and serves
``/ask`` (resolve → verify, optionally cascade + sign), ``/verify``, ``/metrics`` and ``/health``.
Lives behind the ``api`` extra (``pip install 'tessera-analytics[api]'``); the rest of the package
never imports FastAPI.
"""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
