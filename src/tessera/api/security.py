"""API security primitives — fail-closed auth on non-loopback binds, and a request-body cap.

Two of the non-negotiables live here. (1) **Auth on any non-loopback bind:** the app refuses to start
when bound to a routable interface without a token, and when a token is set every request must carry
it (compared constant-time). Loopback stays zero-config. (2) **Bound the request body** an attacker
controls, before doing any work.

Note on injection: the API accepts *natural-language questions*, never SQL. All SQL is built from the
trusted semantic layer (parameterized), so there is no user-controlled SQL path to inject into.
"""

from __future__ import annotations

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_LOOPBACK = {"127.0.0.1", "localhost", "::1", "0.0.0.0.localhost"}


def is_loopback(host: str) -> bool:
    return host.strip().lower() in _LOOPBACK


class BindSecurityError(RuntimeError):
    """Raised at startup when a non-loopback bind has no auth token (fail closed)."""


def check_bind_security(host: str, api_token: str | None) -> None:
    """Refuse to serve a routable interface without a token."""
    if not is_loopback(host) and not api_token:
        raise BindSecurityError(
            f"refusing to bind non-loopback host {host!r} without TESSERA_API_TOKEN "
            "(set a token, or bind 127.0.0.1 for zero-config local use)"
        )


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared body exceeds the cap, before handling them."""

    def __init__(self, app, max_bytes: int = 16_384) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_bytes:
                    return JSONResponse({"detail": "request body too large"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "invalid content-length"}, status_code=400)
        return await call_next(request)


def token_ok(provided: str | None, expected: str) -> bool:
    """Constant-time bearer-token check."""
    if not provided:
        return False
    scheme, _, value = provided.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return False
    return hmac.compare_digest(value, expected)
