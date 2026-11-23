"""
Unit & Integration Tests for LLM-Driven Intent Understanding and Dynamic Evidence Routing.
Verifies that:
1. Natural language questions (perks, benefits, allowances, stipends) route to policy_rag.
2. Employee record questions route to employee_mcp with correct tool suggestions.
3. Hybrid questions route to both policy_rag and employee_mcp.
4. Genuinely out-of-scope questions route to out_of_scope with is_out_of_scope=True.
5. Conversational multi-turn context properly resolves pronouns and anaphoric follow-ups.
6. Authorization invariants (peer isolation) are strictly enforced regardless of LLM recommendations.
"""

import asyncio
from typing import Any, Dict
import uuid
import chromadb
import pytest

from app.core.auth import CallerIdentity, UserRole
from app.schemas.document import DocumentChunk
from app.schemas.retrieval import RetrievalDecision
from app.services.agent_workflow import AgentWorkflow
from app.services.llm_service import LLMService
from app.services.mcp_client import AuthenticatedMCPClient, MCPAuthorizationError
from app.services.policy_retriever import PolicyRetriever
from app.services.vector_store import VectorStoreService


@pytest.fixture
def mock_mcp_client():
    """Provides an isolated mock MCP client enforcing Phase 2.2B authorization."""
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
                    {"leave_type": "annual", "accrued_days": 20.0, "used_days": 10.0, "available_days": 8.0},
                    {"leave_type": "sick", "accrued_days": 10.0, "used_days": 2.0, "available_days": 8.0},
                ],
            }
        elif tool_name == "get_employee_assigned_assets":
            return {
                "found": True,
                "employee_number": target_emp,
                "assets": [
                    {"device_type": "laptop", "model": "Lenovo ThinkPad T14", "asset_tag": "LT-8821"},
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
                    "first_name": "Bob",
                    "last_name": "Jones",
                    "job_title": "Senior Software Engineer",
                },
            }
        raise ValueError(f"Unknown tool: {tool_name}")

    client.call_tool = in_process_tool_dispatcher
    return client


@pytest.fixture
def populated_vector_store():
    """Provides an ephemeral ChromaDB vector store with test policy chunks."""
    client = chromadb.EphemeralClient()
    store = VectorStoreService(client=client, collection_name=f"test_intent_{uuid.uuid4().hex[:8]}")

    doc1_id = "00000000-0000-0000-0000-000000000001"
    doc1_checksum = "0a6699566aa259c20a6699566aa259c20a6699566aa259c20a6699566aa259c2"
    chunks1 = [
        DocumentChunk(
            chunk_id=f"{doc1_id}_{doc1_checksum}_0",
            document_id=doc1_id,
            chunk_index=0,
            document_checksum=doc1_checksum,
            content_hash="hash_0",
            text="[Document: Acme Leave Policy | Section: Annual Vacation Leave]\n"
                 "Acme employees accrue 18 days of paid vacation per year. A maximum of 5 days can rollover into the next calendar year.",
            section="Annual Vacation Leave",
            page_number=1,
            char_count=180,
            token_count=40,
        ),
    ]
    store.index_document_chunks(doc1_id, "Acme_Leave_Policy.pdf", "Acme Leave Policy", "HR", chunks1)

    return store, {doc1_id: doc1_checksum}


@pytest.fixture
def agent_workflow(populated_vector_store, mock_mcp_client):
    """Initializes an AgentWorkflow with test fixtures in mock mode."""
    store, active_map = populated_vector_store
    retriever = PolicyRetriever(vector_store=store)
    retriever.get_active_version_map = lambda: active_map
    llm_service = LLMService(provider="mock")
    return AgentWorkflow(retriever=retriever, mcp_client=mock_mcp_client, llm_service=llm_service)


# =============================================================================
# 1. Natural Language Policy Routing Tests
# =============================================================================
@pytest.mark.parametrize(
    "question,expected_sources,expected_domain",
    [
        ("What are the perks given to employees?", ["policy_rag"], "benefits"),
        ("What benefits does the company provide?", ["policy_rag"], "benefits"),
        ("Do we get an ergonomic allowance?", ["policy_rag"], "benefits"),
        ("What leave benefits are available?", ["policy_rag"], "leave"),
        ("What are the laptop replacement rules?", ["policy_rag"], "it_policy"),
        ("What is the remote work policy?", ["policy_rag"], "it_policy"),
        ("What is our policy on pet insurance?", ["policy_rag"], "benefits"),
        ("Any cool perks here for staff?", ["policy_rag"], "benefits"),
        ("How much vacay time can I roll over into next year?", ["policy_rag"], "leave"),
    ],
)
def test_llm_intent_policy_questions_route_to_rag(agent_workflow, question, expected_sources, expected_domain):
    """Verify legitimate policy, perks, and benefits questions route to policy_rag."""
    bob = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    state = {"question": question, "caller": bob}
    res = asyncio.run(agent_workflow.intent_router_node(state))

    assert res["category"] in ("policy", "hybrid")
    decision = res.get("retrieval_decision")
    assert decision is not None
    assert "policy_rag" in decision["sources"]
    assert decision["requires_policy_evidence"] is True
    assert decision["is_out_of_scope"] is False


# =============================================================================
# 2. Individual Employee MCP Routing Tests
# =============================================================================
@pytest.mark.parametrize(
    "question,expected_tool",
    [
        ("How many leave days do I have left?", "get_employee_leave_balances"),
        ("What is my current sick leave balance?", "get_employee_leave_balances"),
        ("What equipment has been assigned to me?", "get_employee_assigned_assets"),
        ("Which laptop do I currently have?", "get_employee_assigned_assets"),
        ("Can you show me my open IT tickets?", "get_employee_it_tickets"),
        ("What is my employment profile?", "get_employee_profile"),
    ],
)
def test_llm_intent_employee_questions_route_to_mcp(agent_workflow, question, expected_tool):
    """Verify individual employee questions route to employee_mcp with expected tool."""
    bob = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    state = {"question": question, "caller": bob}
    res = asyncio.run(agent_workflow.intent_router_node(state))

    assert res["category"] == "employee"
    decision = res.get("retrieval_decision")
    assert decision is not None
    assert decision["sources"] == ["employee_mcp"]
    assert decision["requires_employee_context"] is True
    assert decision["requires_policy_evidence"] is False
    assert expected_tool in decision["suggested_mcp_tools"]


# =============================================================================
# 3. Hybrid Routing Tests
# =============================================================================
@pytest.mark.parametrize(
    "question",
    [
        "What benefits do I get, and how much leave do I have remaining?",
        "How many vacation days am I entitled to, and how many do I have remaining?",
        "What is the company leave policy, and what is my current leave balance?",
    ],
)
def test_llm_intent_hybrid_questions_route_to_both(agent_workflow, question):
    """Verify hybrid queries request both policy_rag and employee_mcp."""
    bob = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    state = {"question": question, "caller": bob}
    res = asyncio.run(agent_workflow.intent_router_node(state))

    assert res["category"] == "hybrid"
    decision = res.get("retrieval_decision")
    assert decision is not None
    assert set(decision["sources"]) == {"policy_rag", "employee_mcp"}
    assert decision["requires_policy_evidence"] is True
    assert decision["requires_employee_context"] is True


# =============================================================================
# 4. Out-of-Scope Rejection Tests
# =============================================================================
@pytest.mark.parametrize(
    "question",
    [
        "Write me a poem about autumn leaves",
        "Explain cryptocurrency trading strategies",
        "What is the capital of Japan?",
        "Who is the president of France?",
        "Give me a recipe for chocolate cake",
    ],
)
def test_llm_intent_out_of_scope_rejection(agent_workflow, question):
    """Verify genuinely unrelated questions are marked out_of_scope with empty sources."""
    bob = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    state = {"question": question, "caller": bob}
    res = asyncio.run(agent_workflow.intent_router_node(state))

    assert res["category"] == "out_of_scope"
    decision = res.get("retrieval_decision")
    assert decision is not None
    assert decision["is_out_of_scope"] is True
    assert decision["sources"] == []


# =============================================================================
# 5. Multi-Turn Conversational Follow-up Tests
# =============================================================================
def test_conversational_followup_routing(agent_workflow):
    """Verify multi-turn follow-ups resolve pronouns and maintain context across turns."""
    bob = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    conv_id = f"test-conv-{uuid.uuid4().hex[:6]}"

    # Turn 1: Policy question
    t1_res = asyncio.run(agent_workflow.run("What is the annual vacation entitlement?", caller=bob, conversation_id=conv_id))
    assert t1_res["category"] == "policy"

    # Turn 2: Follow-up asking personal balance with pronoun "do I have left"
    t2_res = asyncio.run(agent_workflow.run("And how much do I have left?", caller=bob, conversation_id=conv_id))
    assert t2_res["category"] in ("employee", "hybrid")
    assert "get_employee_leave_balances" in t2_res["mcp_tools_used"]
    assert "8.0" in t2_res["answer"] or "8" in t2_res["answer"]

    # Turn 3: Follow-up asking policy carryover with pronoun "it"
    t3_res = asyncio.run(agent_workflow.run("And what about carryover for it?", caller=bob, conversation_id=conv_id))
    assert t3_res["category"] in ("policy", "hybrid")
    assert len(t3_res["citations"]) > 0


# =============================================================================
# 6. Security Peer Isolation Invariant Tests
# =============================================================================
def test_peer_isolation_enforcement(agent_workflow):
    """Verify security boundary: Bob (E102) attempting to query Carol (E103) is denied access."""
    bob = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    res = asyncio.run(agent_workflow.run("What is Carol's leave balance for E103?", caller=bob))

    # Access Denied must be communicated and Carol's records must NOT be revealed
    assert "access denied" in res["answer"].lower() or "not authorized" in res["answer"].lower()
    assert "Carol" not in res["answer"] or "denied" in res["answer"].lower()
