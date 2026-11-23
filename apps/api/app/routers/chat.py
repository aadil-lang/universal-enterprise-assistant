"""
Conversational Chat & Agent Orchestration Router.
Exposes the authenticated /api/v1/chat and /chat endpoints.
Interprets questions via LangGraph, executes policy RAG and internal MCP tools,
and returns structured answers with verifiable inline citations.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import CallerIdentity, get_current_active_user
from app.services.agent_workflow import AgentWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Chat"])


class ChatRequest(BaseModel):
    """Payload for submitting a conversational question."""
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user query or question for the HR & IT Assistant",
        examples=["What is my remaining annual leave balance?"],
    )
    conversation_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional session / conversation ID to maintain multi-turn context",
    )
    confirmation_action: Optional[str] = Field(
        default=None,
        description="Optional confirmation action ('confirm' or 'cancel') for pending transactions",
    )
    confirmation_token: Optional[str] = Field(
        default=None,
        description="Cryptographically bound confirmation token when confirming a transaction",
    )


class CitationModel(BaseModel):
    """Metadata for a policy document citation."""
    model_config = ConfigDict(extra="ignore")

    document_title: str
    filename: str
    section: str
    page_number: int
    content_hash: str


class ChatResponse(BaseModel):
    """Structured response from the LangGraph conversational assistant."""
    model_config = ConfigDict(extra="ignore")

    answer: str
    category: str
    citations: List[CitationModel] = Field(default_factory=list)
    mcp_tools_used: List[str] = Field(default_factory=list)
    retrieval_decision: Optional[dict] = Field(default=None, description="LLM structured intent understanding and routing decision")
    execution_time_ms: float
    llm_provider: Optional[str] = Field(default=None, description="Active LLM provider used for response synthesis")
    llm_model: Optional[str] = Field(default=None, description="Active LLM model used for response synthesis")
    confirmation_required: bool = Field(default=False, description="True if a transaction requires explicit user confirmation")
    confirmation_prompt: Optional[dict] = Field(default=None, description="Metadata and details of the transaction requiring confirmation")
    transaction_result: Optional[dict] = Field(default=None, description="Execution outcome of a confirmed transaction")


_AGENT_INSTANCE: Optional[AgentWorkflow] = None


def get_agent_workflow() -> AgentWorkflow:
    """Dependency provider returning the process-wide AgentWorkflow instance."""
    global _AGENT_INSTANCE
    if _AGENT_INSTANCE is None:
        _AGENT_INSTANCE = AgentWorkflow()
    return _AGENT_INSTANCE


def set_agent_workflow(workflow: Optional[AgentWorkflow]) -> None:
    """Allows injecting a customized workflow for testing."""
    global _AGENT_INSTANCE
    _AGENT_INSTANCE = workflow


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a conversational HR or IT query",
)
@router.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a conversational HR or IT query (v1)",
)
async def chat_endpoint(
    request: ChatRequest,
    current_user: CallerIdentity = Depends(get_current_active_user),
    agent: AgentWorkflow = Depends(get_agent_workflow),
) -> ChatResponse:
    """
    Submits a user query to the LangGraph conversational agent.
    Requires an authenticated Bearer token.
    Authenticates the session, resolves live employee identity,
    routes intent, invokes RAG or MCP as required, and returns a grounded response.
    """
    try:
        result = await agent.run(
            question=request.message,
            caller=current_user,
            conversation_id=request.conversation_id,
            confirmation_action=request.confirmation_action,
            confirmation_token=request.confirmation_token,
        )

        return ChatResponse(
            answer=result["answer"],
            category=result["category"],
            citations=[CitationModel(**c) for c in result.get("citations", [])],
            mcp_tools_used=result.get("mcp_tools_used", []),
            retrieval_decision=result.get("retrieval_decision"),
            execution_time_ms=result.get("execution_time_ms", 0.0),
            llm_provider=result.get("llm_provider"),
            llm_model=result.get("llm_model"),
            confirmation_required=result.get("confirmation_required", False),
            confirmation_prompt=result.get("confirmation_prompt"),
            transaction_result=result.get("transaction_result"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unhandled error in chat endpoint: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request. Please try again later.",
        )
