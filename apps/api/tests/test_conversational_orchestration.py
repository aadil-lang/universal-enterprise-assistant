"""
Comprehensive Test Suite for LLM-First Conversational Orchestration.
Verifies the architectural principle:
"LLM-first language understanding. Deterministic enterprise execution."

Test coverage:
1. Pure social pleasantries: Greetings ("Hey Archie!!", "Good morning"), Acknowledgements ("Thanks Archie"), Farewells ("Goodbye")
2. General assistant capability inquiries ("Who are you?", "What can you do?")
3. Mixed pleasantry + enterprise queries ("Hi Archie, what's my leave balance?")
4. Multi-turn context resolution: Anaphoric follow-ups ("What about sick leave?"), Pronoun resolution ("What does it provide?")
5. Topic switching and context resetting across conversational turns
6. Genuine out-of-scope isolation ("Write a poem", "What is Bitcoin's price?")
7. Server-side security and authorization invariance: Peer isolation (Bob accessing Carol) blocked deterministically
8. Deterministic failure handling: LLM provider exceptions return graceful responses without regex-based intent guessing
"""

import asyncio
from typing import Any, Dict
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.auth import CallerIdentity, UserRole
from app.services.agent_workflow import AgentWorkflow
from app.services.llm_service import LLMService, LLMProviderError
from app.services.mcp_client import AuthenticatedMCPClient, MCPAuthorizationError


@pytest.fixture
def mock_mcp_client():
    """Provides an authenticated mock MCP client enforcing Phase 2.2B peer isolation."""
    client = AuthenticatedMCPClient()

    async def in_process_tool_dispatcher(tool_name: str, args: Dict[str, Any], caller: CallerIdentity) -> Dict[str, Any]:
        target_emp = args.get("employee_number", "").strip()

        # Peer isolation authorization rule
        if caller.role == UserRole.EMPLOYEE and target_emp != caller.employee_number:
            raise MCPAuthorizationError(
                f"Forbidden: Employee {caller.employee_number} cannot access records for {target_emp}."
            )

        if tool_name == "get_employee_leave_balances":
            return {
                "found": True,
                "employee_number": target_emp,
                "balances": [
                    {"leave_type": "annual", "accrued_days": 20.0, "used_days": 12.0, "available_days": 8.0},
                    {"leave_type": "sick", "accrued_days": 10.0, "used_days": 2.0, "available_days": 8.0},
                ],
            }
        elif tool_name == "get_employee_assigned_assets":
            return {
                "found": True,
                "employee_number": target_emp,
                "assets": [
                    {"device_type": "laptop", "model": "Lenovo ThinkPad T14", "asset_tag": "LT-8821", "status": "active"},
                ],
            }
        elif tool_name == "get_employee_it_tickets":
            return {
                "found": True,
                "employee_number": target_emp,
                "tickets": [
                    {"ticket_number": "IT-1042", "title": "VPN connection timeout", "status": "open"},
                ],
            }
        elif tool_name == "get_employee_profile":
            return {
                "found": True,
                "employee": {
                    "employee_number": target_emp,
                    "first_name": "Bob" if target_emp == "E102" else "Alice",
                    "department": "Engineering",
                    "status": "active",
                },
            }
        raise ValueError(f"Unknown mock tool: {tool_name}")

    client.call_tool = in_process_tool_dispatcher
    return client


@pytest.fixture
def mock_policy_retriever():
    """Provides an isolated mock retriever returning authoritative Acme policy evidence without external dependencies."""
    retriever = MagicMock()
    retriever.retrieve = MagicMock(return_value={
        "evidence": [
            {
                "document_title": "Acme Employee Leave & Absence Policy",
                "section": "Annual Vacation Leave",
                "page_number": 3,
                "text": "Full-time employees at Acme receive 20 days of paid annual leave per fiscal year. Up to 5 days can carry over.",
                "content_hash": "hash-leave-001",
                "filename": "Acme_Leave_Policy.pdf",
            },
            {
                "document_title": "Acme Employee Leave & Absence Policy",
                "section": "Sick Leave Policy",
                "page_number": 5,
                "text": "Employees receive 10 paid sick days annually. Sick leave requires medical certification if exceeding 3 consecutive days.",
                "content_hash": "hash-sick-001",
                "filename": "Acme_Leave_Policy.pdf",
            },
        ],
        "is_sufficient": True,
        "has_conflict": False,
    })
    return retriever


@pytest.fixture
def bob_caller() -> CallerIdentity:
    return CallerIdentity(
        user_id="b0000000-0000-0000-0000-000000000102",
        employee_number="E102",
        role=UserRole.EMPLOYEE,
    )


@pytest.fixture
def alice_admin_caller() -> CallerIdentity:
    return CallerIdentity(
        user_id="a0000000-0000-0000-0000-000000000101",
        employee_number="E101",
        role=UserRole.HR_ADMIN,
    )


@pytest.fixture
def conversational_agent(mock_policy_retriever, mock_mcp_client) -> AgentWorkflow:
    """Instantiates AgentWorkflow with mock LLM service and mock stores."""
    llm = LLMService(provider="mock")
    return AgentWorkflow(
        retriever=mock_policy_retriever,
        mcp_client=mock_mcp_client,
        llm_service=llm,
    )


# =============================================================================
# 1. Pure Conversational Pleasantries Tests
# =============================================================================
def test_hey_archie_greeting(conversational_agent, bob_caller):
    """
    Core bugfix verification:
    Typing 'Hey Archie!!' MUST NOT throw an out-of-scope error.
    Must return a warm, personalized greeting without unnecessary RAG/MCP retrieval.
    """
    res = asyncio.run(conversational_agent.run(
        question="Hey Archie!!",
        caller=bob_caller,
    ))

    assert res["category"] == "conversational"
    assert res["refusal_reason"] is None
    assert "Bob" in res["answer"] or "Archie" in res["answer"]
    assert res["citations"] == []
    assert res["mcp_tools_used"] == []


def test_standard_greetings(conversational_agent, bob_caller):
    """Verifies various greeting formulations route to conversational."""
    for greeting in ["Good morning", "Hello", "Hi Archie", "Hey there"]:
        res = asyncio.run(conversational_agent.run(
            question=greeting,
            caller=bob_caller,
        ))
        assert res["category"] == "conversational", f"Failed on: {greeting}"
        assert res["refusal_reason"] is None
        assert len(res["answer"]) > 10


def test_acknowledgements_and_farewells(conversational_agent, bob_caller):
    """Verifies pleasantries like thanks and goodbyes respond conversationally."""
    thanks_res = asyncio.run(conversational_agent.run(
        question="Thanks Archie, that was very helpful!",
        caller=bob_caller,
    ))
    assert thanks_res["category"] == "conversational"
    assert thanks_res["refusal_reason"] is None
    assert "welcome" in thanks_res["answer"].lower()

    bye_res = asyncio.run(conversational_agent.run(
        question="Goodbye Archie",
        caller=bob_caller,
    ))
    assert bye_res["category"] == "conversational"
    assert bye_res["refusal_reason"] is None
    assert "goodbye" in bye_res["answer"].lower() or "day" in bye_res["answer"].lower()


# =============================================================================
# 2. General Assistant Capability Inquiries
# =============================================================================
def test_assistant_capabilities_inquiry(conversational_agent, bob_caller):
    """Verifies that asking 'What can you do?' returns capabilities instead of out_of_scope."""
    res = asyncio.run(conversational_agent.run(
        question="What can you do?",
        caller=bob_caller,
    ))
    assert res["category"] == "conversational"
    assert "policy" in res["answer"].lower() or "leave" in res["answer"].lower()


# =============================================================================
# 3. Mixed Pleasantry + Enterprise Query
# =============================================================================
def test_mixed_greeting_and_enterprise_query(conversational_agent, bob_caller):
    """
    Verifies that combining a greeting with a real enterprise query
    (e.g., 'Hi Archie, what is my leave balance?')
    does not discard the question as a pure greeting, but executes the employee lookup.
    """
    res = asyncio.run(conversational_agent.run(
        question="Hi Archie, what is my leave balance?",
        caller=bob_caller,
    ))
    assert res["category"] in ("employee", "hybrid")
    assert "get_employee_leave_balances" in res["mcp_tools_used"]
    assert "8" in res["answer"] or "leave" in res["answer"].lower()


# =============================================================================
# 4. Multi-Turn Context Resolution & Anaphoric Follow-ups
# =============================================================================
def test_multiturn_anaphoric_followup(conversational_agent, bob_caller):
    """
    Verifies that follow-up questions resolve topic from prior turns:
    Turn 1: 'What is my annual leave balance?'
    Turn 2: 'What about sick leave?'
    """
    conv_id = str(uuid.uuid4())

    # Turn 1: Annual leave
    res1 = asyncio.run(conversational_agent.run(
        question="What is my annual leave balance?",
        caller=bob_caller,
        conversation_id=conv_id,
    ))
    assert res1["category"] in ("employee", "hybrid")
    assert "get_employee_leave_balances" in res1["mcp_tools_used"]

    # Turn 2: Follow-up about sick leave
    res2 = asyncio.run(conversational_agent.run(
        question="What about sick leave?",
        caller=bob_caller,
        conversation_id=conv_id,
    ))
    assert res2["category"] in ("employee", "hybrid")
    assert "get_employee_leave_balances" in res2["mcp_tools_used"]
    assert "8" in res2["answer"] or "sick" in res2["answer"].lower()


def test_multiturn_topic_switching(conversational_agent, bob_caller):
    """
    Verifies that conversational context shifts cleanly when the user changes topics:
    Turn 1: Ask about leave balance
    Turn 2: Ask about assigned laptop
    """
    conv_id = str(uuid.uuid4())

    # Turn 1: Leave
    res1 = asyncio.run(conversational_agent.run(
        question="What is my leave balance?",
        caller=bob_caller,
        conversation_id=conv_id,
    ))
    assert "get_employee_leave_balances" in res1["mcp_tools_used"]

    # Turn 2: Switch to hardware asset
    res2 = asyncio.run(conversational_agent.run(
        question="Which laptop is assigned to me?",
        caller=bob_caller,
        conversation_id=conv_id,
    ))
    assert "get_employee_assigned_assets" in res2["mcp_tools_used"]
    assert "ThinkPad" in res2["answer"] or "LT-8821" in res2["answer"]


# =============================================================================
# 5. Out-of-Scope Requests Handling
# =============================================================================
def test_genuine_out_of_scope_refusal(conversational_agent, bob_caller):
    """Verifies that non-enterprise queries receive a polite standard refusal."""
    for prompt in ["Write a poem about sunshine", "What is the price of Bitcoin?"]:
        res = asyncio.run(conversational_agent.run(
            question=prompt,
            caller=bob_caller,
        ))
        assert res["category"] == "out_of_scope"
        assert res["refusal_reason"] is not None
        assert "enterprise HR & IT assistant" in res["answer"]


# =============================================================================
# 6. Security and Peer Isolation Invariant
# =============================================================================
def test_peer_isolation_enforced_in_workflow(conversational_agent, bob_caller, alice_admin_caller):
    """
    Security invariant:
    Employee Bob cannot query Carol (E103). MCP client denies access.
    HR Admin Alice can query Bob (E102).
    """
    # Bob attempts to view E103
    bob_res = asyncio.run(conversational_agent.run(
        question="What is E103's leave balance?",
        caller=bob_caller,
    ))
    assert "Access Denied" in bob_res["answer"] or "not authorized" in bob_res["answer"]

    # Alice (HR Admin) queries E102
    alice_res = asyncio.run(conversational_agent.run(
        question="What is E102's leave balance?",
        caller=alice_admin_caller,
    ))
    assert "Access Denied" not in alice_res["answer"]
    assert "get_employee_leave_balances" in alice_res["mcp_tools_used"]


# =============================================================================
# 7. LLM Failure Handling Without Heuristic Fallback
# =============================================================================
def test_llm_provider_error_graceful_handling(mock_policy_retriever, mock_mcp_client, bob_caller):
    """
    Verifies that when the LLM service raises LLMProviderError,
    the workflow returns a polite conversational failure message
    and DOES NOT fall back to guessing intents via regex.
    """
    failing_llm = LLMService(provider="mock")
    # Mock understand_intent to raise LLMProviderError
    failing_llm.understand_intent = AsyncMock(
        side_effect=LLMProviderError("Gemini API rate limit exceeded")
    )

    agent = AgentWorkflow(
        retriever=mock_policy_retriever,
        mcp_client=mock_mcp_client,
        llm_service=failing_llm,
    )

    res = asyncio.run(agent.run(
        question="What is my leave balance?",
        caller=bob_caller,
    ))

    assert res["category"] == "conversational"
    assert "temporarily unable" in res["answer"]
    # Verify no tools were guessed or executed
    assert res["mcp_tools_used"] == []
    assert res["citations"] == []
