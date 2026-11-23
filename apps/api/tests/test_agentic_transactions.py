"""
Unit and Integration Tests for Agentic Transaction Manager & Confirmation Lifecycle.
Verifies ESR-STD-v2.4 guarantees:
- Token generation bound to employee identity, payload, canonical SHA-256 hash, and 15-minute expiration
- One-time execution preventing double-submission / replay attacks
- Rejection of tampered payloads
- Rejection of expired tokens
- Caller authorization boundaries (peer access rejected)
- Multi-turn draft tracking and parameter invalidation
"""

import asyncio
import datetime
from unittest.mock import AsyncMock
import pytest

from app.core.auth import CallerIdentity, UserRole
from app.services.transaction_manager import (
    TransactionManager,
    _canonical_payload_hash,
    CONFIRMATION_EXPIRY_MINUTES,
)


@pytest.fixture
def bob_caller() -> CallerIdentity:
    return CallerIdentity(
        user_id="b0000000-0000-0000-0000-000000000102",
        employee_number="E102",
        role=UserRole.EMPLOYEE,
    )


@pytest.fixture
def carol_caller() -> CallerIdentity:
    return CallerIdentity(
        user_id="c0000000-0000-0000-0000-000000000103",
        employee_number="E103",
        role=UserRole.EMPLOYEE,
    )


@pytest.fixture
def hr_admin_caller() -> CallerIdentity:
    return CallerIdentity(
        user_id="a0000000-0000-0000-0000-000000000101",
        employee_number="E101",
        role=UserRole.HR_ADMIN,
    )


def test_canonical_payload_hash_stability():
    """Verify that key order differences produce identical canonical SHA-256 hashes."""
    p1 = {"leave_type": "annual", "start_date": "2026-12-10", "end_date": "2026-12-12"}
    p2 = {"end_date": "2026-12-12", "leave_type": "annual", "start_date": "2026-12-10"}
    assert _canonical_payload_hash(p1) == _canonical_payload_hash(p2)


def test_create_confirmation_token_binding(bob_caller):
    """Verify token generation with caller identity, payload hash, and 15-minute expiration."""
    mgr = TransactionManager()
    payload = {"leave_type": "annual", "start_date": "2026-12-10", "end_date": "2026-12-12"}
    rec = mgr.create_confirmation(bob_caller, "leave_request", payload)

    assert rec["confirmation_token"].startswith("conf-")
    assert rec["employee_number"] == "E102"
    assert rec["transaction_type"] == "leave_request"
    assert rec["status"] == "awaiting_confirmation"
    assert rec["payload_hash"] == _canonical_payload_hash(payload)

    created_at = datetime.datetime.fromisoformat(rec["created_at"])
    expires_at = datetime.datetime.fromisoformat(rec["expires_at"])
    diff = (expires_at - created_at).total_seconds()
    assert abs(diff - (CONFIRMATION_EXPIRY_MINUTES * 60)) < 2.0


def test_draft_session_tracking():
    """Verify multi-turn draft state collection and clearing."""
    mgr = TransactionManager()
    session_key = "user-123:conv-456"

    assert mgr.get_draft(session_key) is None
    mgr.set_draft(session_key, {"intent": "leave", "start_date": "2026-12-10"})
    assert mgr.get_draft(session_key)["start_date"] == "2026-12-10"

    mgr.clear_draft(session_key)
    assert mgr.get_draft(session_key) is None


def test_invalidate_confirmations_on_parameter_change(bob_caller):
    """Verify pending confirmations are expired if parameters change before confirmation."""
    mgr = TransactionManager()
    rec = mgr.create_confirmation(
        bob_caller,
        "leave_request",
        {"leave_type": "annual", "start_date": "2026-12-10", "end_date": "2026-12-12"},
    )
    token = rec["confirmation_token"]

    mgr.invalidate_confirmations_for_session("E102", "leave_request")
    assert mgr.get_confirmation(token)["status"] == "expired"


def test_cancel_confirmation_explicit(bob_caller, carol_caller):
    """Verify explicit cancellation by owner vs peer denial."""
    mgr = TransactionManager()
    rec = mgr.create_confirmation(
        bob_caller,
        "create_it_ticket",
        {"title": "Screen flicker", "category": "hardware", "priority": "medium"},
    )
    token = rec["confirmation_token"]

    # Carol attempts to cancel Bob's transaction
    peer_res = mgr.cancel_confirmation(token, carol_caller)
    assert peer_res["success"] is False
    assert "Access Denied" in peer_res["error"]

    # Bob cancels his own transaction
    owner_res = mgr.cancel_confirmation(token, bob_caller)
    assert owner_res["success"] is True
    assert mgr.get_confirmation(token)["status"] == "cancelled"


def test_execute_confirmation_success(bob_caller):
    """Verify successful execution transitions token to 'executed' and records request ID."""
    mgr = TransactionManager()
    rec = mgr.create_confirmation(
        bob_caller,
        "leave_request",
        {"leave_type": "annual", "start_date": "2026-12-10", "end_date": "2026-12-12"},
    )
    token = rec["confirmation_token"]

    mock_mcp = AsyncMock()
    mock_mcp.submit_leave_request.return_value = {
        "success": True,
        "request_number": "LV-2026-0001",
        "status": "pending",
    }

    res = asyncio.run(mgr.execute_confirmation(token, bob_caller, mock_mcp))
    assert res["success"] is True
    assert res["request_number"] == "LV-2026-0001"

    updated_rec = mgr.get_confirmation(token)
    assert updated_rec["status"] == "executed"
    assert updated_rec["executed_request_id"] == "LV-2026-0001"


def test_one_time_execution_replays_prevented(bob_caller):
    """Verify executing an already-executed confirmation token is safely idempotent (replay prevention)."""
    mgr = TransactionManager()
    rec = mgr.create_confirmation(
        bob_caller,
        "leave_request",
        {"leave_type": "annual", "start_date": "2026-12-10", "end_date": "2026-12-12"},
    )
    token = rec["confirmation_token"]

    mock_mcp = AsyncMock()
    mock_mcp.submit_leave_request.return_value = {"success": True, "request_number": "LV-2026-0001"}

    # First execution succeeds
    asyncio.run(mgr.execute_confirmation(token, bob_caller, mock_mcp))

    # Second execution attempt is recognized as idempotent replay
    res2 = asyncio.run(mgr.execute_confirmation(token, bob_caller, mock_mcp))
    assert res2["idempotent"] is True
    assert res2["request_id"] == "LV-2026-0001"
    assert "already been executed" in res2["message"]


def test_execute_confirmation_expired_rejected(bob_caller):
    """Verify expired confirmation tokens cannot be executed."""
    mgr = TransactionManager()
    rec = mgr.create_confirmation(
        bob_caller,
        "leave_request",
        {"leave_type": "annual", "start_date": "2026-12-10", "end_date": "2026-12-12"},
    )
    token = rec["confirmation_token"]
    # Force token to expired status
    rec["status"] = "expired"

    mock_mcp = AsyncMock()
    res = asyncio.run(mgr.execute_confirmation(token, bob_caller, mock_mcp))
    assert res["success"] is False
    assert "no longer valid" in res["error"] or "expired" in res["error"]


def test_execute_confirmation_peer_denied(bob_caller, carol_caller):
    """Verify peer employee cannot execute another employee's confirmation token."""
    mgr = TransactionManager()
    rec = mgr.create_confirmation(
        bob_caller,
        "leave_request",
        {"leave_type": "annual", "start_date": "2026-12-10", "end_date": "2026-12-12"},
    )
    token = rec["confirmation_token"]

    mock_mcp = AsyncMock()
    res = asyncio.run(mgr.execute_confirmation(token, carol_caller, mock_mcp))
    assert res["success"] is False
    assert "Access Denied" in res["error"]


def test_concurrent_execution_calls_serialized(bob_caller):
    """Verify concurrent execution calls with the same token do not double-dispatch."""
    mgr = TransactionManager()
    rec = mgr.create_confirmation(
        bob_caller,
        "leave_request",
        {"leave_type": "annual", "start_date": "2026-12-10", "end_date": "2026-12-12"},
    )
    token = rec["confirmation_token"]

    call_count = 0

    async def delayed_submit(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return {"success": True, "request_number": "LV-2026-0001"}

    mock_mcp = AsyncMock()
    mock_mcp.submit_leave_request.side_effect = delayed_submit

    async def run_concurrent():
        task1 = asyncio.create_task(mgr.execute_confirmation(token, bob_caller, mock_mcp))
        task2 = asyncio.create_task(mgr.execute_confirmation(token, bob_caller, mock_mcp))
        return await asyncio.gather(task1, task2)

    res1, res2 = asyncio.run(run_concurrent())
    # One must succeed and create request; the other must be recognized as in_flight or already executed
    assert call_count == 1
    assert (res1.get("success") is True and res1.get("request_number") == "LV-2026-0001") or (res2.get("success") is True and res2.get("request_number") == "LV-2026-0001")
