"""
Transactional FastMCP Tools for Enterprise Assistant.
Implements the 9 genuine transactional and status workflows:
1. submit_leave_request
2. cancel_leave_request
3. get_leave_request_status
4. create_it_ticket
5. update_it_ticket
6. get_it_ticket_status
7. submit_reimbursement_request
8. get_reimbursement_status
9. create_hr_service_request
10. get_hr_request_status
11. submit_equipment_request
12. get_equipment_request_status
13. update_employee_contact
14. get_all_requests_status

Enforces strict parameterization, caller authentication context,
server-side validation, ownership restrictions, and atomic transactions.
"""

import datetime
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text

from app.auth import authorize_employee_access, get_current_caller
from app.auth.models import UserRole
from app.config.settings import get_mcp_settings
from app.database.connection import get_db_manager

logger = logging.getLogger(__name__)

# Allowed sets for server-side validation
VALID_LEAVE_TYPES = {"annual", "sick"}
VALID_IT_CATEGORIES = {"hardware", "software", "network", "vpn", "security", "general"}
VALID_IT_PRIORITIES = {"low", "medium", "high", "urgent"}
VALID_REIMBURSEMENT_CATEGORIES = {"ergonomic_stipend", "travel", "equipment", "general"}
VALID_HR_SERVICE_CATEGORIES = {
    "employment_verification_letter",
    "employment_certificate",
    "payroll_clarification",
    "general_hr",
    "benefits_inquiry",
}
VALID_EQUIPMENT_TYPES = {"laptop", "monitor", "keyboard", "headset", "docking_station", "chair", "other"}
PERMITTED_CONTACT_FIELDS = {
    "phone_number",
    "emergency_contact_name",
    "emergency_contact_phone",
    "personal_email",
}
PROTECTED_CONTACT_FIELDS = {
    "id",
    "employee_number",
    "corporate_email",
    "job_title",
    "department",
    "hire_date",
    "employment_status",
    "role",
    "salary",
}


def _validate_employee_number(employee_number: str) -> str:
    """Validates and normalizes employee_number."""
    if not employee_number or not str(employee_number).strip():
        raise ValueError("employee_number must be a non-empty string.")
    return str(employee_number).strip()


def _get_employee_id(conn, emp_no: str) -> Optional[str]:
    """Helper resolving employee_number to UUID string."""
    stmt = text("SELECT id FROM employees WHERE employee_number = :emp_no")
    row = conn.execute(stmt, {"emp_no": emp_no}).mappings().first()
    return str(row["id"]) if row else None


def _calculate_working_days(start_date: datetime.date, end_date: datetime.date) -> int:
    """Calculates number of working days (Monday-Friday) between dates inclusive."""
    if start_date > end_date:
        raise ValueError("start_date cannot be later than end_date.")
    days = 0
    cur = start_date
    while cur <= end_date:
        if cur.weekday() < 5:  # Monday=0, Friday=4
            days += 1
        cur += datetime.timedelta(days=1)
    return max(1, days)


# =============================================================================
# Tool 1: submit_leave_request
# =============================================================================
def submit_leave_request_handler(
    employee_number: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    caller = authorize_employee_access(emp_no)

    lt = (leave_type or "").strip().lower()
    if lt not in VALID_LEAVE_TYPES:
        raise ValueError(f"Invalid leave_type '{leave_type}'. Allowed: {', '.join(sorted(VALID_LEAVE_TYPES))}")

    try:
        s_date = datetime.date.fromisoformat(start_date.strip())
        e_date = datetime.date.fromisoformat(end_date.strip())
    except Exception as e:
        raise ValueError(f"Invalid date format: {e}. Expected YYYY-MM-DD.")

    if s_date > e_date:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date}).")

    days_req = _calculate_working_days(s_date, e_date)
    settings = get_mcp_settings()
    target_year = s_date.year

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"success": False, "error": f"Employee {emp_no} not found."}

        # 1. Check leave balances
        bal_query = text(
            """
            SELECT accrued_days, used_days, pending_days, available_days
            FROM leave_balances
            WHERE employee_id = :emp_id AND leave_type = :lt AND fiscal_year = :year
            """
        )
        bal_row = conn.execute(bal_query, {"emp_id": emp_id, "lt": lt, "year": target_year}).mappings().first()

        if not bal_row:
            return {
                "success": False,
                "error": f"No {lt} leave balance record found for employee {emp_no} in fiscal year {target_year}.",
            }

        avail_before = float(bal_row["available_days"])
        if avail_before < days_req:
            return {
                "success": False,
                "error": (
                    f"Insufficient leave balance: You requested {days_req} day(s), "
                    f"but only have {avail_before} day(s) available for {lt} leave."
                ),
                "available_days": avail_before,
                "requested_days": days_req,
            }

        # 2. Check overlapping leave requests
        overlap_query = text(
            """
            SELECT request_number, start_date, end_date, status
            FROM leave_requests
            WHERE employee_id = :emp_id
              AND status IN ('pending', 'approved')
              AND start_date <= :e_date
              AND end_date >= :s_date
            """
        )
        overlap_row = conn.execute(
            overlap_query,
            {"emp_id": emp_id, "s_date": str(s_date), "e_date": str(e_date)},
        ).mappings().first()

        if overlap_row:
            return {
                "success": False,
                "error": (
                    f"Overlapping leave request {overlap_row['request_number']} already exists "
                    f"from {overlap_row['start_date']} to {overlap_row['end_date']} "
                    f"with status '{overlap_row['status']}'."
                ),
            }

        # 3. Generate sequential request number
        cnt_query = text("SELECT COUNT(*) AS cnt FROM leave_requests")
        cnt_res = conn.execute(cnt_query).mappings().first()["cnt"]
        req_number = f"LV-{target_year}-{int(cnt_res) + 1:04d}"

        # 4. Insert leave request atomically
        insert_query = text(
            """
            INSERT INTO leave_requests (
                id, request_number, employee_id, leave_type, start_date, end_date,
                days_requested, reason, status, created_at, updated_at
            ) VALUES (
                :id, :req_no, :emp_id, :lt, :s_date, :e_date,
                :days_req, :reason, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        )
        new_id = str(uuid.uuid4())
        conn.execute(
            insert_query,
            {
                "id": new_id,
                "req_no": req_number,
                "emp_id": emp_id,
                "lt": lt,
                "s_date": str(s_date),
                "e_date": str(e_date),
                "days_req": days_req,
                "reason": reason or "",
            },
        )

        # 5. Atomically reserve leave balance (deduct available, increment pending)
        update_bal = text(
            """
            UPDATE leave_balances
            SET pending_days = pending_days + :days_req,
                available_days = available_days - :days_req,
                updated_at = CURRENT_TIMESTAMP
            WHERE employee_id = :emp_id AND leave_type = :lt AND fiscal_year = :year
            """
        )
        conn.execute(update_bal, {"days_req": days_req, "emp_id": emp_id, "lt": lt, "year": target_year})
        conn.commit()

    avail_after = max(0.0, avail_before - days_req)

    return {
        "success": True,
        "request_number": req_number,
        "status": "pending",
        "leave_type": lt,
        "start_date": str(s_date),
        "end_date": str(e_date),
        "days_requested": days_req,
        "available_balance_before": avail_before,
        "projected_available_balance": avail_after,
        "message": f"Leave request {req_number} submitted successfully. Pending manager approval.",
    }


# =============================================================================
# Tool 2: cancel_leave_request
# =============================================================================
def cancel_leave_request_handler(
    employee_number: str,
    request_number: str,
    cancellation_reason: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)
    req_no = (request_number or "").strip()
    if not req_no:
        raise ValueError("request_number must be provided.")

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"success": False, "error": f"Employee {emp_no} not found."}

        stmt = text(
            """
            SELECT id, status, start_date, end_date, days_requested, leave_type
            FROM leave_requests
            WHERE request_number = :req_no AND employee_id = :emp_id
            """
        )
        row = conn.execute(stmt, {"req_no": req_no, "emp_id": emp_id}).mappings().first()

        if not row:
            return {"success": False, "error": f"Leave request '{req_no}' not found for employee {emp_no}."}

        current_status = row["status"]
        if current_status != "pending":
            return {
                "success": False,
                "error": f"Leave request '{req_no}' cannot be cancelled because its current status is '{current_status}'. Only pending requests can be cancelled.",
                "current_status": current_status,
            }

        upd = text(
            """
            UPDATE leave_requests
            SET status = 'cancelled',
                cancelled_at = CURRENT_TIMESTAMP,
                cancellation_reason = :reason,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
            """
        )
        conn.execute(upd, {"id": row["id"], "reason": cancellation_reason or "Cancelled by employee"})

        # Atomically restore leave balance
        days_to_restore = float(row["days_requested"])
        leave_lt = row["leave_type"]
        s_date_obj = datetime.date.fromisoformat(str(row["start_date"]))
        target_year = s_date_obj.year

        restore_bal = text(
            """
            UPDATE leave_balances
            SET pending_days = MAX(0.0, pending_days - :days_restored),
                available_days = available_days + :days_restored,
                updated_at = CURRENT_TIMESTAMP
            WHERE employee_id = :emp_id AND leave_type = :lt AND fiscal_year = :year
            """
        )
        conn.execute(
            restore_bal,
            {
                "days_restored": days_to_restore,
                "emp_id": emp_id,
                "lt": leave_lt,
                "year": target_year,
            },
        )
        conn.commit()

    return {
        "success": True,
        "request_number": req_no,
        "status": "cancelled",
        "message": f"Leave request {req_no} has been cancelled successfully.",
    }


# =============================================================================
# Tool 3: get_leave_request_status
# =============================================================================
def get_leave_request_status_handler(
    employee_number: str,
    request_number: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"found": False, "message": f"Employee {emp_no} not found."}

        if request_number:
            stmt = text(
                """
                SELECT request_number, leave_type, start_date, end_date,
                       days_requested, reason, status, cancellation_reason, created_at, updated_at
                FROM leave_requests
                WHERE employee_id = :emp_id AND request_number = :req_no
                """
            )
            row = conn.execute(stmt, {"emp_id": emp_id, "req_no": request_number.strip()}).mappings().first()
            if not row:
                return {"found": False, "message": f"Leave request '{request_number}' not found."}
            return {
                "found": True,
                "request": {
                    "request_number": row["request_number"],
                    "leave_type": row["leave_type"],
                    "start_date": str(row["start_date"]),
                    "end_date": str(row["end_date"]),
                    "days_requested": float(row["days_requested"]),
                    "reason": row["reason"],
                    "status": row["status"],
                    "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
                },
            }
        else:
            stmt = text(
                """
                SELECT request_number, leave_type, start_date, end_date,
                       days_requested, status, created_at
                FROM leave_requests
                WHERE employee_id = :emp_id
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
            rows = conn.execute(stmt, {"emp_id": emp_id}).mappings().all()
            return {
                "found": True,
                "employee_number": emp_no,
                "requests": [
                    {
                        "request_number": r["request_number"],
                        "leave_type": r["leave_type"],
                        "start_date": str(r["start_date"]),
                        "end_date": str(r["end_date"]),
                        "days_requested": float(r["days_requested"]),
                        "status": r["status"],
                        "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
                    }
                    for r in rows
                ],
            }


# =============================================================================
# Tool 4: create_it_ticket
# =============================================================================
def create_it_ticket_handler(
    employee_number: str,
    title: str,
    description: str,
    category: str,
    priority: str = "medium",
    asset_tag: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    t_title = (title or "").strip()
    t_desc = (description or "").strip()
    t_cat = (category or "").strip().lower()
    t_prio = (priority or "medium").strip().lower()

    if not t_title or not t_desc:
        raise ValueError("title and description are required for an IT ticket.")
    if t_cat not in VALID_IT_CATEGORIES:
        t_cat = "general"
    if t_prio not in VALID_IT_PRIORITIES:
        raise ValueError(f"Invalid priority '{priority}'. Allowed: {', '.join(sorted(VALID_IT_PRIORITIES))}")

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"success": False, "error": f"Employee {emp_no} not found."}

        # Sequential ticket number
        cnt_res = conn.execute(text("SELECT COUNT(*) AS cnt FROM it_tickets")).mappings().first()["cnt"]
        ticket_number = f"IT-{1042 + int(cnt_res) + 1}"

        ins = text(
            """
            INSERT INTO it_tickets (
                id, employee_id, ticket_number, title, description,
                category, priority, status, asset_tag, created_at, updated_at
            ) VALUES (
                :id, :emp_id, :t_no, :title, :desc,
                :cat, :prio, 'open', :asset_tag, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            ins,
            {
                "id": str(uuid.uuid4()),
                "emp_id": emp_id,
                "t_no": ticket_number,
                "title": t_title,
                "desc": t_desc,
                "cat": t_cat,
                "prio": t_prio,
                "asset_tag": asset_tag,
            },
        )
        conn.commit()

    return {
        "success": True,
        "ticket_number": ticket_number,
        "status": "open",
        "title": t_title,
        "category": t_cat,
        "priority": t_prio,
        "asset_tag": asset_tag,
        "message": f"IT support ticket {ticket_number} created successfully.",
    }


# =============================================================================
# Tool 5: update_it_ticket
# =============================================================================
def update_it_ticket_handler(
    employee_number: str,
    ticket_number: str,
    update_text_val: str,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    t_no = (ticket_number or "").strip()
    upd_content = (update_text_val or "").strip()
    if not t_no or not upd_content:
        raise ValueError("ticket_number and update_text must be non-empty.")

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"success": False, "error": f"Employee {emp_no} not found."}

        stmt = text(
            """
            SELECT id, status, title
            FROM it_tickets
            WHERE ticket_number = :t_no AND employee_id = :emp_id
            """
        )
        row = conn.execute(stmt, {"t_no": t_no, "emp_id": emp_id}).mappings().first()
        if not row:
            return {"success": False, "error": f"Ticket '{t_no}' not found for employee {emp_no}."}

        if row["status"] == "closed":
            return {
                "success": False,
                "error": f"Ticket '{t_no}' is closed and cannot be updated. Please raise a new ticket.",
                "status": "closed",
            }

        # Insert update history
        ins = text(
            """
            INSERT INTO it_ticket_updates (id, ticket_id, employee_id, update_text, created_at)
            VALUES (:id, :t_id, :emp_id, :txt, CURRENT_TIMESTAMP)
            """
        )
        conn.execute(ins, {"id": str(uuid.uuid4()), "t_id": row["id"], "emp_id": emp_id, "txt": upd_content})

        # Update it_tickets updated_at timestamp
        conn.execute(text("UPDATE it_tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = :id"), {"id": row["id"]})
        conn.commit()

    return {
        "success": True,
        "ticket_number": t_no,
        "status": row["status"],
        "update_added": upd_content,
        "message": f"IT ticket {t_no} updated successfully.",
    }


# =============================================================================
# Tool 6: get_it_ticket_status
# =============================================================================
def get_it_ticket_status_handler(
    employee_number: str,
    ticket_number: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"found": False, "message": f"Employee {emp_no} not found."}

        if ticket_number:
            stmt = text(
                """
                SELECT id, ticket_number, title, description, category, priority, status, created_at, updated_at
                FROM it_tickets
                WHERE employee_id = :emp_id AND ticket_number = :t_no
                """
            )
            row = conn.execute(stmt, {"emp_id": emp_id, "t_no": ticket_number.strip()}).mappings().first()
            if not row:
                return {"found": False, "message": f"IT ticket '{ticket_number}' not found."}

            # Fetch update history
            upd_stmt = text(
                """
                SELECT update_text, created_at
                FROM it_ticket_updates
                WHERE ticket_id = :t_id
                ORDER BY created_at ASC
                """
            )
            upd_rows = conn.execute(upd_stmt, {"t_id": row["id"]}).mappings().all()

            return {
                "found": True,
                "ticket": {
                    "ticket_number": row["ticket_number"],
                    "title": row["title"],
                    "description": row["description"],
                    "category": row["category"],
                    "priority": row["priority"],
                    "status": row["status"],
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"]),
                    "updates": [
                        {
                            "update_text": u["update_text"],
                            "created_at": str(u["created_at"]),
                        }
                        for u in upd_rows
                    ],
                },
            }
        else:
            stmt = text(
                """
                SELECT ticket_number, title, category, priority, status, created_at
                FROM it_tickets
                WHERE employee_id = :emp_id
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
            rows = conn.execute(stmt, {"emp_id": emp_id}).mappings().all()
            return {
                "found": True,
                "employee_number": emp_no,
                "tickets": [
                    {
                        "ticket_number": r["ticket_number"],
                        "title": r["title"],
                        "category": r["category"],
                        "priority": r["priority"],
                        "status": r["status"],
                        "created_at": str(r["created_at"]),
                    }
                    for r in rows
                ],
            }


# =============================================================================
# Tool 7: submit_reimbursement_request
# =============================================================================
def submit_reimbursement_request_handler(
    employee_number: str,
    expense_category: str,
    amount: float,
    purchase_date: str,
    description: str,
    vendor: Optional[str] = None,
    receipt_filename: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    cat = (expense_category or "").strip().lower()
    if cat not in VALID_REIMBURSEMENT_CATEGORIES:
        cat = "general"

    amt = float(amount)
    if amt <= 0:
        raise ValueError("Amount must be greater than 0.00.")

    try:
        p_date = datetime.date.fromisoformat(purchase_date.strip())
    except Exception as e:
        raise ValueError(f"Invalid purchase_date '{purchase_date}': {e}. Format: YYYY-MM-DD.")

    desc = (description or "").strip()
    if not desc:
        raise ValueError("Description is required for reimbursement.")

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"success": False, "error": f"Employee {emp_no} not found."}

        # Policy rule: $300 home-office ergonomic stipend
        if cat == "ergonomic_stipend":
            if amt > 300.00:
                return {
                    "success": False,
                    "error": f"Reimbursement amount (${amt:.2f}) exceeds the company ergonomic stipend limit of $300.00.",
                    "policy_limit": 300.00,
                }
            # Check previous claims and enforce cumulative limit of $300
            check_stmt = text(
                """
                SELECT COALESCE(SUM(amount), 0) AS total_claimed
                FROM reimbursement_requests
                WHERE employee_id = :emp_id AND expense_category = 'ergonomic_stipend'
                  AND status IN ('submitted', 'pending_approval', 'approved', 'paid')
                """
            )
            prior_total = float(conn.execute(check_stmt, {"emp_id": emp_id}).mappings().first()["total_claimed"])
            remaining_limit = max(0.0, 300.00 - prior_total)
            if prior_total + amt > 300.00:
                return {
                    "success": False,
                    "error": (
                        f"Reimbursement request of ${amt:.2f} exceeds your remaining ergonomic stipend limit "
                        f"(${remaining_limit:.2f}). You have already claimed ${prior_total:.2f} of your $300.00 entitlement."
                    ),
                    "policy_limit": 300.00,
                    "already_claimed": prior_total,
                    "remaining_limit": remaining_limit,
                }

        # Generate sequential request number
        cnt = conn.execute(text("SELECT COUNT(*) AS cnt FROM reimbursement_requests")).mappings().first()["cnt"]
        req_number = f"EXP-{p_date.year}-{int(cnt) + 1:04d}"

        ins = text(
            """
            INSERT INTO reimbursement_requests (
                id, request_number, employee_id, expense_category, amount, currency,
                purchase_date, description, vendor, receipt_filename, status, created_at, updated_at
            ) VALUES (
                :id, :req_no, :emp_id, :cat, :amt, 'USD',
                :p_date, :desc, :vendor, :receipt, 'submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            ins,
            {
                "id": str(uuid.uuid4()),
                "req_no": req_number,
                "emp_id": emp_id,
                "cat": cat,
                "amt": amt,
                "p_date": str(p_date),
                "desc": desc,
                "vendor": vendor or "",
                "receipt": receipt_filename or "",
            },
        )
        conn.commit()

    return {
        "success": True,
        "request_number": req_number,
        "status": "submitted",
        "expense_category": cat,
        "amount": amt,
        "currency": "USD",
        "message": f"Reimbursement request {req_number} submitted successfully for review.",
    }


# =============================================================================
# Tool 8: get_reimbursement_status
# =============================================================================
def get_reimbursement_status_handler(
    employee_number: str,
    request_number: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"found": False, "message": f"Employee {emp_no} not found."}

        if request_number:
            stmt = text(
                """
                SELECT request_number, expense_category, amount, currency,
                       purchase_date, description, vendor, status, created_at
                FROM reimbursement_requests
                WHERE employee_id = :emp_id AND request_number = :req_no
                """
            )
            row = conn.execute(stmt, {"emp_id": emp_id, "req_no": request_number.strip()}).mappings().first()
            if not row:
                return {"found": False, "message": f"Reimbursement request '{request_number}' not found."}
            return {
                "found": True,
                "request": {
                    "request_number": row["request_number"],
                    "expense_category": row["expense_category"],
                    "amount": float(row["amount"]),
                    "currency": row["currency"],
                    "purchase_date": str(row["purchase_date"]),
                    "description": row["description"],
                    "vendor": row["vendor"],
                    "status": row["status"],
                    "created_at": str(row["created_at"]),
                },
            }
        else:
            stmt = text(
                """
                SELECT request_number, expense_category, amount, currency, status, created_at
                FROM reimbursement_requests
                WHERE employee_id = :emp_id
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
            rows = conn.execute(stmt, {"emp_id": emp_id}).mappings().all()
            return {
                "found": True,
                "employee_number": emp_no,
                "requests": [
                    {
                        "request_number": r["request_number"],
                        "expense_category": r["expense_category"],
                        "amount": float(r["amount"]),
                        "currency": r["currency"],
                        "status": r["status"],
                        "created_at": str(r["created_at"]),
                    }
                    for r in rows
                ],
            }


# =============================================================================
# Tool 9: create_hr_service_request
# =============================================================================
def create_hr_service_request_handler(
    employee_number: str,
    service_category: str,
    purpose: str,
    recipient_details: Optional[str] = None,
    additional_details: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    cat = (service_category or "").strip().lower()
    if cat not in VALID_HR_SERVICE_CATEGORIES:
        cat = "general_hr"

    purp = (purpose or "").strip()
    if not purp:
        raise ValueError("purpose is required for HR service request.")

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"success": False, "error": f"Employee {emp_no} not found."}

        cnt = conn.execute(text("SELECT COUNT(*) AS cnt FROM hr_service_requests")).mappings().first()["cnt"]
        req_number = f"HR-2026-{int(cnt) + 1:04d}"

        ins = text(
            """
            INSERT INTO hr_service_requests (
                id, request_number, employee_id, service_category, purpose,
                recipient_details, additional_details, status, created_at, updated_at
            ) VALUES (
                :id, :req_no, :emp_id, :cat, :purp,
                :recip, :addn, 'submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            ins,
            {
                "id": str(uuid.uuid4()),
                "req_no": req_number,
                "emp_id": emp_id,
                "cat": cat,
                "purp": purp,
                "recip": recipient_details or "",
                "addn": additional_details or "",
            },
        )
        conn.commit()

    return {
        "success": True,
        "request_number": req_number,
        "status": "submitted",
        "service_category": cat,
        "purpose": purp,
        "message": f"HR service request {req_number} created successfully.",
    }


# =============================================================================
# Tool 10: get_hr_request_status
# =============================================================================
def get_hr_request_status_handler(
    employee_number: str,
    request_number: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"found": False, "message": f"Employee {emp_no} not found."}

        if request_number:
            stmt = text(
                """
                SELECT request_number, service_category, purpose,
                       recipient_details, status, created_at
                FROM hr_service_requests
                WHERE employee_id = :emp_id AND request_number = :req_no
                """
            )
            row = conn.execute(stmt, {"emp_id": emp_id, "req_no": request_number.strip()}).mappings().first()
            if not row:
                return {"found": False, "message": f"HR service request '{request_number}' not found."}
            return {
                "found": True,
                "request": {
                    "request_number": row["request_number"],
                    "service_category": row["service_category"],
                    "purpose": row["purpose"],
                    "recipient_details": row["recipient_details"],
                    "status": row["status"],
                    "created_at": str(row["created_at"]),
                },
            }
        else:
            stmt = text(
                """
                SELECT request_number, service_category, purpose, status, created_at
                FROM hr_service_requests
                WHERE employee_id = :emp_id
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
            rows = conn.execute(stmt, {"emp_id": emp_id}).mappings().all()
            return {
                "found": True,
                "employee_number": emp_no,
                "requests": [
                    {
                        "request_number": r["request_number"],
                        "service_category": r["service_category"],
                        "purpose": r["purpose"],
                        "status": r["status"],
                        "created_at": str(r["created_at"]),
                    }
                    for r in rows
                ],
            }


# =============================================================================
# Tool 11: submit_equipment_request
# =============================================================================
def submit_equipment_request_handler(
    employee_number: str,
    equipment_type: str,
    business_justification: str,
    specifications: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    eq_type = (equipment_type or "").strip().lower()
    if eq_type not in VALID_EQUIPMENT_TYPES:
        eq_type = "other"

    just = (business_justification or "").strip()
    if not just:
        raise ValueError("business_justification is required for equipment request.")

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"success": False, "error": f"Employee {emp_no} not found."}

        cnt = conn.execute(text("SELECT COUNT(*) AS cnt FROM equipment_requests")).mappings().first()["cnt"]
        req_number = f"EQ-2026-{int(cnt) + 1:04d}"

        ins = text(
            """
            INSERT INTO equipment_requests (
                id, request_number, employee_id, equipment_type, specifications,
                business_justification, status, created_at, updated_at
            ) VALUES (
                :id, :req_no, :emp_id, :eq_type, :specs,
                :just, 'submitted', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            ins,
            {
                "id": str(uuid.uuid4()),
                "req_no": req_number,
                "emp_id": emp_id,
                "eq_type": eq_type,
                "specs": specifications or "",
                "just": just,
            },
        )
        conn.commit()

    return {
        "success": True,
        "request_number": req_number,
        "status": "submitted",
        "equipment_type": eq_type,
        "message": f"Equipment request {req_number} submitted successfully. Availability and approval are subject to IT review.",
    }


# =============================================================================
# Tool 12: get_equipment_request_status
# =============================================================================
def get_equipment_request_status_handler(
    employee_number: str,
    request_number: Optional[str] = None,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"found": False, "message": f"Employee {emp_no} not found."}

        if request_number:
            stmt = text(
                """
                SELECT request_number, equipment_type, specifications,
                       business_justification, status, created_at
                FROM equipment_requests
                WHERE employee_id = :emp_id AND request_number = :req_no
                """
            )
            row = conn.execute(stmt, {"emp_id": emp_id, "req_no": request_number.strip()}).mappings().first()
            if not row:
                return {"found": False, "message": f"Equipment request '{request_number}' not found."}
            return {
                "found": True,
                "request": {
                    "request_number": row["request_number"],
                    "equipment_type": row["equipment_type"],
                    "specifications": row["specifications"],
                    "business_justification": row["business_justification"],
                    "status": row["status"],
                    "created_at": str(row["created_at"]),
                },
            }
        else:
            stmt = text(
                """
                SELECT request_number, equipment_type, business_justification, status, created_at
                FROM equipment_requests
                WHERE employee_id = :emp_id
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
            rows = conn.execute(stmt, {"emp_id": emp_id}).mappings().all()
            return {
                "found": True,
                "employee_number": emp_no,
                "requests": [
                    {
                        "request_number": r["request_number"],
                        "equipment_type": r["equipment_type"],
                        "business_justification": r["business_justification"],
                        "status": r["status"],
                        "created_at": str(r["created_at"]),
                    }
                    for r in rows
                ],
            }


# =============================================================================
# Tool 13: update_employee_contact
# =============================================================================
def update_employee_contact_handler(
    employee_number: str,
    field_name: str,
    new_value: str,
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    caller = authorize_employee_access(emp_no)

    field = (field_name or "").strip().lower()
    if field in PROTECTED_CONTACT_FIELDS or field not in PERMITTED_CONTACT_FIELDS:
        raise ValueError(
            f"Field '{field_name}' is protected and cannot be modified. "
            f"Permitted fields: {', '.join(sorted(PERMITTED_CONTACT_FIELDS))}."
        )

    val = (new_value or "").strip()
    if not val:
        raise ValueError("new_value must not be empty.")

    # Format validation
    if field in ("phone_number", "emergency_contact_phone"):
        cleaned = re.sub(r"[\s\-\(\)\.]", "", val)
        if not re.match(r"^\+?[0-9]{7,15}$", cleaned):
            raise ValueError(f"Invalid phone number format: '{val}'. Expected 7-15 digits.")
    elif field == "personal_email":
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", val):
            raise ValueError(f"Invalid email format: '{val}'.")

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"success": False, "error": f"Employee {emp_no} not found."}

        caller_id = _get_employee_id(conn, caller.employee_number) or emp_id

        # Get existing value
        curr_val = conn.execute(
            text(f"SELECT {field} FROM employees WHERE id = :emp_id"),
            {"emp_id": emp_id},
        ).mappings().first()[field]

        # Update field on employee table
        conn.execute(
            text(f"UPDATE employees SET {field} = :val, updated_at = CURRENT_TIMESTAMP WHERE id = :emp_id"),
            {"val": val, "emp_id": emp_id},
        )

        # Record audit log
        conn.execute(
            text(
                """
                INSERT INTO employee_contact_audit (
                    id, employee_id, field_name, old_value, new_value, changed_by, created_at
                ) VALUES (
                    :id, :emp_id, :field, :old_val, :new_val, :changed_by, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "emp_id": emp_id,
                "field": field,
                "old_val": str(curr_val) if curr_val else "",
                "new_val": val,
                "changed_by": caller_id,
            },
        )
        conn.commit()

    return {
        "success": True,
        "employee_number": emp_no,
        "field_name": field,
        "old_value": str(curr_val) if curr_val else None,
        "new_value": val,
        "message": f"Contact information '{field}' updated successfully.",
    }


# =============================================================================
# Tool 14: get_all_requests_status
# =============================================================================
def get_all_requests_status_handler(
    employee_number: str,
    category_filter: str = "all",
) -> Dict[str, Any]:
    emp_no = _validate_employee_number(employee_number)
    authorize_employee_access(emp_no)

    db = get_db_manager()
    with db.get_connection() as conn:
        emp_id = _get_employee_id(conn, emp_no)
        if not emp_id:
            return {"found": False, "message": f"Employee {emp_no} not found."}

        all_records: List[Dict[str, Any]] = []

        cat = (category_filter or "all").lower()

        # 1. Leave requests
        if cat in ("all", "leave"):
            l_rows = conn.execute(
                text(
                    """
                    SELECT request_number, leave_type, start_date, end_date, days_requested, status, created_at
                    FROM leave_requests WHERE employee_id = :emp_id ORDER BY created_at DESC LIMIT 5
                    """
                ),
                {"emp_id": emp_id},
            ).mappings().all()
            for r in l_rows:
                all_records.append({
                    "category": "leave",
                    "request_number": r["request_number"],
                    "title": f"{r['leave_type'].capitalize()} Leave ({r['start_date']} to {r['end_date']})",
                    "status": r["status"],
                    "created_at": str(r["created_at"]),
                })

        # 2. IT tickets
        if cat in ("all", "it", "tickets"):
            t_rows = conn.execute(
                text(
                    """
                    SELECT ticket_number, title, category, priority, status, created_at
                    FROM it_tickets WHERE employee_id = :emp_id ORDER BY created_at DESC LIMIT 5
                    """
                ),
                {"emp_id": emp_id},
            ).mappings().all()
            for r in t_rows:
                all_records.append({
                    "category": "it_ticket",
                    "request_number": r["ticket_number"],
                    "title": r["title"],
                    "status": r["status"],
                    "created_at": str(r["created_at"]),
                })

        # 3. Reimbursements
        if cat in ("all", "reimbursement", "expenses"):
            e_rows = conn.execute(
                text(
                    """
                    SELECT request_number, expense_category, amount, currency, status, created_at
                    FROM reimbursement_requests WHERE employee_id = :emp_id ORDER BY created_at DESC LIMIT 5
                    """
                ),
                {"emp_id": emp_id},
            ).mappings().all()
            for r in e_rows:
                all_records.append({
                    "category": "reimbursement",
                    "request_number": r["request_number"],
                    "title": f"{r['expense_category']} (${float(r['amount']):.2f})",
                    "status": r["status"],
                    "created_at": str(r["created_at"]),
                })

        # 4. HR service requests
        if cat in ("all", "hr"):
            h_rows = conn.execute(
                text(
                    """
                    SELECT request_number, service_category, purpose, status, created_at
                    FROM hr_service_requests WHERE employee_id = :emp_id ORDER BY created_at DESC LIMIT 5
                    """
                ),
                {"emp_id": emp_id},
            ).mappings().all()
            for r in h_rows:
                all_records.append({
                    "category": "hr_service",
                    "request_number": r["request_number"],
                    "title": r["service_category"].replace("_", " ").title(),
                    "status": r["status"],
                    "created_at": str(r["created_at"]),
                })

        # 5. Equipment requests
        if cat in ("all", "equipment"):
            eq_rows = conn.execute(
                text(
                    """
                    SELECT request_number, equipment_type, business_justification, status, created_at
                    FROM equipment_requests WHERE employee_id = :emp_id ORDER BY created_at DESC LIMIT 5
                    """
                ),
                {"emp_id": emp_id},
            ).mappings().all()
            for r in eq_rows:
                all_records.append({
                    "category": "equipment",
                    "request_number": r["request_number"],
                    "title": f"Equipment: {r['equipment_type']}",
                    "status": r["status"],
                    "created_at": str(r["created_at"]),
                })

    all_records.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "found": True,
        "employee_number": emp_no,
        "total_requests": len(all_records),
        "requests": all_records,
    }


# =============================================================================
# Register all transactional tools with FastMCP
# =============================================================================
def register_transactional_tools(mcp: FastMCP) -> None:
    """Registers all transactional and status tools with the FastMCP application."""

    @mcp.tool()
    def submit_leave_request(
        employee_number: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a new employee leave request with automatic balance and overlap validation."""
        return submit_leave_request_handler(employee_number, leave_type, start_date, end_date, reason)

    @mcp.tool()
    def cancel_leave_request(
        employee_number: str,
        request_number: str,
        cancellation_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancel a pending leave request owned by the employee."""
        return cancel_leave_request_handler(employee_number, request_number, cancellation_reason)

    @mcp.tool()
    def get_leave_request_status(
        employee_number: str,
        request_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve leave request status and details for an employee."""
        return get_leave_request_status_handler(employee_number, request_number)

    @mcp.tool()
    def create_it_ticket(
        employee_number: str,
        title: str,
        description: str,
        category: str,
        priority: str = "medium",
        asset_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new IT support ticket with validated category and priority."""
        return create_it_ticket_handler(employee_number, title, description, category, priority, asset_tag)

    @mcp.tool()
    def update_it_ticket(
        employee_number: str,
        ticket_number: str,
        update_text: str,
    ) -> Dict[str, Any]:
        """Add an update or additional detail to an existing open IT ticket."""
        return update_it_ticket_handler(employee_number, ticket_number, update_text)

    @mcp.tool()
    def get_it_ticket_status(
        employee_number: str,
        ticket_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve IT ticket status and historical updates for an employee."""
        return get_it_ticket_status_handler(employee_number, ticket_number)

    @mcp.tool()
    def submit_reimbursement_request(
        employee_number: str,
        expense_category: str,
        amount: float,
        purchase_date: str,
        description: str,
        vendor: Optional[str] = None,
        receipt_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit an expense reimbursement request with policy limit validation."""
        return submit_reimbursement_request_handler(
            employee_number, expense_category, amount, purchase_date, description, vendor, receipt_filename
        )

    @mcp.tool()
    def get_reimbursement_status(
        employee_number: str,
        request_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve reimbursement request status for an employee."""
        return get_reimbursement_status_handler(employee_number, request_number)

    @mcp.tool()
    def create_hr_service_request(
        employee_number: str,
        service_category: str,
        purpose: str,
        recipient_details: Optional[str] = None,
        additional_details: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an HR service request (employment verification, letters, certificate, etc.)."""
        return create_hr_service_request_handler(
            employee_number, service_category, purpose, recipient_details, additional_details
        )

    @mcp.tool()
    def get_hr_request_status(
        employee_number: str,
        request_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve HR service request status for an employee."""
        return get_hr_request_status_handler(employee_number, request_number)

    @mcp.tool()
    def submit_equipment_request(
        employee_number: str,
        equipment_type: str,
        business_justification: str,
        specifications: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit an equipment or hardware requisition request for IT review."""
        return submit_equipment_request_handler(
            employee_number, equipment_type, business_justification, specifications
        )

    @mcp.tool()
    def get_equipment_request_status(
        employee_number: str,
        request_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve equipment request status for an employee."""
        return get_equipment_request_status_handler(employee_number, request_number)

    @mcp.tool()
    def update_employee_contact(
        employee_number: str,
        field_name: str,
        new_value: str,
    ) -> Dict[str, Any]:
        """Update permitted employee contact information (phone, emergency contact, personal email)."""
        return update_employee_contact_handler(employee_number, field_name, new_value)

    @mcp.tool()
    def get_all_requests_status(
        employee_number: str,
        category_filter: str = "all",
    ) -> Dict[str, Any]:
        """Retrieve consolidated status of all employee requests across all categories."""
        return get_all_requests_status_handler(employee_number, category_filter)
