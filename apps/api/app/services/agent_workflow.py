"""
LangGraph Conversational Orchestration Agent Core.
Implements the deterministic state machine workflow defined in Phase 0 §8:
1. Input validation & prompt injection detection.
2. Intent classification (Policy, Employee, Hybrid, Out-of-Scope).
3. ChromaDB policy retrieval with PostgreSQL active-version verification.
4. Authenticated internal FastMCP tool invocation.
5. Grounded response synthesis with XML reference framing.
6. Post-flight citation verification and PII scrubbing.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.auth import CallerIdentity, UserRole
from app.schemas.retrieval import RetrievalDecision
from app.services.guardrails import GuardrailService
from app.services.llm_service import LLMService
from app.services.mcp_client import AuthenticatedMCPClient, MCPAuthorizationError, get_mcp_client
from app.services.policy_retriever import PolicyRetriever
from app.services.transaction_intent_handler import TransactionIntentHandler

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    """Explicit typed state schema driving the LangGraph orchestration workflow."""
    question: str
    caller: CallerIdentity
    conversation_id: Optional[str]
    history: List[Dict[str, Any]]
    target_employee: Optional[str]
    search_query: Optional[str]
    category: str  # "policy", "employee", "hybrid", "out_of_scope"
    policy_evidence: List[Dict[str, Any]]
    is_sufficient: bool
    has_conflict: bool
    mcp_data: Dict[str, Any]
    mcp_tools_used: List[str]
    citations: List[Dict[str, Any]]
    final_answer: str
    refusal_reason: Optional[str]
    guardrail_status: Dict[str, Any]
    retrieval_decision: Optional[Dict[str, Any]]
    execution_time_ms: float


class AgentWorkflow:
    """Orchestrates the LangGraph conversational AI assistant."""

    def __init__(
        self,
        retriever: Optional[PolicyRetriever] = None,
        mcp_client: Optional[AuthenticatedMCPClient] = None,
        llm_service: Optional[LLMService] = None,
        tx_handler: Optional[TransactionIntentHandler] = None,
    ):
        self.retriever = retriever or PolicyRetriever()
        self.mcp_client = mcp_client or get_mcp_client()
        self.llm_service = llm_service or LLMService()
        self.tx_handler = tx_handler or TransactionIntentHandler()
        self._conversation_sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.graph = self._build_graph()

    def _build_graph(self):
        """Builds and compiles the deterministic LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # 1. Register nodes
        workflow.add_node("input_guardrail", self.input_guardrail_node)
        workflow.add_node("intent_router", self.intent_router_node)
        workflow.add_node("retrieve_policy", self.retrieve_policy_node)
        workflow.add_node("execute_mcp", self.execute_mcp_node)
        workflow.add_node("handle_out_of_scope", self.handle_out_of_scope_node)
        workflow.add_node("synthesize_response", self.synthesize_response_node)
        workflow.add_node("post_flight_guardrail", self.post_flight_guardrail_node)

        # 2. Add control edges
        workflow.add_edge(START, "input_guardrail")

        workflow.add_conditional_edges(
            "input_guardrail",
            self._route_after_input_guardrail,
            {
                "blocked": "post_flight_guardrail",
                "clean": "intent_router",
            },
        )

        workflow.add_conditional_edges(
            "intent_router",
            self._route_after_intent,
            {
                "out_of_scope": "handle_out_of_scope",
                "policy": "retrieve_policy",
                "employee": "execute_mcp",
                "hybrid": "retrieve_policy",
            },
        )

        workflow.add_edge("handle_out_of_scope", "post_flight_guardrail")

        workflow.add_conditional_edges(
            "retrieve_policy",
            self._route_after_retrieval,
            {
                "hybrid_continue": "execute_mcp",
                "synthesize": "synthesize_response",
            },
        )

        workflow.add_edge("execute_mcp", "synthesize_response")
        workflow.add_edge("synthesize_response", "post_flight_guardrail")
        workflow.add_edge("post_flight_guardrail", END)

        return workflow.compile()

    # =========================================================================
    # Conditional Edge Routing
    # =========================================================================
    @staticmethod
    def _route_after_input_guardrail(state: AgentState) -> str:
        if state["guardrail_status"].get("blocked"):
            return "blocked"
        return "clean"

    @staticmethod
    def _route_after_intent(state: AgentState) -> str:
        return state.get("category", "out_of_scope")

    @staticmethod
    def _route_after_retrieval(state: AgentState) -> str:
        if state.get("category") == "hybrid":
            return "hybrid_continue"
        return "synthesize"

    # =========================================================================
    # Node 1: Input Guardrail Node
    # =========================================================================
    async def input_guardrail_node(self, state: AgentState) -> Dict[str, Any]:
        """Pre-flight check: detects prompt injections and redacts sensitive non-operational PII."""
        question = state.get("question", "")
        res = GuardrailService.inspect_input(question)

        if not res["is_valid"]:
            return {
                "question": res["sanitized_query"],
                "guardrail_status": {
                    "blocked": True,
                    "injection_detected": res["injection_detected"],
                    "reason": res["refusal_reason"],
                },
                "final_answer": res["refusal_reason"],
                "refusal_reason": res["refusal_reason"],
                "category": "out_of_scope",
            }

        return {
            "question": res["sanitized_query"],
            "guardrail_status": {
                "blocked": False,
                "injection_detected": False,
                "reason": None,
            },
        }

    # =========================================================================
    # Node 2: Intent Router Node
    # =========================================================================
    async def intent_router_node(self, state: AgentState) -> Dict[str, Any]:
        """
        LLM-driven intent understanding and dynamic evidence routing.
        Uses structured Pydantic decision to select approved retrieval sources:
        policy_rag (ChromaDB), employee_mcp (FastMCP), or both (hybrid).
        """
        decision: RetrievalDecision = await self.llm_service.understand_intent(
            question=state["question"],
            caller=state.get("caller"),
            history=state.get("history"),
        )

        # Dynamic category determination from approved retrieval sources
        if decision.is_out_of_scope or (not decision.requires_policy_evidence and not decision.requires_employee_context):
            category = "out_of_scope"
        elif decision.requires_policy_evidence and decision.requires_employee_context:
            category = "hybrid"
        elif decision.requires_policy_evidence:
            category = "policy"
        elif decision.requires_employee_context:
            category = "employee"
        else:
            category = "out_of_scope"

        return {
            "category": category,
            "retrieval_decision": decision.model_dump(),
            "search_query": decision.search_query or state["question"],
            "target_employee": decision.target_employee or state.get("target_employee"),
        }

    # =========================================================================
    # Node 3: Policy Retrieval Node (ChromaDB + PostgreSQL)
    # =========================================================================
    async def retrieve_policy_node(self, state: AgentState) -> Dict[str, Any]:
        """Queries active ChromaDB chunks with authoritative PostgreSQL version cross-referencing."""
        query = state.get("search_query") or state["question"]
        res = self.retriever.retrieve(query)

        return {
            "policy_evidence": res.get("evidence", []),
            "is_sufficient": res.get("is_sufficient", False),
            "has_conflict": res.get("has_conflict", False),
        }

    # =========================================================================
    # Node 4: MCP Tool Execution Node
    # =========================================================================
    async def execute_mcp_node(self, state: AgentState) -> Dict[str, Any]:
        """Dispatches verified employee database query through internal authenticated MCP client."""
        caller = state["caller"]
        q = state["question"].lower()
        tools_used = []
        data: Dict[str, Any] = {}

        # Authorization invariant:
        # Determine target employee number
        target_emp_no = caller.employee_number

        # If caller is hr_admin, inspect whether another employee number (e.g. E102, E103) is specified or in state
        if caller.role == UserRole.HR_ADMIN:
            match = re.search(r"\b(E\d{3,4})\b", state["question"], re.I)
            if match:
                target_emp_no = match.group(1).upper()
            elif state.get("target_employee"):
                target_emp_no = state.get("target_employee")
        else:
            # If caller is employee but prompts for another employee:
            match = re.search(r"\b(E\d{3,4})\b", state["question"], re.I)
            if match and match.group(1).upper() != caller.employee_number:
                # User is attempting peer access (e.g. Bob asks for E103)
                target_emp_no = match.group(1).upper()
            elif state.get("target_employee") and state.get("target_employee") != caller.employee_number:
                target_emp_no = state.get("target_employee")

        # Determine which tools to invoke from structured decision or query topics
        decision_dict = state.get("retrieval_decision") or {}
        suggested_tools = decision_dict.get("suggested_mcp_tools") or []

        try:
            if "get_employee_leave_balances" in suggested_tools:
                tools_used.append("get_employee_leave_balances")
                data = await self.mcp_client.get_employee_leave_balances(
                    employee_number=target_emp_no,
                    caller=caller,
                )
            elif "get_employee_assigned_assets" in suggested_tools:
                tools_used.append("get_employee_assigned_assets")
                data = await self.mcp_client.get_employee_assigned_assets(
                    employee_number=target_emp_no,
                    caller=caller,
                )
            elif "get_employee_it_tickets" in suggested_tools:
                tools_used.append("get_employee_it_tickets")
                data = await self.mcp_client.get_employee_it_tickets(
                    employee_number=target_emp_no,
                    caller=caller,
                )
            elif "get_employee_profile" in suggested_tools:
                tools_used.append("get_employee_profile")
                data = await self.mcp_client.get_employee_profile(
                    employee_number=target_emp_no,
                    caller=caller,
                )
            elif "leave" in q or "vacation" in q or "sick" in q or "balance" in q or "day" in q:
                tools_used.append("get_employee_leave_balances")
                data = await self.mcp_client.get_employee_leave_balances(
                    employee_number=target_emp_no,
                    caller=caller,
                )
            elif "asset" in q or "laptop" in q or "equipment" in q or "device" in q or "tag" in q or "hardware" in q:
                tools_used.append("get_employee_assigned_assets")
                data = await self.mcp_client.get_employee_assigned_assets(
                    employee_number=target_emp_no,
                    caller=caller,
                )
            elif "ticket" in q or "vpn" in q or "issue" in q:
                tools_used.append("get_employee_it_tickets")
                data = await self.mcp_client.get_employee_it_tickets(
                    employee_number=target_emp_no,
                    caller=caller,
                )
            else:
                tools_used.append("get_employee_profile")
                data = await self.mcp_client.get_employee_profile(
                    employee_number=target_emp_no,
                    caller=caller,
                )
        except MCPAuthorizationError as auth_err:
            logger.warning("MCP tool execution blocked by authorization boundary: %s", auth_err)
            data = {"error": "Access Denied: You are not authorized to view records for this employee."}
        except Exception as e:
            logger.error("MCP tool execution failed: %s", e)
            data = {"error": f"Tool execution failed: {e}"}

        return {
            "mcp_data": data,
            "mcp_tools_used": tools_used,
        }


    # =========================================================================
    # Node 5: Handle Out-of-Scope Node
    # =========================================================================
    async def handle_out_of_scope_node(self, state: AgentState) -> Dict[str, Any]:
        """Provides polite standard refusal for requests outside enterprise HR and IT."""
        return {
            "final_answer": "I am an enterprise HR & IT assistant. I can only assist with company policies and your employee records.",
            "refusal_reason": "Out of scope request.",
        }

    # =========================================================================
    # Node 6: Response Synthesis Node
    # =========================================================================
    async def synthesize_response_node(self, state: AgentState) -> Dict[str, Any]:
        """Synthesizes grounded answers strictly from retrieved evidence and verified MCP data."""
        from app.services.llm_service import LLMProviderError
        try:
            answer = await self.llm_service.generate_response(
                question=state["question"],
                category=state["category"],
                policy_evidence=state.get("policy_evidence", []),
                mcp_data=state.get("mcp_data", {}),
                is_sufficient=state.get("is_sufficient", True),
                has_conflict=state.get("has_conflict", False),
            )
        except LLMProviderError as pe:
            logger.error("LLM provider error during synthesis: %s", pe)
            answer = f"The AI assistant is temporarily unavailable: {pe}"
        except Exception as e:
            logger.error("Unexpected error during synthesis: %s", e)
            answer = "An error occurred while generating the assistant response. Please try again later."

        return {"final_answer": answer}

    # =========================================================================
    # Node 7: Post-Flight Guardrail Node
    # =========================================================================
    async def post_flight_guardrail_node(self, state: AgentState) -> Dict[str, Any]:
        """Validates citations against retrieved chunks and scrubs leaked sensitive entities."""
        raw_answer = state.get("final_answer", "")
        evidence = state.get("policy_evidence", [])

        sanitized_answer, citations = GuardrailService.validate_citations(
            response_text=raw_answer,
            retrieved_evidence=evidence,
        )

        # Attach top verified evidence chunk citation deterministically if not cited in brackets
        if not citations and evidence and state.get("category") in ("policy", "hybrid"):
            top_ev = evidence[0]
            citations.append({
                "document_title": top_ev.get("document_title", "Company Policy"),
                "filename": top_ev.get("filename", ""),
                "section": top_ev.get("section", "General"),
                "page_number": top_ev.get("page_number", 1),
                "content_hash": top_ev.get("content_hash", ""),
            })

        return {
            "final_answer": sanitized_answer,
            "citations": citations,
        }

    # =========================================================================
    # Execution Entrypoint
    # =========================================================================
    async def run(
        self,
        question: str,
        caller: CallerIdentity,
        conversation_id: Optional[str] = None,
        confirmation_action: Optional[str] = None,
        confirmation_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full LangGraph conversational workflow for a user inquiry.
        Handles transactional workflows with confirmation lifecycle and maintains
        conversational session history to support anaphoric follow-up resolution (DEF-01).
        """
        start_time = time.perf_counter()

        session_key = f"{caller.user_id}:{conversation_id or 'default'}"

        # 0. Check for transactional workflows or active confirmation handling
        tx_result = await self.tx_handler.handle_message(
            message=question,
            caller=caller,
            session_key=session_key,
            mcp_client=self.mcp_client,
            confirmation_action=confirmation_action,
            confirmation_token=confirmation_token,
        )

        if tx_result is not None:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            tx_result["execution_time_ms"] = round(elapsed_ms, 2)
            tx_result["llm_provider"] = getattr(self.llm_service, "provider", "gemini")
            tx_result["llm_model"] = getattr(self.llm_service, "model", "gemini-3.5-flash-lite")
            if "citations" not in tx_result:
                tx_result["citations"] = []
            if "mcp_tools_used" not in tx_result:
                tx_result["mcp_tools_used"] = []
            return tx_result

        history = self._conversation_sessions.get(session_key, [])

        initial_state: AgentState = {
            "question": question,
            "caller": caller,
            "conversation_id": conversation_id,
            "history": list(history),
            "category": "out_of_scope",
            "policy_evidence": [],
            "is_sufficient": False,
            "has_conflict": False,
            "mcp_data": {},
            "mcp_tools_used": [],
            "citations": [],
            "final_answer": "",
            "refusal_reason": None,
            "guardrail_status": {},
            "execution_time_ms": 0.0,
        }

        final_state = await self.graph.ainvoke(initial_state)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Update session history for conversational context (DEF-01)
        if final_state.get("category") != "out_of_scope":
            q_lower = question.lower()
            topic = ""
            if "leave" in q_lower or "vacation" in q_lower or "holiday" in q_lower:
                topic = "annual leave"
            elif "sick" in q_lower:
                topic = "sick leave"
            elif any(w in q_lower for w in ("laptop", "computer", "hardware", "asset", "equipment")):
                topic = "assigned laptop hardware"
            elif "vpn" in q_lower or "remote" in q_lower:
                topic = "remote work VPN security"
            elif "stipend" in q_lower or "ergonomic" in q_lower:
                topic = "ergonomic stipend"
            elif "ticket" in q_lower or "support" in q_lower:
                topic = "IT support tickets"
            else:
                topic = final_state.get("category", "")

            decision_dict = final_state.get("retrieval_decision") or {}
            domains = decision_dict.get("domains") or []
            if domains:
                topic = " ".join(domains)
            elif not topic:
                topic = final_state.get("category", "")

            target_emp = None
            match = re.search(r"\b(E\d{3,4})\b", question, re.I)
            if match:
                target_emp = match.group(1).upper()
            elif final_state.get("target_employee"):
                target_emp = final_state.get("target_employee")
            elif caller.role == UserRole.EMPLOYEE:
                target_emp = caller.employee_number

            turn_entry = {
                "question": question,
                "category": final_state.get("category"),
                "topic": topic,
                "target_employee": target_emp,
                "answer": final_state.get("final_answer"),
                "retrieval_decision": decision_dict,
            }
            if session_key not in self._conversation_sessions:
                self._conversation_sessions[session_key] = []
            self._conversation_sessions[session_key].append(turn_entry)
            if len(self._conversation_sessions[session_key]) > 10:
                self._conversation_sessions[session_key] = self._conversation_sessions[session_key][-10:]

        return {
            "answer": final_state["final_answer"],
            "category": final_state["category"],
            "citations": final_state["citations"],
            "mcp_tools_used": final_state["mcp_tools_used"],
            "refusal_reason": final_state["refusal_reason"],
            "retrieval_decision": final_state.get("retrieval_decision"),
            "execution_time_ms": round(elapsed_ms, 2),
            "llm_provider": getattr(self.llm_service, "provider", "mock"),
            "llm_model": getattr(self.llm_service, "model", "mock"),
        }

