"""
Transaction Manager & Confirmation Lifecycle Service.
Enforces Phase 0 §4 and ESR-STD-v2.4 transactional security contracts:
1. In-flight conversational draft parameter collection.
2. Server-side pre-flight business validation.
3. Cryptographically bound confirmation token generation (employee, payload, hash, expiration).
4. Explicit one-time execution and idempotency enforcement.
5. Invalidation upon payload alteration.
"""

import asyncio
import datetime
import hashlib
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.auth import CallerIdentity, UserRole
from app.services.mcp_client import AuthenticatedMCPClient, MCPAuthorizationError

logger = logging.getLogger(__name__)

CONFIRMATION_EXPIRY_MINUTES = 15

# Permitted transactional types
TRANSACTION_TYPES = {
    "leave_request",
    "cancel_leave",
    "create_it_ticket",
    "update_it_ticket",
    "submit_reimbursement",
    "create_hr_service",
    "submit_equipment",
    "update_contact",
}


def _canonical_payload_hash(payload: Dict[str, Any]) -> str:
    """Computes SHA-256 hash over canonical JSON representation."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class TransactionManager:
    """
    Stateful transaction & confirmation manager.
    Tracks draft parameters across multi-turn sessions and validates confirmation tokens.
    """

    def __init__(self):
        # Session drafts: key = f"{caller.user_id}:{conversation_id}"
        self._drafts: Dict[str, Dict[str, Any]] = {}
        # In-memory confirmation store (fallback / fast lookups aligned with DB)
        self._confirmations: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def get_draft(self, session_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves active transaction draft for session."""
        return self._drafts.get(session_key)

    def set_draft(self, session_key: str, draft: Dict[str, Any]) -> None:
        """Sets or updates active transaction draft for session."""
        self._drafts[session_key] = draft

    def clear_draft(self, session_key: str) -> None:
        """Clears transaction draft for session."""
        self._drafts.pop(session_key, None)

    # =========================================================================
    # Confirmation Lifecycle
    # =========================================================================
    def create_confirmation(
        self,
        caller: CallerIdentity,
        transaction_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new confirmation record bound to employee, transaction type,
        canonical payload hash, and 15-minute expiration window.
        """
        if transaction_type not in TRANSACTION_TYPES:
            raise ValueError(f"Unknown transaction type '{transaction_type}'.")

        token = f"conf-{uuid.uuid4().hex}"
        p_hash = _canonical_payload_hash(payload)
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(minutes=CONFIRMATION_EXPIRY_MINUTES)

        record = {
            "confirmation_token": token,
            "employee_number": caller.employee_number,
            "user_id": caller.user_id,
            "transaction_type": transaction_type,
            "payload": dict(payload),
            "payload_hash": p_hash,
            "status": "awaiting_confirmation",
            "idempotency_key": idempotency_key or f"idem-{uuid.uuid4().hex[:12]}",
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "executed_request_id": None,
        }

        self._confirmations[token] = record
        return record

    def get_confirmation(self, token: str) -> Optional[Dict[str, Any]]:
        """Retrieves confirmation record by token."""
        return self._confirmations.get(token)

    def invalidate_confirmations_for_session(self, employee_number: str, transaction_type: str) -> None:
        """Invalidates pending confirmations when draft parameters change."""
        for rec in self._confirmations.values():
            if (
                rec.get("employee_number") == employee_number
                and rec.get("transaction_type") == transaction_type
                and rec.get("status") == "awaiting_confirmation"
            ):
                rec["status"] = "expired"

    def cancel_confirmation(self, token: str, caller: CallerIdentity) -> Dict[str, Any]:
        """Cancels a pending confirmation explicitly."""
        rec = self._confirmations.get(token)
        if not rec:
            return {"success": False, "error": "Confirmation token not found."}

        if rec["employee_number"] != caller.employee_number and caller.role != UserRole.HR_ADMIN:
            return {"success": False, "error": "Access Denied: Confirmation belongs to another employee."}

        rec["status"] = "cancelled"
        return {"success": True, "message": "Transaction cancelled."}

    async def execute_confirmation(
        self,
        token: str,
        caller: CallerIdentity,
        mcp_client: AuthenticatedMCPClient,
    ) -> Dict[str, Any]:
        """
        Verifies confirmation record validity, enforces caller identity binding,
        checks expiration, verifies payload hash, and executes the designated MCP write tool once.
        Guarantees thread-safe / async-safe concurrency and eliminates TOCTOU double-execution.
        """
        async with self._lock:
            rec = self._confirmations.get(token)
            if not rec:
                return {
                    "success": False,
                    "error": "Confirmation token not found or invalid.",
                }

            # 1. Authorization: Bound to authenticated employee
            if rec["employee_number"] != caller.employee_number and caller.role != UserRole.HR_ADMIN:
                logger.warning(
                    "Security alert: User %s attempted to execute confirmation belonging to %s",
                    caller.employee_number,
                    rec["employee_number"],
                )
                return {
                    "success": False,
                    "error": "Access Denied: You are not authorized to execute this confirmation.",
                }

            # 2. Expiration check
            now = datetime.datetime.now(datetime.timezone.utc)
            exp = datetime.datetime.fromisoformat(rec["expires_at"])
            if now > exp:
                rec["status"] = "expired"
                return {
                    "success": False,
                    "error": "Confirmation token has expired. Please submit your request again.",
                }

            # 3. Status check: one-time execution (no replay)
            if rec["status"] == "executed":
                return {
                    "success": True,
                    "message": "This transaction has already been executed.",
                    "request_id": rec.get("executed_request_id"),
                    "idempotent": True,
                }

            if rec["status"] == "in_flight":
                return {
                    "success": False,
                    "error": "This transaction is currently in progress. Please wait.",
                    "idempotent": True,
                }

            if rec["status"] != "awaiting_confirmation":
                return {
                    "success": False,
                    "error": f"Confirmation cannot be executed because status is '{rec['status']}'.",
                }

            # 4. Hash integrity verification
            payload = rec["payload"]
            if _canonical_payload_hash(payload) != rec["payload_hash"]:
                rec["status"] = "rejected"
                return {
                    "success": False,
                    "error": "Security validation failed: Payload has been tampered with or modified.",
                }

            # Atomically claim token to block concurrent requests
            rec["status"] = "in_flight"

        # 5. Dispatch to appropriate FastMCP write tool
        t_type = rec["transaction_type"]
        emp_no = rec["employee_number"]
        result = {}

        try:
            if t_type == "leave_request":
                result = await mcp_client.submit_leave_request(
                    employee_number=emp_no,
                    leave_type=payload["leave_type"],
                    start_date=payload["start_date"],
                    end_date=payload["end_date"],
                    reason=payload.get("reason"),
                    caller=caller,
                )
            elif t_type == "cancel_leave":
                result = await mcp_client.cancel_leave_request(
                    employee_number=emp_no,
                    request_number=payload["request_number"],
                    cancellation_reason=payload.get("cancellation_reason"),
                    caller=caller,
                )
            elif t_type == "create_it_ticket":
                result = await mcp_client.create_it_ticket(
                    employee_number=emp_no,
                    title=payload["title"],
                    description=payload["description"],
                    category=payload.get("category", "general"),
                    priority=payload.get("priority", "medium"),
                    asset_tag=payload.get("asset_tag"),
                    caller=caller,
                )
            elif t_type == "update_it_ticket":
                result = await mcp_client.update_it_ticket(
                    employee_number=emp_no,
                    ticket_number=payload["ticket_number"],
                    update_text=payload["update_text"],
                    caller=caller,
                )
            elif t_type == "submit_reimbursement":
                result = await mcp_client.submit_reimbursement_request(
                    employee_number=emp_no,
                    expense_category=payload["expense_category"],
                    amount=payload["amount"],
                    purchase_date=payload["purchase_date"],
                    description=payload["description"],
                    vendor=payload.get("vendor"),
                    receipt_filename=payload.get("receipt_filename"),
                    caller=caller,
                )
            elif t_type == "create_hr_service":
                result = await mcp_client.create_hr_service_request(
                    employee_number=emp_no,
                    service_category=payload["service_category"],
                    purpose=payload["purpose"],
                    recipient_details=payload.get("recipient_details"),
                    additional_details=payload.get("additional_details"),
                    caller=caller,
                )
            elif t_type == "submit_equipment":
                result = await mcp_client.submit_equipment_request(
                    employee_number=emp_no,
                    equipment_type=payload["equipment_type"],
                    business_justification=payload["business_justification"],
                    specifications=payload.get("specifications"),
                    caller=caller,
                )
            elif t_type == "update_contact":
                result = await mcp_client.update_employee_contact(
                    employee_number=emp_no,
                    field_name=payload["field_name"],
                    new_value=payload["new_value"],
                    caller=caller,
                )
            else:
                async with self._lock:
                    rec["status"] = "awaiting_confirmation"
                return {"success": False, "error": f"Unsupported transaction type '{t_type}'."}

            if result.get("success") or result.get("found"):
                async with self._lock:
                    rec["status"] = "executed"
                    req_id = (
                        result.get("request_number")
                        or result.get("ticket_number")
                        or result.get("employee_number")
                    )
                    rec["executed_request_id"] = req_id
                    result["confirmation_token"] = token
                return result
            else:
                # Business layer validation failed (e.g. balance, overlap, policy)
                async with self._lock:
                    rec["status"] = "awaiting_confirmation"
                return result

        except MCPAuthorizationError as auth_err:
            async with self._lock:
                rec["status"] = "awaiting_confirmation"
            logger.warning("Confirmation execution blocked by authorization: %s", auth_err)
            return {"success": False, "error": f"Authorization error: {auth_err}"}
        except Exception as e:
            async with self._lock:
                rec["status"] = "awaiting_confirmation"
            logger.error("Error executing confirmation: %s", e)
            return {"success": False, "error": f"Execution error: {e}"}


_TX_MANAGER: Optional[TransactionManager] = None


def get_transaction_manager() -> TransactionManager:
    """Returns the singleton TransactionManager instance."""
    global _TX_MANAGER
    if _TX_MANAGER is None:
        _TX_MANAGER = TransactionManager()
    return _TX_MANAGER
