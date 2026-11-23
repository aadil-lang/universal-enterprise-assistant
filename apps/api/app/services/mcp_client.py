"""
Authenticated Model Context Protocol (MCP) Client Service.
Enforces Phase 0 §4.2 and Phase 2.2B security contracts:
1. Derives authenticated caller identity from the current verified session.
2. Constructs canonical X-Internal-Identity JSON payload.
3. Computes HMAC-SHA256 signature using INTERNAL_MCP_SECRET.
4. Transmits signed headers with MCP requests over Streamable HTTP.
5. Injects fiscal year configuration when needed.
"""

import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Union

import httpx
from mcp.client.session import ClientSession
try:
    from mcp.client.streamable_http import streamable_http_client
except ImportError:
    from mcp.client.streamable_http import streamablehttp_client as streamable_http_client

from app.config.settings import get_settings
from app.core.auth import CallerIdentity, UserRole

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _open_streamable_http_client(endpoint: str, headers: Dict[str, str]):
    """Opens a streamable HTTP transport session compatible with both mcp 1.12 and 1.30+."""
    import inspect
    sig = inspect.signature(streamable_http_client)
    if "http_client" in sig.parameters:
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as http_client:
            async with streamable_http_client(endpoint, http_client=http_client) as streams:
                yield streams
    else:
        async with streamable_http_client(endpoint, headers=headers, timeout=10.0) as streams:
            yield streams


class MCPClientError(Exception):
    """Raised when an MCP protocol or tool invocation error occurs."""
    pass


class MCPAuthorizationError(MCPClientError):
    """Raised when an MCP tool invocation is rejected due to authorization boundaries."""
    pass


def create_internal_auth_headers(
    identity: Union[CallerIdentity, Dict[str, str]],
    secret: str,
) -> Dict[str, str]:
    """
    Constructs the approved internal identity headers matching Phase 2.2B contract:
    - X-Internal-Identity: Canonical JSON representation of CallerIdentity
    - X-Internal-Signature: Hex-encoded HMAC-SHA256 signature computed over X-Internal-Identity
    """
    if not secret or not secret.strip():
        raise ValueError("HMAC signing secret must be a non-empty string.")

    if isinstance(identity, CallerIdentity):
        identity_json = identity.model_dump_json()
    elif isinstance(identity, dict):
        identity_json = json.dumps(identity, separators=(",", ":"))
    else:
        raise TypeError("identity must be a CallerIdentity instance or a dictionary.")

    raw_bytes = identity_json.encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    return {
        "X-Internal-Identity": identity_json,
        "X-Internal-Signature": signature,
    }


class AuthenticatedMCPClient:
    """
    Client interface for calling internal FastMCP employee database tools
    using cryptographically signed internal identity headers.
    """

    def __init__(self, base_url: Optional[str] = None, secret: Optional[str] = None):
        self.settings = get_settings()
        self.base_url = base_url or self.settings.mcp_base_url
        self.secret = secret or self.settings.INTERNAL_MCP_SECRET
        self._in_process_handler = None

    def set_in_process_handler(self, handler_func):
        """Allows test suites to register an in-process tool dispatcher for fast offline testing."""
        self._in_process_handler = handler_func

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        caller: CallerIdentity,
    ) -> Dict[str, Any]:
        """
        Executes a typed tool call on the MCP server with signed identity headers.
        """
        # If an in-process handler is registered (e.g. during offline test execution):
        if self._in_process_handler is not None:
            return await self._in_process_handler(tool_name, arguments, caller)

        # Build authenticated headers
        auth_headers = create_internal_auth_headers(caller, secret=self.secret)
        mcp_endpoint = f"{self.base_url}/mcp"

        try:
            async with _open_streamable_http_client(mcp_endpoint, headers=auth_headers) as streams:
                read_stream, write_stream = streams[0], streams[1]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)

                    # Check for MCP protocol level errors
                    if getattr(result, "isError", False) or getattr(result, "is_error", False):
                        err_msg = result.content[0].text if result.content else "Unknown MCP tool error"
                        if "Forbidden" in err_msg or "Unauthorized" in err_msg:
                            raise MCPAuthorizationError(err_msg)
                        raise MCPClientError(f"Tool {tool_name} failed: {err_msg}")

                    if not result.content:
                        return {"found": False, "message": "No response returned from tool."}

                    text_payload = result.content[0].text
                    return json.loads(text_payload)
        except httpx.HTTPStatusError as http_err:
            if http_err.response.status_code == 401 or http_err.response.status_code == 403:
                raise MCPAuthorizationError(f"MCP server rejected request: {http_err.response.text}") from http_err
            raise MCPClientError(f"HTTP error communicating with MCP server: {http_err}") from http_err
        except (httpx.ConnectError, httpx.TimeoutException) as conn_err:
            logger.error("Failed to connect to MCP server at %s: %s", mcp_endpoint, conn_err)
            raise MCPClientError(f"MCP service unavailable at {mcp_endpoint}: {conn_err}") from conn_err
        except MCPAuthorizationError:
            raise
        except MCPClientError:
            raise
        except Exception as e:
            curr = e
            while hasattr(curr, "exceptions") and curr.exceptions:
                curr = curr.exceptions[0]
            if isinstance(curr, MCPAuthorizationError):
                raise curr from e
            logger.error("Unexpected error during MCP tool execution (%s): %s", tool_name, e)
            raise MCPClientError(f"Error calling MCP tool {tool_name}: {e}") from e

    async def get_employee_profile(
        self,
        employee_number: str,
        caller: CallerIdentity,
    ) -> Dict[str, Any]:
        """Retrieves employee demographic profile."""
        return await self.call_tool(
            "get_employee_profile",
            {"employee_number": str(employee_number).strip()},
            caller,
        )

    async def get_employee_leave_balances(
        self,
        employee_number: str,
        caller: CallerIdentity,
        fiscal_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieves employee leave balances (accrued, used, pending, available)."""
        args: Dict[str, Any] = {"employee_number": str(employee_number).strip()}
        if fiscal_year is not None:
            args["fiscal_year"] = int(fiscal_year)
        else:
            args["fiscal_year"] = self.settings.DEMO_FISCAL_YEAR

        return await self.call_tool("get_employee_leave_balances", args, caller)

    async def get_employee_assigned_assets(
        self,
        employee_number: str,
        caller: CallerIdentity,
    ) -> Dict[str, Any]:
        """Retrieves IT hardware assigned to an employee."""
        return await self.call_tool(
            "get_employee_assigned_assets",
            {"employee_number": str(employee_number).strip()},
            caller,
        )

    async def get_employee_it_tickets(
        self,
        employee_number: str,
        caller: CallerIdentity,
        status_filter: str = "all",
    ) -> Dict[str, Any]:
        """Retrieves IT support tickets for an employee."""
        return await self.call_tool(
            "get_employee_it_tickets",
            {
                "employee_number": str(employee_number).strip(),
                "status_filter": str(status_filter).strip().lower(),
            },
            caller,
        )

    async def submit_leave_request(
        self,
        employee_number: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        caller: CallerIdentity,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submits a verified leave request for the authenticated employee."""
        return await self.call_tool(
            "submit_leave_request",
            {
                "employee_number": str(employee_number).strip(),
                "leave_type": str(leave_type).strip().lower(),
                "start_date": str(start_date).strip(),
                "end_date": str(end_date).strip(),
                "reason": reason or "",
            },
            caller,
        )

    async def cancel_leave_request(
        self,
        employee_number: str,
        request_number: str,
        caller: CallerIdentity,
        cancellation_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancels a pending leave request owned by the employee."""
        return await self.call_tool(
            "cancel_leave_request",
            {
                "employee_number": str(employee_number).strip(),
                "request_number": str(request_number).strip(),
                "cancellation_reason": cancellation_reason or "",
            },
            caller,
        )

    async def get_leave_request_status(
        self,
        employee_number: str,
        caller: CallerIdentity,
        request_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves leave request status for an employee."""
        return await self.call_tool(
            "get_leave_request_status",
            {
                "employee_number": str(employee_number).strip(),
                "request_number": str(request_number).strip() if request_number else None,
            },
            caller,
        )

    async def create_it_ticket(
        self,
        employee_number: str,
        title: str,
        description: str,
        category: str,
        caller: CallerIdentity,
        priority: str = "medium",
        asset_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates an IT support ticket."""
        return await self.call_tool(
            "create_it_ticket",
            {
                "employee_number": str(employee_number).strip(),
                "title": str(title).strip(),
                "description": str(description).strip(),
                "category": str(category).strip().lower(),
                "priority": str(priority).strip().lower(),
                "asset_tag": str(asset_tag).strip() if asset_tag else None,
            },
            caller,
        )

    async def update_it_ticket(
        self,
        employee_number: str,
        ticket_number: str,
        update_text: str,
        caller: CallerIdentity,
    ) -> Dict[str, Any]:
        """Adds an update to an existing IT ticket."""
        return await self.call_tool(
            "update_it_ticket",
            {
                "employee_number": str(employee_number).strip(),
                "ticket_number": str(ticket_number).strip(),
                "update_text_val": str(update_text).strip(),
            },
            caller,
        )

    async def get_it_ticket_status(
        self,
        employee_number: str,
        caller: CallerIdentity,
        ticket_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves IT ticket status and history."""
        return await self.call_tool(
            "get_it_ticket_status",
            {
                "employee_number": str(employee_number).strip(),
                "ticket_number": str(ticket_number).strip() if ticket_number else None,
            },
            caller,
        )

    async def submit_reimbursement_request(
        self,
        employee_number: str,
        expense_category: str,
        amount: float,
        purchase_date: str,
        description: str,
        caller: CallerIdentity,
        vendor: Optional[str] = None,
        receipt_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submits an expense reimbursement request."""
        return await self.call_tool(
            "submit_reimbursement_request",
            {
                "employee_number": str(employee_number).strip(),
                "expense_category": str(expense_category).strip().lower(),
                "amount": float(amount),
                "purchase_date": str(purchase_date).strip(),
                "description": str(description).strip(),
                "vendor": str(vendor).strip() if vendor else None,
                "receipt_filename": str(receipt_filename).strip() if receipt_filename else None,
            },
            caller,
        )

    async def get_reimbursement_status(
        self,
        employee_number: str,
        caller: CallerIdentity,
        request_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves reimbursement status."""
        return await self.call_tool(
            "get_reimbursement_status",
            {
                "employee_number": str(employee_number).strip(),
                "request_number": str(request_number).strip() if request_number else None,
            },
            caller,
        )

    async def create_hr_service_request(
        self,
        employee_number: str,
        service_category: str,
        purpose: str,
        caller: CallerIdentity,
        recipient_details: Optional[str] = None,
        additional_details: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates an HR service request."""
        return await self.call_tool(
            "create_hr_service_request",
            {
                "employee_number": str(employee_number).strip(),
                "service_category": str(service_category).strip().lower(),
                "purpose": str(purpose).strip(),
                "recipient_details": str(recipient_details).strip() if recipient_details else None,
                "additional_details": str(additional_details).strip() if additional_details else None,
            },
            caller,
        )

    async def get_hr_request_status(
        self,
        employee_number: str,
        caller: CallerIdentity,
        request_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves HR request status."""
        return await self.call_tool(
            "get_hr_request_status",
            {
                "employee_number": str(employee_number).strip(),
                "request_number": str(request_number).strip() if request_number else None,
            },
            caller,
        )

    async def submit_equipment_request(
        self,
        employee_number: str,
        equipment_type: str,
        business_justification: str,
        caller: CallerIdentity,
        specifications: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submits an equipment requisition request."""
        return await self.call_tool(
            "submit_equipment_request",
            {
                "employee_number": str(employee_number).strip(),
                "equipment_type": str(equipment_type).strip().lower(),
                "business_justification": str(business_justification).strip(),
                "specifications": str(specifications).strip() if specifications else None,
            },
            caller,
        )

    async def get_equipment_request_status(
        self,
        employee_number: str,
        caller: CallerIdentity,
        request_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves equipment request status."""
        return await self.call_tool(
            "get_equipment_request_status",
            {
                "employee_number": str(employee_number).strip(),
                "request_number": str(request_number).strip() if request_number else None,
            },
            caller,
        )

    async def update_employee_contact(
        self,
        employee_number: str,
        field_name: str,
        new_value: str,
        caller: CallerIdentity,
    ) -> Dict[str, Any]:
        """Updates employee contact details (phone, emergency contact, personal email)."""
        return await self.call_tool(
            "update_employee_contact",
            {
                "employee_number": str(employee_number).strip(),
                "field_name": str(field_name).strip().lower(),
                "new_value": str(new_value).strip(),
            },
            caller,
        )

    async def get_all_requests_status(
        self,
        employee_number: str,
        caller: CallerIdentity,
        category_filter: str = "all",
    ) -> Dict[str, Any]:
        """Retrieves all requests for an employee."""
        return await self.call_tool(
            "get_all_requests_status",
            {
                "employee_number": str(employee_number).strip(),
                "category_filter": str(category_filter).strip().lower(),
            },
            caller,
        )


_MCP_CLIENT_INSTANCE: Optional[AuthenticatedMCPClient] = None


def get_mcp_client() -> AuthenticatedMCPClient:
    """Returns the process-wide cached AuthenticatedMCPClient instance."""
    global _MCP_CLIENT_INSTANCE
    if _MCP_CLIENT_INSTANCE is None:
        _MCP_CLIENT_INSTANCE = AuthenticatedMCPClient()
    return _MCP_CLIENT_INSTANCE
