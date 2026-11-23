"""Typed, parameterized MCP tools for employee records."""

from app.tools.employee_tools import (
    VALID_STATUS_FILTERS,
    get_employee_assigned_assets_handler,
    get_employee_it_tickets_handler,
    get_employee_leave_balances_handler,
    get_employee_profile_handler,
    register_employee_tools,
)

__all__ = [
    "VALID_STATUS_FILTERS",
    "get_employee_assigned_assets_handler",
    "get_employee_it_tickets_handler",
    "get_employee_leave_balances_handler",
    "get_employee_profile_handler",
    "register_employee_tools",
]
