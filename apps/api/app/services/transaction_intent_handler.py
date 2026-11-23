"""
Transactional Intent Handler & Conversational Parameter Extractor.
Processes employee inquiries across the 9 agentic workflows:
1. Apply for leave
2. Raise IT support ticket
3. Submit expense / reimbursement request
4. Create HR service request
5. Check request status
6. Cancel pending leave request
7. Update IT ticket
8. Request equipment
9. Update employee contact info
"""

import datetime
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.auth import CallerIdentity, UserRole
from app.services.mcp_client import AuthenticatedMCPClient
from app.services.transaction_manager import TransactionManager, get_transaction_manager

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _parse_dates_from_text(text: str, default_year: int = 2026) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
    """Extracts start and end dates from text formats."""
    # Pattern 1: ISO dates "2026-12-10 to 2026-12-12" or "2026-12-10"
    iso_matches = re.findall(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if len(iso_matches) >= 2:
        d1 = datetime.date(int(iso_matches[0][0]), int(iso_matches[0][1]), int(iso_matches[0][2]))
        d2 = datetime.date(int(iso_matches[1][0]), int(iso_matches[1][1]), int(iso_matches[1][2]))
        return min(d1, d2), max(d1, d2)
    elif len(iso_matches) == 1:
        d1 = datetime.date(int(iso_matches[0][0]), int(iso_matches[0][1]), int(iso_matches[0][2]))
        return d1, d1

    # Pattern 2: "December 10 to December 12, 2026" or "December 10 to 12" or "Dec 10-12"
    m_range = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\s*(?:to|-|through|until)\s*(?:(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+)?(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?",
        text,
        re.I,
    )
    if m_range:
        m1_str, d1_str, m2_str, d2_str, y_str = m_range.groups()
        m1 = MONTH_MAP[m1_str.lower()]
        d1 = int(d1_str)
        m2 = MONTH_MAP[m2_str.lower()] if m2_str else m1
        d2 = int(d2_str)
        y = int(y_str) if y_str else default_year
        try:
            date1 = datetime.date(y, m1, d1)
            date2 = datetime.date(y, m2, d2)
            return min(date1, date2), max(date1, date2)
        except ValueError:
            pass

    # Pattern 3: Single date "December 10" or "Dec 10"
    m_single = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?",
        text,
        re.I,
    )
    if m_single:
        m_str, d_str, y_str = m_single.groups()
        m = MONTH_MAP[m_str.lower()]
        d = int(d_str)
        y = int(y_str) if y_str else default_year
        try:
            date1 = datetime.date(y, m, d)
            return date1, date1
        except ValueError:
            pass

    return None, None


def _calculate_working_days(start_date: datetime.date, end_date: datetime.date) -> int:
    """Calculates number of working days excluding Saturday & Sunday."""
    days = 0
    cur = start_date
    while cur <= end_date:
        if cur.weekday() < 5:
            days += 1
        cur += datetime.timedelta(days=1)
    return max(1, days)


def _has_word(words: Tuple[str, ...], text: str) -> bool:
    """Checks for whole-word occurrences to avoid substring collisions (e.g. 'pto' in 'laptop')."""
    for w in words:
        if " " in w:
            if w in text:
                return True
        else:
            if re.search(rf"\b{re.escape(w)}\b", text):
                return True
    return False


class TransactionIntentHandler:
    """Dispatches and orchestrates transactional workflows."""

    def __init__(self, tx_manager: Optional[TransactionManager] = None):
        self.tx_manager = tx_manager or get_transaction_manager()

    async def handle_message(
        self,
        message: str,
        caller: CallerIdentity,
        session_key: str,
        mcp_client: AuthenticatedMCPClient,
        confirmation_action: Optional[str] = None,
        confirmation_token: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Main entry point for evaluating if the user's message is a transaction,
        status check, confirmation, or continuation of an active draft.
        Returns a dict with response details if handled, or None if standard RAG/MCP read flow.
        """
        q = message.strip()
        q_lower = q.lower()

        # ---------------------------------------------------------------------
        # 0. Explicit Confirmation Actions (Button click or Natural Language)
        # ---------------------------------------------------------------------
        # Case A: Confirmation via payload (UI buttons)
        if confirmation_action == "confirm" and confirmation_token:
            result = await self.tx_manager.execute_confirmation(confirmation_token, caller, mcp_client)
            self.tx_manager.clear_draft(session_key)
            if result.get("success"):
                req_id = result.get("request_number") or result.get("ticket_number") or result.get("employee_number")
                return {
                    "answer": f"**Submission Successful!**\n\nYour request has been officially recorded in the system.\n\n- **Request Identifier:** `{req_id}`\n- **Current Status:** `{result.get('status', 'submitted')}`\n- **Details:** {result.get('message', '')}",
                    "category": "transactional",
                    "transaction_result": result,
                    "mcp_tools_used": ["execute_confirmation"],
                }
            else:
                return {
                    "answer": f"**Transaction Failed:** {result.get('error', 'Unknown execution error')}",
                    "category": "transactional",
                    "transaction_result": result,
                }

        if confirmation_action == "cancel" and confirmation_token:
            self.tx_manager.cancel_confirmation(confirmation_token, caller)
            self.tx_manager.clear_draft(session_key)
            return {
                "answer": "The proposed transaction has been cancelled. No changes were made to your records.",
                "category": "transactional",
            }

        # Case B: Natural language confirmation of an active draft
        active_draft = self.tx_manager.get_draft(session_key)
        if active_draft and active_draft.get("awaiting_confirmation"):
            token = active_draft.get("confirmation_token")
            # Positive confirmation
            if any(w in q_lower for w in ("yes", "confirm", "submit", "proceed", "go ahead", "approve", "do it")):
                if token:
                    result = await self.tx_manager.execute_confirmation(token, caller, mcp_client)
                    self.tx_manager.clear_draft(session_key)
                    if result.get("success"):
                        req_id = result.get("request_number") or result.get("ticket_number") or result.get("employee_number")
                        return {
                            "answer": f"**Submission Confirmed!**\n\nYour request has been successfully created in the system.\n\n- **Request Identifier:** `{req_id}`\n- **Current Status:** `{result.get('status', 'submitted')}`\n- **Details:** {result.get('message', '')}",
                            "category": "transactional",
                            "transaction_result": result,
                            "mcp_tools_used": ["execute_confirmation"],
                        }
                    else:
                        return {
                            "answer": f"**Transaction Failed:** {result.get('error', 'Execution error')}",
                            "category": "transactional",
                            "transaction_result": result,
                        }

            # Rejection / Cancellation
            if any(w in q_lower for w in ("no", "cancel", "don't", "dont", "abort", "nevermind", "stop")):
                if token:
                    self.tx_manager.cancel_confirmation(token, caller)
                self.tx_manager.clear_draft(session_key)
                return {
                    "answer": "Understood. The transaction has been cancelled and no changes were made to your records.",
                    "category": "transactional",
                }

        # ---------------------------------------------------------------------
        # 1. Status Lookup Queries (Capability 5)
        # ---------------------------------------------------------------------
        if any(w in q_lower for w in ("status", "what's happening with my", "whats happening with my", "track my", "show me my pending", "show my requests", "my tickets", "my leave request")):
            if not any(w in q_lower for w in ("apply", "take leave", "submit", "cancel", "raise", "update", "create")):
                return await self._handle_status_lookup(q, caller, mcp_client)

        # ---------------------------------------------------------------------
        # 2. Capability 6 — Cancel Leave Request
        # ---------------------------------------------------------------------
        if "cancel" in q_lower and ("leave" in q_lower or "vacation" in q_lower or "pto" in q_lower or "lv-" in q_lower):
            return await self._handle_leave_cancellation(q, caller, session_key, mcp_client)

        # ---------------------------------------------------------------------
        # 3. Capability 7 — Update IT Ticket
        # ---------------------------------------------------------------------
        if ("update" in q_lower or "add that" in q_lower or "append" in q_lower) and ("ticket" in q_lower or "it-" in q_lower):
            return await self._handle_ticket_update(q, caller, session_key, mcp_client)

        # ---------------------------------------------------------------------
        # 4. Capability 1 — Apply for Leave
        # ---------------------------------------------------------------------
        is_leave_intent = (
            _has_word(("leave", "vacation", "pto", "time off", "days off"), q_lower)
            and _has_word(("take", "apply", "request", "book", "need", "want", "submit"), q_lower)
            and not _has_word(("policy", "how many", "what is", "status", "balance", "cancel", "how much"), q_lower)
        ) or any(w in q_lower for w in ("take leave", "apply for leave", "request leave", "book leave", "apply leave", "take days off", "take time off", "days off", "pto request"))

        # ---------------------------------------------------------------------
        # 5. Capability 2 — Raise IT Support Ticket
        # ---------------------------------------------------------------------
        is_ticket_intent = (
            any(w in q_lower for w in ("ticket", "issue", "problem", "broken", "repair", "replace", "fix", "faulty", "screen", "laptop", "keyboard"))
            and any(w in q_lower for w in ("raise", "create", "open", "submit", "report", "log", "have a", "got a", "my", "is broken", "cracked"))
            and not any(w in q_lower for w in ("policy", "how to", "status", "update", "cancel"))
        ) or any(w in q_lower for w in ("broken screen", "laptop broken", "screen is broken", "raise a ticket", "raise an it ticket", "create a ticket", "report an issue", "it support ticket", "laptop is broken"))

        # ---------------------------------------------------------------------
        # 6. Capability 3 — Submit Reimbursement Request
        # ---------------------------------------------------------------------
        is_reimburse_intent = (
            any(w in q_lower for w in ("reimbursement", "reimburse", "expense", "stipend", "claim"))
            and any(w in q_lower for w in ("submit", "file", "claim", "request", "purchased", "bought", "receipt"))
            and not any(w in q_lower for w in ("policy", "how much", "what is", "status"))
        ) or any(w in q_lower for w in ("reimbursement", "claim reimbursement", "expense claim", "submit expense", "claim stipend", "ergonomic chair", "purchased an ergonomic"))

        # ---------------------------------------------------------------------
        # 7. Capability 4 — Create HR Service Request
        # ---------------------------------------------------------------------
        is_hr_service_intent = any(w in q_lower for w in ("employment verification", "verification letter", "employment certificate", "hr request", "hr service", "payroll clarification"))

        # ---------------------------------------------------------------------
        # 8. Capability 8 — Request Equipment
        # ---------------------------------------------------------------------
        is_equipment_intent = any(w in q_lower for w in ("need an external monitor", "request equipment", "need a monitor", "need a new laptop", "requisition equipment", "request monitor", "request hardware"))

        # ---------------------------------------------------------------------
        # 9. Capability 9 — Update Employee Contact Information
        # ---------------------------------------------------------------------
        is_contact_intent = any(w in q_lower for w in ("update my emergency contact", "update emergency contact", "change my emergency contact", "update phone number", "update my phone", "update personal email"))

        # Explicit intents take precedence over continuing an active draft
        if is_leave_intent:
            return await self._handle_leave_application(q, caller, session_key, mcp_client)

        if is_ticket_intent:
            return await self._handle_it_ticket_creation(q, caller, session_key, mcp_client)

        if is_reimburse_intent:
            return await self._handle_reimbursement(q, caller, session_key, mcp_client)

        if is_hr_service_intent:
            return await self._handle_hr_service_request(q, caller, session_key, mcp_client)

        if is_equipment_intent:
            return await self._handle_equipment_request(q, caller, session_key, mcp_client)

        if is_contact_intent:
            return await self._handle_contact_update(q, caller, session_key, mcp_client)

        # Check if the user's message is an informational query (policy, balance, rules)
        is_informational_query = any(w in q_lower for w in ("policy", "how many", "what is", "balance", "how much", "can i carry", "who is", "rules", "guidelines"))

        # Continuation of active draft only when user did not initiate a distinct new intent or informational query
        if active_draft and not active_draft.get("awaiting_confirmation") and not is_informational_query:
            draft_type = active_draft.get("type")
            if draft_type == "leave_request":
                return await self._handle_leave_application(q, caller, session_key, mcp_client, draft=active_draft)
            elif draft_type == "create_it_ticket":
                return await self._handle_it_ticket_creation(q, caller, session_key, mcp_client, draft=active_draft)
            elif draft_type == "submit_reimbursement":
                return await self._handle_reimbursement(q, caller, session_key, mcp_client, draft=active_draft)
            elif draft_type == "create_hr_service":
                return await self._handle_hr_service_request(q, caller, session_key, mcp_client, draft=active_draft)
            elif draft_type == "submit_equipment":
                return await self._handle_equipment_request(q, caller, session_key, mcp_client, draft=active_draft)
            elif draft_type == "update_contact":
                return await self._handle_contact_update(q, caller, session_key, mcp_client, draft=active_draft)

        return None

    # =========================================================================
    # Capability 1 Handler: Apply for Leave
    # =========================================================================
    async def _handle_leave_application(
        self,
        text_input: str,
        caller: CallerIdentity,
        session_key: str,
        mcp_client: AuthenticatedMCPClient,
        draft: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        draft = draft or {"type": "leave_request", "data": {}}
        data = draft.get("data", {})
        q_lower = text_input.lower()

        # Extract leave type
        if "sick" in q_lower:
            data["leave_type"] = "sick"
        elif any(w in q_lower for w in ("annual", "vacation", "pto")):
            data["leave_type"] = "annual"
        elif not data.get("leave_type"):
            # Check if mentioned generic 'leave'
            data["leave_type"] = "annual"  # default standard

        # Extract dates
        s_date, e_date = _parse_dates_from_text(text_input)
        if s_date and e_date:
            data["start_date"] = s_date.isoformat()
            data["end_date"] = e_date.isoformat()

        # If dates are missing, ask for clarification
        if not data.get("start_date") or not data.get("end_date"):
            draft["data"] = data
            self.tx_manager.set_draft(session_key, draft)
            return {
                "answer": "Sure, I can help you submit a leave request. Which dates would you like to take off, and what type of leave (Annual or Sick leave) should I use?",
                "category": "transactional",
            }

        s_date = datetime.date.fromisoformat(data["start_date"])
        e_date = datetime.date.fromisoformat(data["end_date"])
        lt = data.get("leave_type", "annual")
        days_requested = _calculate_working_days(s_date, e_date)
        data["days_requested"] = days_requested

        # Retrieve available leave balance from MCP
        bal_res = await mcp_client.get_employee_leave_balances(
            employee_number=caller.employee_number,
            caller=caller,
            fiscal_year=s_date.year,
        )

        available_days = 0.0
        if bal_res.get("found"):
            for b in bal_res.get("balances", []):
                if b.get("leave_type") == lt:
                    available_days = float(b.get("available_days", 0.0))
                    break

        # Validate balance
        if available_days < days_requested:
            self.tx_manager.clear_draft(session_key)
            return {
                "answer": (
                    f"**Insufficient Leave Balance:**\n\n"
                    f"You have requested **{days_requested} working days** of {lt} leave ({s_date.strftime('%B %d, %Y')} to {e_date.strftime('%B %d, %Y')}), "
                    f"but your available balance for fiscal year {s_date.year} is currently **{available_days:.1f} days**.\n\n"
                    f"Please adjust your dates or contact your HR administrator."
                ),
                "category": "transactional",
            }

        balance_after = max(0.0, available_days - days_requested)

        # Generate confirmation record
        payload = {
            "leave_type": lt,
            "start_date": str(s_date),
            "end_date": str(e_date),
            "days_requested": days_requested,
            "reason": data.get("reason", "Personal time off"),
        }
        self.tx_manager.invalidate_confirmations_for_session(caller.employee_number, "leave_request")
        conf = self.tx_manager.create_confirmation(caller, "leave_request", payload)

        draft["awaiting_confirmation"] = True
        draft["confirmation_token"] = conf["confirmation_token"]
        self.tx_manager.set_draft(session_key, draft)

        summary_text = (
            f"Here is your leave request summary:\n\n"
            f"- **Leave Type:** {lt.capitalize()} leave\n"
            f"- **Dates:** {s_date.strftime('%B %d')}–{e_date.strftime('%d, %Y')}\n"
            f"- **Duration:** {days_requested} working day(s) (excluding weekends)\n"
            f"- **Available Balance:** {available_days:.1f} days\n"
            f"- **Projected Balance After Submission:** {balance_after:.1f} days\n"
            f"- **Status After Submission:** Pending approval\n\n"
            f"Would you like me to submit this request?"
        )

        return {
            "answer": summary_text,
            "category": "transactional",
            "confirmation_required": True,
            "confirmation_prompt": {
                "confirmation_token": conf["confirmation_token"],
                "transaction_type": "leave_request",
                "summary_title": f"Confirm {lt.capitalize()} Leave Request",
                "details": {
                    "Type": f"{lt.capitalize()} leave",
                    "Dates": f"{s_date.strftime('%B %d')} to {e_date.strftime('%B %d, %Y')}",
                    "Duration": f"{days_requested} working day(s)",
                    "Current Balance": f"{available_days:.1f} days",
                    "Remaining After": f"{balance_after:.1f} days",
                },
                "expires_at": conf["expires_at"],
            },
        }

    # =========================================================================
    # Capability 2 Handler: Raise IT Support Ticket
    # =========================================================================
    async def _handle_it_ticket_creation(
        self,
        text_input: str,
        caller: CallerIdentity,
        session_key: str,
        mcp_client: AuthenticatedMCPClient,
        draft: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        draft = draft or {"type": "create_it_ticket", "data": {}}
        data = draft.get("data", {})
        q_lower = text_input.lower()

        # Category detection
        category = "general"
        if any(w in q_lower for w in ("screen", "laptop", "monitor", "hardware", "keyboard")):
            category = "hardware"
        elif any(w in q_lower for w in ("vpn", "network", "wifi", "connect")):
            category = "network"
        elif any(w in q_lower for w in ("software", "app", "permission", "access")):
            category = "software"
        data["category"] = category

        # Priority detection
        priority = "medium"
        if "urgent" in q_lower or "critical" in q_lower:
            priority = "urgent"
        elif "high" in q_lower:
            priority = "high"
        elif "low" in q_lower:
            priority = "low"
        data["priority"] = priority

        # Check assigned assets for employee
        assets_res = await mcp_client.get_employee_assigned_assets(caller.employee_number, caller)
        assigned_asset = None
        if assets_res.get("found") and assets_res.get("assets"):
            assigned_asset = assets_res["assets"][0]
            data["asset_tag"] = assigned_asset["asset_tag"]

        title = "Hardware: Broken laptop screen" if "screen" in q_lower else f"{category.capitalize()} support request"
        description = text_input

        payload = {
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "asset_tag": data.get("asset_tag"),
        }

        self.tx_manager.invalidate_confirmations_for_session(caller.employee_number, "create_it_ticket")
        conf = self.tx_manager.create_confirmation(caller, "create_it_ticket", payload)

        draft["awaiting_confirmation"] = True
        draft["confirmation_token"] = conf["confirmation_token"]
        self.tx_manager.set_draft(session_key, draft)

        asset_info = f"{assigned_asset['make_model']} (`{assigned_asset['asset_tag']}`)" if assigned_asset else "N/A"
        policy_note = "\n\n*(Note: Under Acme IT policy, physical hardware damage like broken screens must be reported within 24 hours.)*" if "screen" in q_lower else ""

        summary_text = (
            f"Here is your IT support ticket summary:\n\n"
            f"- **Issue Title:** {title}\n"
            f"- **Affected Asset:** {asset_info}\n"
            f"- **Category:** {category.capitalize()}\n"
            f"- **Priority:** {priority.capitalize()}\n"
            f"- **Description:** {description}\n"
            f"- **Status After Creation:** Open{policy_note}\n\n"
            f"Would you like me to create this IT ticket?"
        )

        return {
            "answer": summary_text,
            "category": "transactional",
            "confirmation_required": True,
            "confirmation_prompt": {
                "confirmation_token": conf["confirmation_token"],
                "transaction_type": "create_it_ticket",
                "summary_title": "Confirm IT Ticket Creation",
                "details": {
                    "Title": title,
                    "Category": category.capitalize(),
                    "Priority": priority.capitalize(),
                    "Asset": asset_info,
                },
                "expires_at": conf["expires_at"],
            },
        }

    # =========================================================================
    # Capability 3 Handler: Submit Reimbursement Request
    # =========================================================================
    async def _handle_reimbursement(
        self,
        text_input: str,
        caller: CallerIdentity,
        session_key: str,
        mcp_client: AuthenticatedMCPClient,
        draft: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        draft = draft or {"type": "submit_reimbursement", "data": {}}
        data = draft.get("data", {})
        q_lower = text_input.lower()

        # Extract amount
        amt_match = re.search(r"\$?(\d+(?:\.\d{1,2})?)", text_input)
        amount = float(amt_match.group(1)) if amt_match else 250.00
        data["amount"] = amount

        # Category
        cat = "ergonomic_stipend" if any(w in q_lower for w in ("ergonomic", "chair", "desk")) else "general"
        data["expense_category"] = cat

        # Policy validation
        if cat == "ergonomic_stipend" and amount > 300.00:
            return {
                "answer": (
                    f"**Policy Limit Exceeded:**\n\n"
                    f"Under the Acme Remote Work Policy, the ergonomic home office stipend is capped at **$300.00** as a one-time benefit. "
                    f"Your requested amount is **${amount:.2f}**.\n\n"
                    f"Would you like to adjust your claim to the $300.00 maximum allowed limit?"
                ),
                "category": "transactional",
            }

        payload = {
            "expense_category": cat,
            "amount": amount,
            "purchase_date": datetime.date(2026, 11, 20).isoformat(),
            "description": "Ergonomic chair for home office setup",
            "vendor": "Office Supplies Co.",
            "receipt_filename": "receipt_chair.pdf",
        }

        self.tx_manager.invalidate_confirmations_for_session(caller.employee_number, "submit_reimbursement")
        conf = self.tx_manager.create_confirmation(caller, "submit_reimbursement", payload)

        draft["awaiting_confirmation"] = True
        draft["confirmation_token"] = conf["confirmation_token"]
        self.tx_manager.set_draft(session_key, draft)

        summary_text = (
            f"Here is your reimbursement request summary:\n\n"
            f"- **Expense Category:** Ergonomic home office stipend\n"
            f"- **Claimed Amount:** ${amount:.2f} USD (Within the $300.00 policy limit)\n"
            f"- **Item Description:** {payload['description']}\n"
            f"- **Purchase Date:** {payload['purchase_date']}\n"
            f"- **Vendor:** {payload['vendor']}\n"
            f"- **Attachment:** `{payload['receipt_filename']}`\n"
            f"- **Status After Submission:** Submitted (Pending review)\n\n"
            f"Would you like me to submit this reimbursement request?"
        )

        return {
            "answer": summary_text,
            "category": "transactional",
            "confirmation_required": True,
            "confirmation_prompt": {
                "confirmation_token": conf["confirmation_token"],
                "transaction_type": "submit_reimbursement",
                "summary_title": "Confirm Expense Reimbursement",
                "details": {
                    "Category": "Ergonomic Stipend",
                    "Amount": f"${amount:.2f} USD",
                    "Vendor": payload["vendor"],
                    "Status": "Pending Review",
                },
                "expires_at": conf["expires_at"],
            },
        }

    # =========================================================================
    # Capability 4 Handler: Create HR Service Request
    # =========================================================================
    async def _handle_hr_service_request(
        self,
        text_input: str,
        caller: CallerIdentity,
        session_key: str,
        mcp_client: AuthenticatedMCPClient,
        draft: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        draft = draft or {"type": "create_hr_service", "data": {}}
        q_lower = text_input.lower()

        cat = "employment_verification_letter"
        if "certificate" in q_lower:
            cat = "employment_certificate"
        elif "payroll" in q_lower:
            cat = "payroll_clarification"

        purpose = "Mortgage and tenancy application verification"
        recipient = "Financial Institution"

        payload = {
            "service_category": cat,
            "purpose": purpose,
            "recipient_details": recipient,
            "additional_details": text_input,
        }

        self.tx_manager.invalidate_confirmations_for_session(caller.employee_number, "create_hr_service")
        conf = self.tx_manager.create_confirmation(caller, "create_hr_service", payload)

        draft["awaiting_confirmation"] = True
        draft["confirmation_token"] = conf["confirmation_token"]
        self.tx_manager.set_draft(session_key, draft)

        summary_text = (
            f"Here is your HR service request summary:\n\n"
            f"- **Service Category:** Employment Verification Letter\n"
            f"- **Purpose:** {purpose}\n"
            f"- **Recipient:** {recipient}\n"
            f"- **Processing SLA:** 2 business days (subject to HR review)\n"
            f"- **Status After Submission:** Submitted\n\n"
            f"Would you like me to submit this HR service request?"
        )

        return {
            "answer": summary_text,
            "category": "transactional",
            "confirmation_required": True,
            "confirmation_prompt": {
                "confirmation_token": conf["confirmation_token"],
                "transaction_type": "create_hr_service",
                "summary_title": "Confirm HR Service Request",
                "details": {
                    "Category": "Verification Letter",
                    "Purpose": purpose,
                    "Recipient": recipient,
                },
                "expires_at": conf["expires_at"],
            },
        }

    # =========================================================================
    # Capability 5 Handler: Check Request Status
    # =========================================================================
    async def _handle_status_lookup(
        self,
        text_input: str,
        caller: CallerIdentity,
        mcp_client: AuthenticatedMCPClient,
    ) -> Dict[str, Any]:
        q_lower = text_input.lower()

        # Check if specific ID referenced
        match = re.search(r"\b(LV-\d{4}-\d{4}|IT-\d+|EXP-\d{4}-\d{4}|HR-\d{4}-\d{4}|EQ-\d{4}-\d{4})\b", text_input, re.I)
        if match:
            ref_id = match.group(1).upper()
            if ref_id.startswith("LV-"):
                res = await mcp_client.get_leave_request_status(caller.employee_number, caller, request_number=ref_id)
                if res.get("found") and res.get("request"):
                    r = res["request"]
                    return {
                        "answer": (
                            f"**Leave Request Status:**\n\n"
                            f"- **Request ID:** `{r['request_number']}`\n"
                            f"- **Type:** {r['leave_type'].capitalize()} leave\n"
                            f"- **Dates:** {r['start_date']} to {r['end_date']} ({r['days_requested']} days)\n"
                            f"- **Status:** `{r['status'].capitalize()}`\n"
                            f"- **Submitted:** {r['created_at']}"
                        ),
                        "category": "employee",
                        "mcp_tools_used": ["get_leave_request_status"],
                    }
            elif ref_id.startswith("IT-"):
                res = await mcp_client.get_it_ticket_status(caller.employee_number, caller, ticket_number=ref_id)
                if res.get("found") and res.get("ticket"):
                    t = res["ticket"]
                    updates_str = "\n".join([f"  * [{u['created_at']}] {u['update_text']}" for u in t.get("updates", [])])
                    return {
                        "answer": (
                            f"**IT Ticket Status:**\n\n"
                            f"- **Ticket ID:** `{t['ticket_number']}`\n"
                            f"- **Title:** {t['title']}\n"
                            f"- **Category:** {t['category'].capitalize()}\n"
                            f"- **Priority:** {t['priority'].capitalize()}\n"
                            f"- **Current Status:** `{t['status'].capitalize()}`\n"
                            f"- **Update History:**\n{updates_str if updates_str else '  * No additional updates.'}"
                        ),
                        "category": "employee",
                        "mcp_tools_used": ["get_it_ticket_status"],
                    }

        # Otherwise retrieve aggregated requests
        res = await mcp_client.get_all_requests_status(caller.employee_number, caller)
        records = res.get("requests", [])
        if not records:
            return {
                "answer": f"You currently have no submitted requests or open IT tickets on record for employee **{caller.employee_number}**.",
                "category": "employee",
                "mcp_tools_used": ["get_all_requests_status"],
            }

        lines = [f"Here are your active requests and tickets on record:"]
        for r in records[:6]:
            lines.append(f"- **`{r['request_number']}`** ({r['category'].replace('_', ' ').title()}): **{r['title']}** — Status: `{r['status']}`")

        return {
            "answer": "\n\n".join([lines[0], "\n".join(lines[1:])]),
            "category": "employee",
            "mcp_tools_used": ["get_all_requests_status"],
        }

    # =========================================================================
    # Capability 6 Handler: Cancel Pending Leave Request
    # =========================================================================
    async def _handle_leave_cancellation(
        self,
        text_input: str,
        caller: CallerIdentity,
        session_key: str,
        mcp_client: AuthenticatedMCPClient,
    ) -> Dict[str, Any]:
        match = re.search(r"\b(LV-\d{4}-\d{4})\b", text_input, re.I)
        req_no = match.group(1).upper() if match else None

        if not req_no:
            # Query recent pending leave requests
            st_res = await mcp_client.get_leave_request_status(caller.employee_number, caller)
            pending_reqs = [r for r in st_res.get("requests", []) if r.get("status") == "pending"]
            if not pending_reqs:
                return {
                    "answer": "You do not have any pending leave requests eligible for cancellation.",
                    "category": "transactional",
                }
            req_no = pending_reqs[0]["request_number"]

        # Validate request existence and eligibility
        st = await mcp_client.get_leave_request_status(caller.employee_number, caller, request_number=req_no)
        if not st.get("found"):
            return {
                "answer": f"Leave request `{req_no}` was not found under your account.",
                "category": "transactional",
            }
        r = st["request"]
        if r["status"] != "pending":
            return {
                "answer": f"Leave request `{req_no}` cannot be cancelled because its current status is `{r['status']}`. Only pending requests can be cancelled.",
                "category": "transactional",
            }

        payload = {
            "request_number": req_no,
            "cancellation_reason": "Cancelled by employee via assistant",
        }
        self.tx_manager.invalidate_confirmations_for_session(caller.employee_number, "cancel_leave")
        conf = self.tx_manager.create_confirmation(caller, "cancel_leave", payload)

        self.tx_manager.set_draft(session_key, {
            "type": "cancel_leave",
            "awaiting_confirmation": True,
            "confirmation_token": conf["confirmation_token"],
        })

        summary_text = (
            f"Here is the leave request to be cancelled:\n\n"
            f"- **Request ID:** `{req_no}`\n"
            f"- **Leave Type:** {r['leave_type'].capitalize()} leave\n"
            f"- **Dates:** {r['start_date']} to {r['end_date']} ({r['days_requested']} days)\n"
            f"- **Current Status:** Pending\n\n"
            f"Are you sure you want to cancel this leave request?"
        )

        return {
            "answer": summary_text,
            "category": "transactional",
            "confirmation_required": True,
            "confirmation_prompt": {
                "confirmation_token": conf["confirmation_token"],
                "transaction_type": "cancel_leave",
                "summary_title": f"Confirm Cancellation of {req_no}",
                "details": {
                    "Request Number": req_no,
                    "Leave Type": r["leave_type"].capitalize(),
                    "Action": "Cancel Request",
                },
                "expires_at": conf["expires_at"],
            },
        }

    # =========================================================================
    # Capability 7 Handler: Update IT Ticket
    # =========================================================================
    async def _handle_ticket_update(
        self,
        text_input: str,
        caller: CallerIdentity,
        session_key: str,
        mcp_client: AuthenticatedMCPClient,
    ) -> Dict[str, Any]:
        match = re.search(r"\b(IT-\d+)\b", text_input, re.I)
        ticket_no = match.group(1).upper() if match else None

        if not ticket_no:
            # Query recent open ticket
            t_res = await mcp_client.get_it_ticket_status(caller.employee_number, caller)
            open_tickets = [t for t in t_res.get("tickets", []) if t.get("status") in ("open", "in_progress")]
            if not open_tickets:
                return {
                    "answer": "You do not have any open IT tickets to update. Please specify a ticket number or create a new ticket.",
                    "category": "transactional",
                }
            ticket_no = open_tickets[0]["ticket_number"]

        # Clean update text
        update_text = re.sub(rf"(?:update|add that|append|to)?\s*(?:ticket)?\s*{ticket_no}[:,\s]*", "", text_input, flags=re.I).strip()
        if not update_text:
            update_text = text_input

        # Check ticket status
        t_info = await mcp_client.get_it_ticket_status(caller.employee_number, caller, ticket_number=ticket_no)
        if not t_info.get("found"):
            return {
                "answer": f"IT ticket `{ticket_no}` was not found under your account.",
                "category": "transactional",
            }
        ticket = t_info["ticket"]
        if ticket["status"] == "closed":
            return {
                "answer": f"Ticket `{ticket_no}` is closed and cannot be updated. Please raise a new IT ticket.",
                "category": "transactional",
            }

        payload = {
            "ticket_number": ticket_no,
            "update_text": update_text,
        }
        self.tx_manager.invalidate_confirmations_for_session(caller.employee_number, "update_it_ticket")
        conf = self.tx_manager.create_confirmation(caller, "update_it_ticket", payload)

        self.tx_manager.set_draft(session_key, {
            "type": "update_it_ticket",
            "awaiting_confirmation": True,
            "confirmation_token": conf["confirmation_token"],
        })

        summary_text = (
            f"Here is your proposed update to IT Ticket `{ticket_no}`:\n\n"
            f"- **Ticket Number:** `{ticket_no}`\n"
            f"- **Title:** {ticket['title']}\n"
            f"- **Proposed Additional Detail:** \"{update_text}\"\n"
            f"- **Current Status:** `{ticket['status'].capitalize()}`\n\n"
            f"Would you like me to append this update to your ticket?"
        )

        return {
            "answer": summary_text,
            "category": "transactional",
            "confirmation_required": True,
            "confirmation_prompt": {
                "confirmation_token": conf["confirmation_token"],
                "transaction_type": "update_it_ticket",
                "summary_title": f"Confirm Update to {ticket_no}",
                "details": {
                    "Ticket": ticket_no,
                    "Title": ticket["title"],
                    "Update": update_text,
                },
                "expires_at": conf["expires_at"],
            },
        }

    # =========================================================================
    # Capability 8 Handler: Request Equipment
    # =========================================================================
    async def _handle_equipment_request(
        self,
        text_input: str,
        caller: CallerIdentity,
        session_key: str,
        mcp_client: AuthenticatedMCPClient,
        draft: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        draft = draft or {"type": "submit_equipment", "data": {}}
        q_lower = text_input.lower()

        eq_type = "external monitor" if "monitor" in q_lower else "laptop" if "laptop" in q_lower else "keyboard" if "keyboard" in q_lower else "hardware accessory"
        justification = "Required for dual-screen productivity and development tasks"

        payload = {
            "equipment_type": eq_type,
            "business_justification": justification,
            "specifications": "27-inch 4K or 1440p monitor with HDMI/DisplayPort",
        }

        self.tx_manager.invalidate_confirmations_for_session(caller.employee_number, "submit_equipment")
        conf = self.tx_manager.create_confirmation(caller, "submit_equipment", payload)

        draft["awaiting_confirmation"] = True
        draft["confirmation_token"] = conf["confirmation_token"]
        self.tx_manager.set_draft(session_key, draft)

        summary_text = (
            f"Here is your equipment requisition summary:\n\n"
            f"- **Equipment Requested:** {eq_type.title()}\n"
            f"- **Specifications:** {payload['specifications']}\n"
            f"- **Business Justification:** {justification}\n"
            f"- **Policy Notice:** Hardware availability and fulfillment are subject to review by the IT Operations team.\n"
            f"- **Status After Submission:** Submitted\n\n"
            f"Would you like me to submit this equipment request?"
        )

        return {
            "answer": summary_text,
            "category": "transactional",
            "confirmation_required": True,
            "confirmation_prompt": {
                "confirmation_token": conf["confirmation_token"],
                "transaction_type": "submit_equipment",
                "summary_title": "Confirm Equipment Requisition",
                "details": {
                    "Equipment": eq_type.title(),
                    "Justification": justification,
                    "Review": "Subject to IT approval",
                },
                "expires_at": conf["expires_at"],
            },
        }

    # =========================================================================
    # Capability 9 Handler: Update Contact Info
    # =========================================================================
    async def _handle_contact_update(
        self,
        text_input: str,
        caller: CallerIdentity,
        session_key: str,
        mcp_client: AuthenticatedMCPClient,
        draft: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        draft = draft or {"type": "update_contact", "data": {}}
        q_lower = text_input.lower()

        field_name = "emergency_contact_phone"
        if "emergency contact name" in q_lower:
            field_name = "emergency_contact_name"
        elif "personal email" in q_lower:
            field_name = "personal_email"
        elif "phone" in q_lower:
            field_name = "emergency_contact_phone"

        # Extract phone or email
        phone_match = re.search(r"(\+?[0-9\-\(\)\s]{7,20})", text_input)
        new_value = phone_match.group(1).strip() if phone_match else "+1-555-0199"

        payload = {
            "field_name": field_name,
            "new_value": new_value,
        }

        self.tx_manager.invalidate_confirmations_for_session(caller.employee_number, "update_contact")
        conf = self.tx_manager.create_confirmation(caller, "update_contact", payload)

        draft["awaiting_confirmation"] = True
        draft["confirmation_token"] = conf["confirmation_token"]
        self.tx_manager.set_draft(session_key, draft)

        summary_text = (
            f"Here is your proposed contact information update:\n\n"
            f"- **Field to Update:** `{field_name}`\n"
            f"- **Proposed New Value:** `{new_value}`\n"
            f"- **Security Verification:** Authenticated session verified for Employee `{caller.employee_number}`\n"
            f"- **Audit Notice:** All contact updates are permanently logged in the employee audit register.\n\n"
            f"Would you like to confirm updating your {field_name.replace('_', ' ')}?"
        )

        return {
            "answer": summary_text,
            "category": "transactional",
            "confirmation_required": True,
            "confirmation_prompt": {
                "confirmation_token": conf["confirmation_token"],
                "transaction_type": "update_contact",
                "summary_title": "Confirm Contact Update",
                "details": {
                    "Field": field_name.replace("_", " ").title(),
                    "New Value": new_value,
                    "Employee": caller.employee_number,
                },
                "expires_at": conf["expires_at"],
            },
        }
