"""
Pydantic schema for LLM-driven structured retrieval decisions.
Enables natural-language understanding and dynamic evidence routing
across Policy RAG and Authenticated FastMCP employee records.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

ApprovedSource = Literal["policy_rag", "employee_mcp"]
ApprovedMCPTool = Literal[
    "get_employee_leave_balances",
    "get_employee_assigned_assets",
    "get_employee_it_tickets",
    "get_employee_profile",
    "submit_leave_request",
    "cancel_leave_request",
    "get_leave_request_status",
    "create_it_ticket",
    "update_it_ticket",
    "get_it_ticket_status",
    "submit_reimbursement_request",
    "get_reimbursement_status",
    "create_hr_service_request",
    "get_hr_request_status",
    "submit_equipment_request",
    "get_equipment_request_status",
    "update_employee_contact",
    "get_all_requests_status",
]


class RetrievalDecision(BaseModel):
    """
    Structured retrieval decision produced by LLM intent understanding.
    Constrained to explicitly approved evidence sources and read-only MCP tools.
    """
    intent: str = Field(
        ...,
        description="High-level intent descriptor, e.g. 'policy_query', 'employee_record_query', 'hybrid_query', 'out_of_scope'",
    )
    domains: List[str] = Field(
        default_factory=list,
        description="Business domains involved, e.g. ['benefits'], ['leave'], ['hardware'], ['it_tickets']",
    )
    sources: List[ApprovedSource] = Field(
        default_factory=list,
        description="Explicitly approved retrieval sources: 'policy_rag', 'employee_mcp', or empty for out-of-scope",
    )
    requires_policy_evidence: bool = Field(
        default=False,
        description="True if company-wide policy documents are required via ChromaDB RAG",
    )
    requires_employee_context: bool = Field(
        default=False,
        description="True if individual employee database records are required via FastMCP",
    )
    suggested_mcp_tools: List[ApprovedMCPTool] = Field(
        default_factory=list,
        description="Approved read-only FastMCP tools required for employee data retrieval",
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Optimized semantic search query for policy retrieval, resolving pronouns/follow-ups if multi-turn",
    )
    target_employee: Optional[str] = Field(
        default=None,
        description="Target employee number (e.g. E102) if referenced or inferred",
    )
    is_out_of_scope: bool = Field(
        default=False,
        description="True if the inquiry is completely outside enterprise HR and IT domain",
    )
    clarification_needed: bool = Field(
        default=False,
        description="True if the inquiry is ambiguous and requires user clarification",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Brief justification for the retrieval decision",
    )
