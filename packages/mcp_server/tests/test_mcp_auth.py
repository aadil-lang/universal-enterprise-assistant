"""
Comprehensive Security Regression Test Suite for Phase 2.2B.
Verifies MCP identity authentication, HMAC signature verification, constant-time comparison,
role-based employee authorization boundary enforcement, context isolation, and protocol integration.

Covers all 24 required test scenarios (A through X):
- Authentication Tests (A-F)
- Authorization Tests (G-R)
- Context Isolation Tests (S-T)
- Protocol Integration Tests (U-X)
"""

import asyncio
import json
import socket
import threading
import time
from typing import Generator
import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from app.auth.context import (
    MCPAuthorizationError,
    caller_identity_var,
    get_current_caller,
    reset_current_caller,
    set_current_caller,
)
from app.auth.middleware import HMACAuthMiddleware
from app.auth.models import CallerIdentity, UserRole
from app.auth.signer import create_internal_auth_headers
from app.config.settings import get_mcp_settings
from app.database.connection import DatabaseManager, set_db_manager
from app.main import create_mcp_app, create_mcp_server
from app.tools.employee_tools import (
    get_employee_assigned_assets_handler,
    get_employee_it_tickets_handler,
    get_employee_leave_balances_handler,
    get_employee_profile_handler,
)


def find_free_port() -> int:
    """Dynamically allocate an available ephemeral TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# =============================================================================
# Isolated SQLite In-Memory Database Fixture with Authoritative Seed Data
# =============================================================================
@pytest.fixture(autouse=True)
def setup_auth_test_database() -> Generator[DatabaseManager, None, None]:
    """Sets up an in-memory SQLite database populated with Acme seed data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE employees (
                    id TEXT PRIMARY KEY,
                    employee_number TEXT UNIQUE NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    corporate_email TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    department TEXT NOT NULL,
                    hire_date TEXT NOT NULL,
                    employment_status TEXT NOT NULL DEFAULT 'active'
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE app_users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'employee',
                    employee_id TEXT NOT NULL REFERENCES employees(id),
                    is_active INTEGER NOT NULL DEFAULT 1
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE leave_balances (
                    id TEXT PRIMARY KEY,
                    employee_id TEXT NOT NULL REFERENCES employees(id),
                    leave_type TEXT NOT NULL,
                    accrued_days REAL NOT NULL DEFAULT 0.0,
                    used_days REAL NOT NULL DEFAULT 0.0,
                    pending_days REAL NOT NULL DEFAULT 0.0,
                    available_days REAL GENERATED ALWAYS AS (accrued_days - used_days - pending_days) STORED,
                    fiscal_year INTEGER NOT NULL
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE it_assets (
                    id TEXT PRIMARY KEY,
                    employee_id TEXT REFERENCES employees(id),
                    asset_tag TEXT UNIQUE NOT NULL,
                    device_type TEXT NOT NULL,
                    make_model TEXT NOT NULL,
                    serial_number TEXT NOT NULL,
                    assigned_date TEXT,
                    condition_status TEXT NOT NULL DEFAULT 'active'
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE it_tickets (
                    id TEXT PRIMARY KEY,
                    employee_id TEXT NOT NULL REFERENCES employees(id),
                    ticket_number TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )

        # Seed data
        conn.execute(
            text(
                """
                INSERT INTO employees (id, employee_number, first_name, last_name, corporate_email, job_title, department, hire_date, employment_status)
                VALUES 
                ('a0000000-0000-0000-0000-000000000101', 'E101', 'Alice', 'Smith', 'alice@acme.com', 'HR Director', 'Human Resources', '2021-03-15', 'active'),
                ('a0000000-0000-0000-0000-000000000102', 'E102', 'Bob', 'Jones', 'bob@acme.com', 'Senior Software Engineer', 'Engineering', '2022-06-01', 'active'),
                ('a0000000-0000-0000-0000-000000000103', 'E103', 'Carol', 'Davis', 'carol@acme.com', 'Marketing Specialist', 'Marketing', '2023-01-10', 'active'),
                ('a0000000-0000-0000-0000-000000000104', 'E104', 'David', 'Miller', 'david@acme.com', 'Operations Associate', 'Operations', '2023-04-01', 'active');
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO app_users (id, email, password_hash, role, employee_id, is_active)
                VALUES 
                ('b0000000-0000-0000-0000-000000000101', 'alice@acme.com', '$2b$12$cWUuhQr0YEKbHoHu0qm5B.QL9wkX6mqy3SjOwU0HtLKvVoQBHI1Z2', 'hr_admin', 'a0000000-0000-0000-0000-000000000101', 1),
                ('b0000000-0000-0000-0000-000000000102', 'bob@acme.com', '$2b$12$cWUuhQr0YEKbHoHu0qm5B.QL9wkX6mqy3SjOwU0HtLKvVoQBHI1Z2', 'employee', 'a0000000-0000-0000-0000-000000000102', 1),
                ('b0000000-0000-0000-0000-000000000103', 'carol@acme.com', '$2b$12$cWUuhQr0YEKbHoHu0qm5B.QL9wkX6mqy3SjOwU0HtLKvVoQBHI1Z2', 'employee', 'a0000000-0000-0000-0000-000000000103', 1);
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO leave_balances (id, employee_id, leave_type, accrued_days, used_days, pending_days, fiscal_year)
                VALUES 
                ('c0000000-0000-0000-0000-000000000103', 'a0000000-0000-0000-0000-000000000102', 'annual', 20.00, 10.00, 2.00, 2026),
                ('c0000000-0000-0000-0000-000000000104', 'a0000000-0000-0000-0000-000000000102', 'sick', 10.00, 2.00, 0.00, 2026),
                ('c0000000-0000-0000-0000-000000000105', 'a0000000-0000-0000-0000-000000000103', 'annual', 18.00, 4.00, 0.00, 2026);
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO it_assets (id, employee_id, asset_tag, device_type, make_model, serial_number, assigned_date, condition_status)
                VALUES 
                ('d0000000-0000-0000-0000-000000000102', 'a0000000-0000-0000-0000-000000000102', 'LT-8821', 'laptop', 'Lenovo ThinkPad T14', 'SN-994821', '2022-06-05', 'active'),
                ('d0000000-0000-0000-0000-000000000103', 'a0000000-0000-0000-0000-000000000103', 'LT-7740', 'laptop', 'Dell Latitude 5420', 'SN-774012', '2023-01-15', 'active');
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO it_tickets (id, employee_id, ticket_number, title, description, category, priority, status)
                VALUES 
                ('e0000000-0000-0000-0000-000000000102', 'a0000000-0000-0000-0000-000000000102', 'IT-1042', 'VPN Disconnects', 'VPN drops hourly', 'network', 'medium', 'open'),
                ('e0000000-0000-0000-0000-000000000103', 'a0000000-0000-0000-0000-000000000103', 'IT-1043', 'Monitor flicker', 'External display flickers', 'hardware', 'low', 'in_progress');
                """
            )
        )
        conn.commit()

    manager = DatabaseManager(database_url="sqlite:///:memory:")
    manager._engine = engine
    set_db_manager(manager)

    yield manager

    set_db_manager(None)
    manager.dispose()


# =============================================================================
# 1. Authentication Tests (A through F)
# =============================================================================
def test_a_missing_identity_header():
    """Test A: Missing X-Internal-Identity header returns 401 Unauthorized."""
    app = create_mcp_app()
    client = TestClient(app)
    response = client.post("/mcp", headers={"X-Internal-Signature": "dummy-sig"})
    assert response.status_code == 401
    assert "Missing required" in response.text


def test_b_missing_signature_header():
    """Test B: Missing X-Internal-Signature header returns 401 Unauthorized."""
    app = create_mcp_app()
    client = TestClient(app)
    identity_json = json.dumps({"user_id": "b102", "employee_number": "E102", "role": "employee"})
    response = client.post("/mcp", headers={"X-Internal-Identity": identity_json})
    assert response.status_code == 401
    assert "Missing required" in response.text


def test_c_invalid_signature():
    """Test C: Invalid/forged HMAC signature returns 401 Unauthorized."""
    app = create_mcp_app()
    client = TestClient(app)
    identity_json = json.dumps({"user_id": "b102", "employee_number": "E102", "role": "employee"})
    response = client.post(
        "/mcp",
        headers={
            "X-Internal-Identity": identity_json,
            "X-Internal-Signature": "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff",
        },
    )
    assert response.status_code == 401
    assert "Invalid HMAC signature" in response.text


def test_d_tampered_payload():
    """Test D: Modifying payload after signature generation returns 401 Unauthorized."""
    secret = get_mcp_settings().INTERNAL_MCP_SECRET
    original_id = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    headers = create_internal_auth_headers(original_id, secret=secret)

    # Tamper payload: change E102 to E101 (escalation attempt) while keeping signature
    tampered_identity = json.dumps({"user_id": "b102", "employee_number": "E101", "role": "hr_admin"})
    headers["X-Internal-Identity"] = tampered_identity

    app = create_mcp_app()
    client = TestClient(app)
    response = client.post("/mcp", headers=headers)
    assert response.status_code == 401
    assert "Invalid HMAC signature" in response.text


def test_e_valid_identity_and_signature():
    """Test E: Valid identity and signature passes middleware and reaches server endpoint."""
    secret = get_mcp_settings().INTERNAL_MCP_SECRET
    caller = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    headers = create_internal_auth_headers(caller, secret=secret)

    async def dummy_endpoint(scope, receive, send):
        cur = get_current_caller()
        resp = JSONResponse({"status": "authenticated", "employee_number": cur.employee_number})
        await resp(scope, receive, send)

    app = HMACAuthMiddleware(dummy_endpoint, secret=secret)
    client = TestClient(app)
    response = client.post("/mcp", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "authenticated"
    assert response.json()["employee_number"] == "E102"


def test_f_fail_closed_on_missing_secret():
    """Test F: Fail closed when INTERNAL_MCP_SECRET is empty or whitespace."""
    caller = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    headers = create_internal_auth_headers(caller, secret="some-secret")

    # App initialized with empty secret
    app_no_secret = create_mcp_app(secret="")
    client = TestClient(app_no_secret)
    response = client.post("/mcp", headers=headers)
    assert response.status_code == 401
    assert "Server authentication configuration failure" in response.text


# =============================================================================
# 2. Authorization Tests (G through R)
# =============================================================================
def test_g_employee_self_service_profile():
    """Test G: Bob (E102, employee) requesting E102 profile succeeds."""
    token = set_current_caller(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    )
    try:
        res = get_employee_profile_handler("E102")
        assert res["found"] is True
        assert res["employee"]["employee_number"] == "E102"
        assert res["employee"]["first_name"] == "Bob"
    finally:
        reset_current_caller(token)


def test_h_employee_self_service_leave():
    """Test H: Bob (E102, employee) requesting E102 leave balances succeeds."""
    token = set_current_caller(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    )
    try:
        res = get_employee_leave_balances_handler("E102")
        assert res["found"] is True
        assert res["employee_number"] == "E102"
        assert len(res["balances"]) == 2
    finally:
        reset_current_caller(token)


def test_i_employee_self_service_assets():
    """Test I: Bob (E102, employee) requesting E102 assigned assets succeeds."""
    token = set_current_caller(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    )
    try:
        res = get_employee_assigned_assets_handler("E102")
        assert res["found"] is True
        assert res["employee_number"] == "E102"
        assert len(res["assets"]) == 1
        assert res["assets"][0]["asset_tag"] == "LT-8821"
    finally:
        reset_current_caller(token)


def test_j_employee_self_service_tickets():
    """Test J: Bob (E102, employee) requesting E102 IT tickets succeeds."""
    token = set_current_caller(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    )
    try:
        res = get_employee_it_tickets_handler("E102")
        assert res["found"] is True
        assert res["employee_number"] == "E102"
        assert len(res["tickets"]) == 1
        assert res["tickets"][0]["ticket_number"] == "IT-1042"
    finally:
        reset_current_caller(token)


def test_k_employee_peer_access_profile_denied():
    """Test K: Bob (E102, employee) requesting Carol's (E103) profile is denied."""
    token = set_current_caller(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    )
    try:
        with pytest.raises(MCPAuthorizationError) as exc_info:
            get_employee_profile_handler("E103")
        assert "Forbidden" in str(exc_info.value)
        assert "E102" in str(exc_info.value)
        assert "E103" in str(exc_info.value)
    finally:
        reset_current_caller(token)


def test_l_employee_peer_access_leave_denied():
    """Test L: Bob (E102, employee) requesting Carol's (E103) leave balances is denied."""
    token = set_current_caller(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    )
    try:
        with pytest.raises(MCPAuthorizationError) as exc_info:
            get_employee_leave_balances_handler("E103")
        assert "Forbidden" in str(exc_info.value)
    finally:
        reset_current_caller(token)


def test_m_employee_peer_access_assets_denied():
    """Test M: Bob (E102, employee) requesting Carol's (E103) assigned assets is denied."""
    token = set_current_caller(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    )
    try:
        with pytest.raises(MCPAuthorizationError) as exc_info:
            get_employee_assigned_assets_handler("E103")
        assert "Forbidden" in str(exc_info.value)
    finally:
        reset_current_caller(token)


def test_n_employee_peer_access_tickets_denied():
    """Test N: Bob (E102, employee) requesting Carol's (E103) IT tickets is denied."""
    token = set_current_caller(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    )
    try:
        with pytest.raises(MCPAuthorizationError) as exc_info:
            get_employee_it_tickets_handler("E103")
        assert "Forbidden" in str(exc_info.value)
    finally:
        reset_current_caller(token)


def test_o_hr_admin_access_any_employee_bob():
    """Test O: Alice (E101, hr_admin) accessing Bob's (E102) records is permitted."""
    token = set_current_caller(
        CallerIdentity(user_id="b101", employee_number="E101", role=UserRole.HR_ADMIN)
    )
    try:
        prof = get_employee_profile_handler("E102")
        assert prof["found"] is True
        leave = get_employee_leave_balances_handler("E102")
        assert leave["found"] is True
        assets = get_employee_assigned_assets_handler("E102")
        assert assets["found"] is True
        tickets = get_employee_it_tickets_handler("E102")
        assert tickets["found"] is True
    finally:
        reset_current_caller(token)


def test_p_hr_admin_access_another_employee_carol():
    """Test P: Alice (E101, hr_admin) accessing Carol's (E103) records is permitted."""
    token = set_current_caller(
        CallerIdentity(user_id="b101", employee_number="E101", role=UserRole.HR_ADMIN)
    )
    try:
        prof = get_employee_profile_handler("E103")
        assert prof["found"] is True
        leave = get_employee_leave_balances_handler("E103")
        assert leave["found"] is True
        assets = get_employee_assigned_assets_handler("E103")
        assert assets["found"] is True
        tickets = get_employee_it_tickets_handler("E103")
        assert tickets["found"] is True
    finally:
        reset_current_caller(token)


def test_q_missing_caller_context_denied():
    """Test Q: Calling tool handlers directly without caller context raises MCPAuthorizationError."""
    # Ensure caller identity is None
    assert caller_identity_var.get() is None

    with pytest.raises(MCPAuthorizationError) as exc_info:
        get_employee_profile_handler("E102")
    assert "Missing verified caller identity" in str(exc_info.value)


def test_r_argument_override_prevention():
    """Test R: Caller cannot circumvent authorization by passing different employee_number argument."""
    token = set_current_caller(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    )
    try:
        # Caller claims identity E102, passes E101 (Alice) in tool arguments
        with pytest.raises(MCPAuthorizationError) as exc_info:
            get_employee_profile_handler("E101")
        assert "Forbidden" in str(exc_info.value)
    finally:
        reset_current_caller(token)


# =============================================================================
# 3. Context Isolation Tests (S and T)
# =============================================================================
def test_s_concurrent_requests_isolated():
    """Test S: Concurrent requests with different identities do not leak across async contexts."""
    results = {}

    async def worker(emp_no: str, role: UserRole):
        caller = CallerIdentity(user_id=f"u_{emp_no}", employee_number=emp_no, role=role)
        tok = set_current_caller(caller)
        try:
            # Yield control to allow interleaving
            await asyncio.sleep(0.01)
            current = get_current_caller()
            results[emp_no] = current.employee_number if current else None
        finally:
            reset_current_caller(tok)

    async def _run():
        await asyncio.gather(
            worker("E102", UserRole.EMPLOYEE),
            worker("E103", UserRole.EMPLOYEE),
            worker("E101", UserRole.HR_ADMIN),
        )

    asyncio.run(_run())

    assert results["E102"] == "E102"
    assert results["E103"] == "E103"
    assert results["E101"] == "E101"


def test_t_context_reset_after_request():
    """Test T: Caller identity is completely reset after request completes."""
    assert caller_identity_var.get() is None

    secret = get_mcp_settings().INTERNAL_MCP_SECRET
    caller = CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE)
    headers = create_internal_auth_headers(caller, secret=secret)

    async def dummy_endpoint(scope, receive, send):
        resp = JSONResponse({"ok": True})
        await resp(scope, receive, send)

    app = HMACAuthMiddleware(dummy_endpoint, secret=secret)
    client = TestClient(app)
    response = client.post("/mcp", headers=headers)
    assert response.status_code == 200

    # Verify context variable is reset and None outside the request
    assert caller_identity_var.get() is None


# =============================================================================
# 4. Protocol Integration Tests (U through X)
# =============================================================================
def test_u_protocol_handshake_with_valid_auth():
    """Test U: Streamable HTTP handshake succeeds with valid signed auth headers."""
    import uvicorn
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    port = find_free_port()
    server = create_mcp_server()
    app = create_mcp_app(server=server)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    uvi_server = uvicorn.Server(config)

    thread = threading.Thread(target=uvi_server.run, daemon=True)
    thread.start()

    deadline = time.time() + 5.0
    ready = False
    while time.time() < deadline:
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/health/live", timeout=0.5)
            if resp.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.1)

    assert ready, "Server failed to start"

    auth_headers = create_internal_auth_headers(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE),
        secret=get_mcp_settings().INTERNAL_MCP_SECRET,
    )

    async def _handshake():
        url = f"http://127.0.0.1:{port}/mcp"
        async with httpx.AsyncClient(headers=auth_headers) as http_client:
            async with streamable_http_client(url, http_client=http_client) as streams:
                read_stream, write_stream = streams[0], streams[1]
                async with ClientSession(read_stream, write_stream) as session:
                    res = await session.initialize()
                    assert res.capabilities is not None

    try:
        asyncio.run(_handshake())
    finally:
        uvi_server.should_exit = True
        thread.join(timeout=3.0)


def test_v_protocol_tools_list_authenticated():
    """Test V: Authenticated ClientSession discovers all four approved employee tools."""
    import uvicorn
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    port = find_free_port()
    server = create_mcp_server()
    app = create_mcp_app(server=server)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    uvi_server = uvicorn.Server(config)

    thread = threading.Thread(target=uvi_server.run, daemon=True)
    thread.start()

    deadline = time.time() + 5.0
    ready = False
    while time.time() < deadline:
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/health/live", timeout=0.5)
            if resp.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.1)

    assert ready, "Server failed to start"

    auth_headers = create_internal_auth_headers(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE),
        secret=get_mcp_settings().INTERNAL_MCP_SECRET,
    )

    async def _list_tools():
        url = f"http://127.0.0.1:{port}/mcp"
        async with httpx.AsyncClient(headers=auth_headers) as http_client:
            async with streamable_http_client(url, http_client=http_client) as streams:
                read_stream, write_stream = streams[0], streams[1]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_res = await session.list_tools()
                    names = {t.name for t in tools_res.tools}
                    assert names == {
                        "get_employee_profile",
                        "get_employee_leave_balances",
                        "get_employee_assigned_assets",
                        "get_employee_it_tickets",
                    }

    try:
        asyncio.run(_list_tools())
    finally:
        uvi_server.should_exit = True
        thread.join(timeout=3.0)


def test_w_protocol_tool_call_self_service_authenticated():
    """Test W: Authenticated ClientSession calls get_employee_profile for Bob E102."""
    import uvicorn
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    port = find_free_port()
    server = create_mcp_server()
    app = create_mcp_app(server=server)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    uvi_server = uvicorn.Server(config)

    thread = threading.Thread(target=uvi_server.run, daemon=True)
    thread.start()

    deadline = time.time() + 5.0
    ready = False
    while time.time() < deadline:
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/health/live", timeout=0.5)
            if resp.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.1)

    assert ready, "Server failed to start"

    auth_headers = create_internal_auth_headers(
        CallerIdentity(user_id="b102", employee_number="E102", role=UserRole.EMPLOYEE),
        secret=get_mcp_settings().INTERNAL_MCP_SECRET,
    )

    async def _call_tool():
        url = f"http://127.0.0.1:{port}/mcp"
        async with httpx.AsyncClient(headers=auth_headers) as http_client:
            async with streamable_http_client(url, http_client=http_client) as streams:
                read_stream, write_stream = streams[0], streams[1]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    res = await session.call_tool("get_employee_profile", {"employee_number": "E102"})
                    data = json.loads(res.content[0].text)
                    assert data["found"] is True
                    assert data["employee"]["full_name"] == "Bob Jones"

    try:
        asyncio.run(_call_tool())
    finally:
        uvi_server.should_exit = True
        thread.join(timeout=3.0)


def test_x_protocol_unauthenticated_request_rejected():
    """Test X: Unauthenticated request to /mcp is rejected at HTTP layer with 401."""
    app = create_mcp_app()
    client = TestClient(app)
    response = client.post("/mcp", content=b"{}")
    assert response.status_code == 401
    assert "Missing required" in response.text
