"""
Pydantic schema for LLM-driven structured retrieval decisions.
Enables natural-language understanding and dynamic evidence routing
across Policy RAG and Authenticated FastMCP employee records.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

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

InteractionType = Literal[
    "greeting",                 # "Hey Archie", "Good morning"
    "acknowledgement",          # "Thanks", "Got it", "Understood"
    "farewell",                 # "Goodbye", "Bye Archie"
    "general_inquiry",          # "Who are you?", "What can you help me with?"
    "policy_inquiry",           # "What is the remote work policy?"
    "employee_inquiry",         # "What is my remaining annual leave balance?"
    "hybrid_inquiry",           # "What are the leave rules and how many days do I have?"
    "transaction_request",      # "I need off next Wednesday to Friday"
    "clarification_response",   # "Yes, annual leave" (answers outstanding clarification)
    "out_of_scope",             # Unrelated trivia, poetry, crypto
]


class RetrievalDecision(BaseModel):
    """
    Unified LLM structured decision governing conversation, retrieval,
    tool selection, clarification, and transaction parameter extraction.
    """
    model_config = ConfigDict(extra="ignore")

    interaction_type: InteractionType = Field(
        default="policy_inquiry",
        description="Categorized interaction pattern: greeting, acknowledgement, farewell, general_inquiry, policy_inquiry, employee_inquiry, hybrid_inquiry, transaction_request, clarification_response, out_of_scope",
    )
    intent: str = Field(
        ...,
        description="High-level intent descriptor, e.g. 'policy_query', 'employee_record_query', 'hybrid_query', 'greeting', 'transaction_request', 'out_of_scope'",
    )
    domains: List[str] = Field(
        default_factory=list,
        description="Business domains involved, e.g. ['benefits'], ['leave'], ['hardware'], ['it_tickets']",
    )
    sources: List[ApprovedSource] = Field(
        default_factory=list,
        description="Explicitly approved retrieval sources: 'policy_rag', 'employee_mcp', or empty for out-of-scope/conversational",
    )
    requires_retrieval: bool = Field(
        default=False,
        description="True if external evidence retrieval (ChromaDB or FastMCP) is needed",
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
    clarification_question: Optional[str] = Field(
        default=None,
        description="Specific question to present to the user to resolve ambiguity",
    )
    transaction_type: Optional[str] = Field(
        default=None,
        description="Transactional workflow identifier if interaction_type is 'transaction_request'",
    )
    extracted_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured transaction parameters extracted from user utterance",
    )
    proposed_direct_response: Optional[str] = Field(
        default=None,
        description="Natural language response for greetings, pleasantries, or clarifications",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Brief justification for the retrieval decision",
    )


# Alias for comprehensive conversational decision nomenclature
ConversationalDecision = RetrievalDecision
