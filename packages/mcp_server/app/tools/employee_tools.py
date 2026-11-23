"""
Genuine Model Context Protocol (MCP) Tools for Employee Database Access.
Exposes four typed, parameterized, read-only tools accessing PostgreSQL employee data:
1. get_employee_profile(employee_number)
2. get_employee_leave_balances(employee_number, fiscal_year=None)
3. get_employee_assigned_assets(employee_number)
4. get_employee_it_tickets(employee_number, status_filter="all")

Enforces parameterized queries, read-only safety, central fiscal year resolution,
and complete exclusion of credentials or authentication hashes.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text

from app.auth import authorize_employee_access
from app.config.settings import get_mcp_settings
from app.database.connection import get_db_manager

logger = logging.getLogger(__name__)

VALID_STATUS_FILTERS = {"all", "open", "in_progress", "resolved", "closed"}


def _validate_employee_number(employee_number: str) -> str:
    """Validates and normalizes employee_number argument."""
    if not employee_number or not str(employee_number).strip():
        raise ValueError("employee_number must be a non-empty string.")
    return str(employee_number).strip()


def _check_employee_exists(conn, employee_number: str) -> bool:
    """Helper executing a parameterized query to check if an employee exists."""
    stmt = text("SELECT 1 FROM employees WHERE employee_number = :emp_no")
    res = conn.execute(stmt, {"emp_no": employee_number}).first()
    return res is not None


# =============================================================================
# Tool 1 Implementation: get_employee_profile
# =============================================================================
def get_employee_profile_handler(employee_number: str) -> Dict[str, Any]:
    """
    Retrieves demographic and organizational profile for an employee.
    Strictly excludes authentication principals, credentials, and password hashes.
    """
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)
    db = get_db_manager()

    query = text(
        """
        SELECT 
            id,
            employee_number,
            first_name,
            last_name,
            corporate_email,
            job_title,
            department,
            hire_date,
            employment_status
        FROM employees
        WHERE employee_number = :emp_no
        """
    )

    with db.get_connection() as conn:
        row = conn.execute(query, {"emp_no": emp_no}).mappings().first()

    if not row:
        return {
            "found": False,
            "message": f"Employee with number '{emp_no}' not found.",
        }

    return {
        "found": True,
        "employee": {
            "id": str(row["id"]),
            "employee_number": str(row["employee_number"]),
            "first_name": str(row["first_name"]),
            "last_name": str(row["last_name"]),
            "full_name": f"{row['first_name']} {row['last_name']}",
            "corporate_email": str(row["corporate_email"]),
            "job_title": str(row["job_title"]),
            "department": str(row["department"]),
            "hire_date": str(row["hire_date"]),
            "employment_status": str(row["employment_status"]),
        },
    }


# =============================================================================
# Tool 2 Implementation: get_employee_leave_balances
# =============================================================================
def get_employee_leave_balances_handler(
    employee_number: str,
    fiscal_year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retrieves accrued, used, pending, and available leave balances for an employee.
    Resolves omitted fiscal year via the central DEMO_FISCAL_YEAR setting.
    """
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)
    settings = get_mcp_settings()
    target_year = int(fiscal_year) if fiscal_year is not None else settings.DEMO_FISCAL_YEAR

    db = get_db_manager()

    with db.get_connection() as conn:
        if not _check_employee_exists(conn, emp_no):
            return {
                "found": False,
                "message": f"Employee with number '{emp_no}' not found.",
            }

        query = text(
            """
            SELECT 
                lb.leave_type,
                lb.accrued_days,
                lb.used_days,
                lb.pending_days,
                lb.available_days,
                lb.fiscal_year
            FROM leave_balances lb
            JOIN employees e ON lb.employee_id = e.id
            WHERE e.employee_number = :emp_no
              AND lb.fiscal_year = :year
            ORDER BY lb.leave_type ASC
            """
        )
        rows = conn.execute(query, {"emp_no": emp_no, "year": target_year}).mappings().all()

    if not rows:
        return {
            "found": True,
            "employee_number": emp_no,
            "fiscal_year": target_year,
            "balances": [],
            "message": f"No leave balance records found for fiscal year {target_year}.",
        }

    formatted_balances: List[Dict[str, Any]] = []
    for r in rows:
        accrued = float(r["accrued_days"])
        used = float(r["used_days"])
        pending = float(r["pending_days"])
        available = float(r["available_days"])
        formatted_balances.append(
            {
                "leave_type": str(r["leave_type"]),
                "accrued_days": accrued,
                "used_days": used,
                "pending_days": pending,
                "available_days": available,
                "fiscal_year": int(r["fiscal_year"]),
            }
        )

    return {
        "found": True,
        "employee_number": emp_no,
        "fiscal_year": target_year,
        "balances": formatted_balances,
    }


# =============================================================================
# Tool 3 Implementation: get_employee_assigned_assets
# =============================================================================
def get_employee_assigned_assets_handler(employee_number: str) -> Dict[str, Any]:
    """
    Retrieves IT hardware and assets assigned to the specified employee.
    Returns an empty collection when no assets are assigned.
    """
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)
    db = get_db_manager()

    with db.get_connection() as conn:
        if not _check_employee_exists(conn, emp_no):
            return {
                "found": False,
                "message": f"Employee with number '{emp_no}' not found.",
            }

        query = text(
            """
            SELECT 
                ia.id,
                ia.asset_tag,
                ia.device_type,
                ia.make_model,
                ia.serial_number,
                ia.assigned_date,
                ia.condition_status
            FROM it_assets ia
            JOIN employees e ON ia.employee_id = e.id
            WHERE e.employee_number = :emp_no
            ORDER BY ia.asset_tag ASC
            """
        )
        rows = conn.execute(query, {"emp_no": emp_no}).mappings().all()

    formatted_assets: List[Dict[str, Any]] = [
        {
            "id": str(r["id"]),
            "asset_tag": str(r["asset_tag"]),
            "device_type": str(r["device_type"]),
            "make_model": str(r["make_model"]),
            "serial_number": str(r["serial_number"]),
            "assigned_date": str(r["assigned_date"]) if r["assigned_date"] else None,
            "condition_status": str(r["condition_status"]),
        }
        for r in rows
    ]

    return {
        "found": True,
        "employee_number": emp_no,
        "assets": formatted_assets,
    }


# =============================================================================
# Tool 4 Implementation: get_employee_it_tickets
# =============================================================================
def get_employee_it_tickets_handler(
    employee_number: str,
    status_filter: str = "all",
) -> Dict[str, Any]:
    """
    Retrieves IT support tickets for the specified employee.
    Supports status filters ('all', 'open', 'in_progress', 'resolved', 'closed').
    Rejects invalid filter values with ValueError.
    """
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)
    norm_filter = (status_filter or "all").strip().lower()

    if norm_filter not in VALID_STATUS_FILTERS:
        raise ValueError(
            f"Invalid status_filter '{status_filter}'. Supported filters are: "
            f"{', '.join(sorted(VALID_STATUS_FILTERS))}."
        )

    db = get_db_manager()

    with db.get_connection() as conn:
        if not _check_employee_exists(conn, emp_no):
            return {
                "found": False,
                "message": f"Employee with number '{emp_no}' not found.",
            }

        if norm_filter == "all":
            query = text(
                """
                SELECT 
                    it.id,
                    it.ticket_number,
                    it.title,
                    it.description,
                    it.category,
                    it.priority,
                    it.status,
                    it.created_at,
                    it.updated_at
                FROM it_tickets it
                JOIN employees e ON it.employee_id = e.id
                WHERE e.employee_number = :emp_no
                ORDER BY it.created_at DESC
                """
            )
            rows = conn.execute(query, {"emp_no": emp_no}).mappings().all()
        else:
            query = text(
                """
                SELECT 
                    it.id,
                    it.ticket_number,
                    it.title,
                    it.description,
                    it.category,
                    it.priority,
                    it.status,
                    it.created_at,
                    it.updated_at
                FROM it_tickets it
                JOIN employees e ON it.employee_id = e.id
                WHERE e.employee_number = :emp_no
                  AND it.status = :status_filter
                ORDER BY it.created_at DESC
                """
            )
            rows = conn.execute(query, {"emp_no": emp_no, "status_filter": norm_filter}).mappings().all()

    formatted_tickets: List[Dict[str, Any]] = [
        {
            "id": str(r["id"]),
            "ticket_number": str(r["ticket_number"]),
            "title": str(r["title"]),
            "description": str(r["description"]),
            "category": str(r["category"]),
            "priority": str(r["priority"]),
            "status": str(r["status"]),
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
            "updated_at": r["updated_at"].isoformat() if hasattr(r["updated_at"], "isoformat") else str(r["updated_at"]),
        }
        for r in rows
    ]

    return {
        "found": True,
        "employee_number": emp_no,
        "status_filter": norm_filter,
        "tickets": formatted_tickets,
    }


# =============================================================================
# FastMCP Registration Hook
# =============================================================================
def register_employee_tools(mcp: FastMCP) -> None:
    """
    Registers the four genuine employee database tools with the FastMCP application.
    Enables automatic typed schema generation and MCP discovery via tools/list.
    """

    @mcp.tool()
    def get_employee_profile(employee_number: str) -> Dict[str, Any]:
        """
        Retrieve employee demographic and organizational profile by employee number.
        Returns job title, department, corporate email, hire date, and status.
        Does not expose authentication credentials.
        """
        return get_employee_profile_handler(employee_number)

    @mcp.tool()
    def get_employee_leave_balances(
        employee_number: str,
        fiscal_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve accrued, used, pending, and available leave balances for an employee.
        When fiscal_year is omitted, the central system demonstration fiscal year is used.
        """
        return get_employee_leave_balances_handler(employee_number, fiscal_year)

    @mcp.tool()
    def get_employee_assigned_assets(employee_number: str) -> Dict[str, Any]:
        """
        Retrieve IT hardware, laptops, and equipment assigned to an employee.
        Returns asset tags, serial numbers, make/model, and condition status.
        """
        return get_employee_assigned_assets_handler(employee_number)

    @mcp.tool()
    def get_employee_it_tickets(
        employee_number: str,
        status_filter: str = "all",
    ) -> Dict[str, Any]:
        """
        Retrieve IT support tickets submitted by an employee.
        Supports status filtering ('all', 'open', 'in_progress', 'resolved', 'closed').
        """
        return get_employee_it_tickets_handler(employee_number, status_filter)
