"""
HMAC-SHA256 authentication middleware for internal Model Context Protocol (MCP) requests.
Validates X-Internal-Identity and X-Internal-Signature headers using constant-time comparison.
Enforces fail-closed authentication on all MCP endpoints while leaving health probes open.
"""

import hashlib
import hmac
import json
import logging
from typing import Callable, Optional

from app.auth.context import reset_current_caller, set_current_caller
from app.auth.models import CallerIdentity
from app.config.settings import get_mcp_settings

logger = logging.getLogger(__name__)

# Endpoints excluded from internal HMAC verification (liveness/root info probes)
UNPROTECTED_PATHS = {"/health/live", "/", "/docs", "/redoc", "/openapi.json"}


class HMACAuthMiddleware:
    """
    Pure ASGI middleware that intercepts MCP requests, enforces HMAC verification,
    and binds the verified caller identity to a request-scoped context variable.
    """

    def __init__(self, app: Callable, secret: Optional[str] = None):
        self.app = app
        self.secret = secret

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Allow unprotected liveness and discovery endpoints
        if path in UNPROTECTED_PATHS:
            await self.app(scope, receive, send)
            return

        # For all protected endpoints (specifically /mcp and subpaths):
        # 1. Resolve server secret; fail closed if absent or empty
        effective_secret = self.secret if self.secret is not None else get_mcp_settings().INTERNAL_MCP_SECRET
        if not effective_secret or not effective_secret.strip():
            logger.error("Authentication rejected: INTERNAL_MCP_SECRET is empty or unconfigured.")
            await self._send_unauthorized(send, "Server authentication configuration failure.")
            return

        # 2. Extract headers (case-insensitive lookup from ASGI bytes list)
        headers = dict(scope.get("headers", []))
        raw_identity = headers.get(b"x-internal-identity")
        raw_signature = headers.get(b"x-internal-signature")

        if not raw_identity or not raw_signature:
            await self._send_unauthorized(
                send,
                "Missing required X-Internal-Identity or X-Internal-Signature headers.",
            )
            return

        # 3. Compute expected HMAC-SHA256 over exact raw bytes of X-Internal-Identity
        expected_sig = hmac.new(
            effective_secret.encode("utf-8"),
            raw_identity,
            hashlib.sha256,
        ).hexdigest()

        try:
            provided_sig = raw_signature.decode("utf-8").strip()
        except UnicodeDecodeError:
            await self._send_unauthorized(send, "Invalid header encoding.")
            return

        # 4. Constant-time comparison
        if not hmac.compare_digest(expected_sig, provided_sig):
            logger.warning("HMAC signature verification failed for incoming request to %s", path)
            await self._send_unauthorized(send, "Invalid HMAC signature.")
            return

        # 5. Parse and validate identity payload structure
        try:
            identity_json_str = raw_identity.decode("utf-8")
            payload = json.loads(identity_json_str)
            caller = CallerIdentity.model_validate(payload)
        except Exception as parse_err:
            logger.warning("Malformed identity payload in X-Internal-Identity: %s", parse_err)
            await self._send_unauthorized(send, f"Malformed identity payload: {parse_err}")
            return

        # 6. Bind verified caller identity to request-scoped ContextVar
        token = set_current_caller(caller)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_current_caller(token)

    async def _send_unauthorized(self, send, detail: str):
        """Constructs and delivers a pure ASGI 401 Unauthorized JSON response."""
        content = json.dumps({"error": "Unauthorized", "detail": detail}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(content)).encode("ascii")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": content,
                "more_body": False,
            }
        )
