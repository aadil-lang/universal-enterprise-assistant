"""
Unit tests for API security response headers (Phase 5B.1).
Validates:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Referrer-Policy: strict-origin-when-cross-origin
- Content-Security-Policy: default-src 'none'; frame-ancestors 'none' (API endpoints)
- Content-Security-Policy: relaxed for docs endpoints
- Strict-Transport-Security: present only when HTTPS is active
"""

from unittest.mock import MagicMock
from fastapi import Response
import pytest

from app.main import add_security_headers


def run_coro(coro):
    """Executes a simple coroutine synchronously without socket-based event loops."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


def test_security_headers_standard_http():
    """Verify security headers added to standard HTTP API responses."""
    request = MagicMock()
    request.url.scheme = "http"
    request.url.path = "/api/v1/chat"
    request.headers.get.return_value = None  # No x-forwarded-proto

    async def call_next(req):
        return Response(content="ok", status_code=200)

    response = run_coro(add_security_headers(request, call_next))

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    # HSTS must NOT be set on HTTP
    assert "Strict-Transport-Security" not in response.headers


def test_security_headers_https_enforces_hsts():
    """Verify HSTS header is attached when connection is HTTPS or behind HTTPS proxy."""
    # Direct HTTPS
    request_https = MagicMock()
    request_https.url.scheme = "https"
    request_https.url.path = "/api/v1/auth/login"
    request_https.headers.get.return_value = None

    async def call_next(req):
        return Response(content="ok", status_code=200)

    response = run_coro(add_security_headers(request_https, call_next))
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

    # Behind reverse proxy with x-forwarded-proto: https
    request_proxy = MagicMock()
    request_proxy.url.scheme = "http"
    request_proxy.url.path = "/api/v1/auth/login"
    request_proxy.headers.get.side_effect = lambda k: "https" if k.lower() == "x-forwarded-proto" else None

    response_proxy = run_coro(add_security_headers(request_proxy, call_next))
    assert "Strict-Transport-Security" in response_proxy.headers


def test_security_headers_docs_relaxed_csp():
    """Verify Swagger/Redoc UI documentation routes receive appropriate CSP allowing assets."""
    request_docs = MagicMock()
    request_docs.url.scheme = "http"
    request_docs.url.path = "/docs"
    request_docs.headers.get.return_value = None

    async def call_next(req):
        return Response(content="swagger ui html", status_code=200)

    response = run_coro(add_security_headers(request_docs, call_next))
    assert "https://cdn.jsdelivr.net" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
