"""Internal identity authentication and authorization for MCP server."""

from app.auth.context import (
    MCPAuthorizationError,
    authorize_employee_access,
    caller_identity_var,
    get_current_caller,
    reset_current_caller,
    set_current_caller,
)
from app.auth.middleware import HMACAuthMiddleware
from app.auth.models import CallerIdentity, UserRole
from app.auth.signer import create_internal_auth_headers

__all__ = [
    "CallerIdentity",
    "HMACAuthMiddleware",
    "MCPAuthorizationError",
    "UserRole",
    "authorize_employee_access",
    "caller_identity_var",
    "create_internal_auth_headers",
    "get_current_caller",
    "reset_current_caller",
    "set_current_caller",
]
