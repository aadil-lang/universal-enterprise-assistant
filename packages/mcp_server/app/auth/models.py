"""
Validated caller identity models for internal Model Context Protocol (MCP) requests.
Strictly defines caller attributes propagated from the authenticated API Gateway.
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRole(str, Enum):
    """Approved enterprise authorization roles."""
    EMPLOYEE = "employee"
    HR_ADMIN = "hr_admin"


class CallerIdentity(BaseModel):
    """
    Typed, validated caller identity transferred via X-Internal-Identity header.
    Guarantees user identifier, employee number, and role integrity.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str = Field(..., min_length=1, description="Authenticated principal user identifier or UUID")
    employee_number: str = Field(..., min_length=1, description="Assigned employee identifier (e.g., E101, E102)")
    role: UserRole = Field(..., description="Role-based access level ('employee' or 'hr_admin')")

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("user_id must be a non-empty string.")
        return s

    @field_validator("employee_number")
    @classmethod
    def validate_employee_number(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("employee_number must be a non-empty string.")
        return s
