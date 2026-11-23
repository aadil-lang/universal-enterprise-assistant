"""
Request-scoped caller identity context and authorization enforcement.
Provides isolated, task-local identity tracking and role-based employee access enforcement.
"""

from contextvars import ContextVar
from typing import Optional

from app.auth.models import CallerIdentity, UserRole


class MCPAuthorizationError(Exception):
    """Raised when caller identity is missing, invalid, or unauthorized for the requested record."""
    pass


# Request-scoped task-isolated identity storage
caller_identity_var: ContextVar[Optional[CallerIdentity]] = ContextVar("caller_identity", default=None)


def get_current_caller() -> CallerIdentity:
    """
    Retrieves the verified caller identity for the current request.
    Raises MCPAuthorizationError if unauthenticated or missing context.
    """
    caller = caller_identity_var.get()
    if caller is None:
        raise MCPAuthorizationError("Unauthorized: Missing verified caller identity context.")
    return caller


def set_current_caller(identity: Optional[CallerIdentity]):
    """Sets the verified caller identity and returns the context token."""
    return caller_identity_var.set(identity)


def reset_current_caller(token):
    """Resets caller identity using the context token in a finally block."""
    caller_identity_var.reset(token)


def authorize_employee_access(requested_employee_number: str) -> CallerIdentity:
    """
    Enforces role-based employee record access:
    - hr_admin: Permitted to access any employee record.
    - employee: Permitted ONLY if requested_employee_number equals the caller's employee_number.
    - missing/unauthenticated: Denied.
    """
    caller = get_current_caller()
    norm_req = str(requested_employee_number).strip()

    if caller.role == UserRole.HR_ADMIN:
        return caller

    if caller.role == UserRole.EMPLOYEE:
        if caller.employee_number != norm_req:
            raise MCPAuthorizationError(
                f"Forbidden: Employee '{caller.employee_number}' is not authorized to access records for employee '{norm_req}'."
            )
        return caller

    raise MCPAuthorizationError(f"Forbidden: Role '{caller.role}' is not authorized to access employee records.")
