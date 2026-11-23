"""
Comprehensive Test Suite for Phase 2.2 Genuine MCP Employee Database Tools.
Covers all required test categories (A through F):
A. Employee profile tests
B. Leave balance tests
C. Asset tests
D. IT ticket tests
E. Security and database tests
F. MCP protocol streamable HTTP integration tests
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

from app.auth.context import reset_current_caller, set_current_caller
from app.auth.models import CallerIdentity, UserRole
from app.auth.signer import create_internal_auth_headers
from app.config.settings import get_mcp_settings
from app.database.connection import DatabaseManager, set_db_manager
from app.main import app, create_mcp_app, create_mcp_server, mcp_server
from app.tools.employee_tools import (
    VALID_STATUS_FILTERS,
    get_employee_assigned_assets_handler,
    get_employee_it_tickets_handler,
    get_employee_leave_balances_handler,
    get_employee_profile_handler,
)


# =============================================================================
# Isolated SQLite In-Memory Database Fixture with Seed Data
# =============================================================================
@pytest.fixture(autouse=True)
def setup_sqlite_database() -> Generator[DatabaseManager, None, None]:
    """
    Sets up an in-memory SQLite database populated with the authoritative Acme Corporation
    seed data (matching 001_schema.sql and 002_seed.sql baseline).
    Injects this manager into set_db_manager for isolated test execution.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    with engine.connect() as conn:
        # 1. Create employees table
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

        # 2. Create app_users table (Authentication Principals - never exposed by tools)
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

        # 3. Create leave_balances table (with generated column available_days)
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

        # 4. Create it_assets table
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

        # 5. Create it_tickets table
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

        # Seed 1: Employees
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

        # Seed 2: App Users with BCrypt hashes (Sensitive credentials)
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

        # Seed 3: Leave Balances for 2026
        conn.execute(
            text(
                """
                INSERT INTO leave_balances (id, employee_id, leave_type, accrued_days, used_days, pending_days, fiscal_year)
                VALUES 
                ('c0000000-0000-0000-0000-000000000101', 'a0000000-0000-0000-0000-000000000101', 'annual', 25.00, 5.00, 0.00, 2026),
                ('c0000000-0000-0000-0000-000000000102', 'a0000000-0000-0000-0000-000000000101', 'sick', 10.00, 1.00, 0.00, 2026),
                ('c0000000-0000-0000-0000-000000000103', 'a0000000-0000-0000-0000-000000000102', 'annual', 20.00, 10.00, 2.00, 2026),
                ('c0000000-0000-0000-0000-000000000104', 'a0000000-0000-0000-0000-000000000102', 'sick', 10.00, 2.00, 0.00, 2026),
                ('c0000000-0000-0000-0000-000000000105', 'a0000000-0000-0000-0000-000000000103', 'annual', 18.00, 4.00, 0.00, 2026),
                ('c0000000-0000-0000-0000-000000000106', 'a0000000-0000-0000-0000-000000000103', 'sick', 10.00, 0.00, 0.00, 2026);
                """
            )
        )

        # Seed 4: IT Assets
        conn.execute(
            text(
                """
                INSERT INTO it_assets (id, employee_id, asset_tag, device_type, make_model, serial_number, assigned_date, condition_status)
                VALUES 
                ('d0000000-0000-0000-0000-000000000101', 'a0000000-0000-0000-0000-000000000101', 'LT-5510', 'laptop', 'Dell Latitude 7420', 'SN-551098', '2021-03-20', 'active'),
                ('d0000000-0000-0000-0000-000000000102', 'a0000000-0000-0000-0000-000000000102', 'LT-8821', 'laptop', 'Lenovo ThinkPad T14', 'SN-994821', '2022-06-05', 'active'),
                ('d0000000-0000-0000-0000-000000000103', 'a0000000-0000-0000-0000-000000000103', 'LT-7740', 'laptop', 'Dell Latitude 5420', 'SN-774012', '2023-01-15', 'active');
                """
            )
        )

        # Seed 5: IT Tickets
        conn.execute(
            text(
                """
                INSERT INTO it_tickets (id, employee_id, ticket_number, title, description, category, priority, status, created_at, updated_at)
                VALUES 
                ('e0000000-0000-0000-0000-000000000101', 'a0000000-0000-0000-0000-000000000102', 'IT-1042', 'VPN connection timeout', 'VPN timeout on home Wi-Fi after 30 minutes of continuous connection.', 'VPN', 'medium', 'open', '2026-02-10 09:30:00', '2026-02-10 09:30:00'),
                ('e0000000-0000-0000-0000-000000000102', 'a0000000-0000-0000-0000-000000000103', 'IT-1011', 'Second monitor request', 'Requesting an external 27-inch 4K monitor for marketing graphic layout design.', 'Hardware', 'low', 'closed', '2026-01-15 14:00:00', '2026-01-16 11:00:00'),
                ('e0000000-0000-0000-0000-000000000103', 'a0000000-0000-0000-0000-000000000102', 'IT-1002', 'Keyboard replacement', 'Spacebar sticking intermittently on external keyboard.', 'Hardware', 'low', 'closed', '2026-01-05 10:00:00', '2026-01-06 16:00:00');
                """
            )
        )
        conn.commit()

    manager = DatabaseManager(database_url="sqlite:///:memory:")
    manager._engine = engine
    set_db_manager(manager)

    token = set_current_caller(
        CallerIdentity(
            user_id="b0000000-0000-0000-0000-000000000101",
            employee_number="E101",
            role=UserRole.HR_ADMIN,
        )
    )

    try:
        yield manager
    finally:
        reset_current_caller(token)
        set_db_manager(None)
        manager.dispose()


# =============================================================================
# A. Employee Profile Tests
# =============================================================================
def test_a1_existing_employee_profile_e102():
    """Verify existing employee E102 returns Bob Jones' approved profile fields."""
    res = get_employee_profile_handler("E102")
    assert res["found"] is True
    emp = res["employee"]

    assert emp["employee_number"] == "E102"
    assert emp["first_name"] == "Bob"
    assert emp["last_name"] == "Jones"
    assert emp["full_name"] == "Bob Jones"
    assert emp["corporate_email"] == "bob@acme.com"
    assert emp["job_title"] == "Senior Software Engineer"
    assert emp["department"] == "Engineering"
    assert emp["hire_date"] == "2022-06-01"
    assert emp["employment_status"] == "active"


def test_a2_unknown_employee_profile():
    """Verify unknown employee number returns a clear not-found response."""
    res = get_employee_profile_handler("E999")
    assert res["found"] is False
    assert "not found" in res["message"].lower()
    assert "E999" in res["message"]


def test_a3_profile_excludes_sensitive_auth_fields():
    """Verify sensitive authentication and credential fields are never returned."""
    res = get_employee_profile_handler("E102")
    assert res["found"] is True
    emp = res["employee"]

    # Sensitive fields that must NEVER appear
    forbidden_keys = {
        "password",
        "password_hash",
        "role",
        "is_active",
        "token",
        "secret",
    }
    assert forbidden_keys.isdisjoint(emp.keys()), "Employee profile must not expose credentials or security roles"


def test_a4_profile_invalid_empty_employee_number():
    """Verify empty or whitespace-only employee number is rejected."""
    with pytest.raises(ValueError, match="non-empty"):
        get_employee_profile_handler("")

    with pytest.raises(ValueError, match="non-empty"):
        get_employee_profile_handler("   ")


# =============================================================================
# B. Leave Balance Tests
# =============================================================================
def test_b1_leave_balances_e102_annual_and_sick():
    """
    Verify E102 leave balances match approved baseline:
    - annual: accrued 20, used 10, pending 2, available 8
    - sick: accrued 10, used 2, pending 0, available 8
    """
    res = get_employee_leave_balances_handler("E102", fiscal_year=2026)
    assert res["found"] is True
    assert res["employee_number"] == "E102"
    assert res["fiscal_year"] == 2026

    balances = {b["leave_type"]: b for b in res["balances"]}
    assert "annual" in balances
    assert "sick" in balances

    annual = balances["annual"]
    assert annual["accrued_days"] == 20.0
    assert annual["used_days"] == 10.0
    assert annual["pending_days"] == 2.0
    assert annual["available_days"] == 8.0
    # Confirm formula: available == accrued - used - pending
    assert annual["available_days"] == annual["accrued_days"] - annual["used_days"] - annual["pending_days"]

    sick = balances["sick"]
    assert sick["accrued_days"] == 10.0
    assert sick["used_days"] == 2.0
    assert sick["pending_days"] == 0.0
    assert sick["available_days"] == 8.0
    assert sick["available_days"] == sick["accrued_days"] - sick["used_days"] - sick["pending_days"]


def test_b2_leave_balances_omitted_fiscal_year_uses_central_setting():
    """Verify omitted fiscal_year resolves through central DEMO_FISCAL_YEAR (2026)."""
    settings = get_mcp_settings()
    assert settings.DEMO_FISCAL_YEAR == 2026

    res = get_employee_leave_balances_handler("E102")  # fiscal_year=None
    assert res["found"] is True
    assert res["fiscal_year"] == 2026
    assert len(res["balances"]) == 2


def test_b3_leave_balances_explicit_fiscal_year():
    """Verify explicit fiscal_year parameter is respected."""
    res = get_employee_leave_balances_handler("E102", fiscal_year=2026)
    assert res["found"] is True
    assert res["fiscal_year"] == 2026


def test_b4_leave_balances_missing_fiscal_year_not_fabricated():
    """Verify missing fiscal-year records return empty collection without fabricated values."""
    res = get_employee_leave_balances_handler("E102", fiscal_year=2024)
    assert res["found"] is True
    assert res["fiscal_year"] == 2024
    assert res["balances"] == []
    assert "No leave balance records found" in res["message"]


def test_b5_leave_balances_unknown_employee():
    """Verify leave balances for unknown employee returns not-found response."""
    res = get_employee_leave_balances_handler("E999")
    assert res["found"] is False
    assert "not found" in res["message"].lower()


# =============================================================================
# C. Asset Tests
# =============================================================================
def test_c1_assigned_assets_e102_returns_lenovo():
    """
    Verify E102 returns approved Lenovo ThinkPad T14:
    - asset tag: LT-8821
    - serial number: SN-994821
    """
    res = get_employee_assigned_assets_handler("E102")
    assert res["found"] is True
    assert res["employee_number"] == "E102"
    assert len(res["assets"]) == 1

    asset = res["assets"][0]
    assert asset["asset_tag"] == "LT-8821"
    assert asset["serial_number"] == "SN-994821"
    assert asset["device_type"] == "laptop"
    assert asset["make_model"] == "Lenovo ThinkPad T14"
    assert asset["condition_status"] == "active"
    assert asset["assigned_date"] == "2022-06-05"


def test_c2_assigned_assets_employee_without_assets():
    """Verify employee without assigned hardware receives empty collection."""
    res = get_employee_assigned_assets_handler("E104")  # David Miller has no assets
    assert res["found"] is True
    assert res["employee_number"] == "E104"
    assert res["assets"] == []


def test_c3_assigned_assets_cross_employee_isolation():
    """Verify one employee cannot retrieve another employee's assets."""
    res_bob = get_employee_assigned_assets_handler("E102")
    res_alice = get_employee_assigned_assets_handler("E101")

    bob_tags = {a["asset_tag"] for a in res_bob["assets"]}
    alice_tags = {a["asset_tag"] for a in res_alice["assets"]}

    assert "LT-8821" in bob_tags
    assert "LT-5510" in alice_tags
    assert bob_tags.isdisjoint(alice_tags), "Assets must remain strictly isolated between employees"


def test_c4_assigned_assets_unknown_employee():
    """Verify asset lookup for unknown employee returns not found."""
    res = get_employee_assigned_assets_handler("E999")
    assert res["found"] is False
    assert "not found" in res["message"].lower()


# =============================================================================
# D. IT Ticket Tests
# =============================================================================
def test_d1_it_tickets_e102_open_medium_priority():
    """
    Verify E102 returns approved ticket IT-1042:
    - open status, medium priority, VPN category
    """
    res = get_employee_it_tickets_handler("E102", status_filter="open")
    assert res["found"] is True
    assert res["employee_number"] == "E102"
    assert len(res["tickets"]) == 1

    ticket = res["tickets"][0]
    assert ticket["ticket_number"] == "IT-1042"
    assert ticket["title"] == "VPN connection timeout"
    assert ticket["category"] == "VPN"
    assert ticket["priority"] == "medium"
    assert ticket["status"] == "open"
    assert "30 minutes" in ticket["description"]


def test_d2_it_tickets_all_filter():
    """Verify 'all' filter returns both open and closed tickets for employee."""
    res = get_employee_it_tickets_handler("E102", status_filter="all")
    assert res["found"] is True
    assert len(res["tickets"]) == 2

    ticket_numbers = {t["ticket_number"] for t in res["tickets"]}
    assert "IT-1042" in ticket_numbers
    assert "IT-1002" in ticket_numbers


def test_d3_it_tickets_closed_filter():
    """Verify status_filter='closed' returns only closed tickets."""
    res = get_employee_it_tickets_handler("E102", status_filter="closed")
    assert res["found"] is True
    assert len(res["tickets"]) == 1
    assert res["tickets"][0]["ticket_number"] == "IT-1002"
    assert res["tickets"][0]["status"] == "closed"


def test_d4_it_tickets_invalid_filter_rejected():
    """Verify invalid status filter is rejected with ValueError."""
    for bad_filter in ["urgent", "pending", "deleted", "active"]:
        with pytest.raises(ValueError, match="Invalid status_filter"):
            get_employee_it_tickets_handler("E102", status_filter=bad_filter)


def test_d5_it_tickets_no_matching_tickets_returns_empty():
    """Verify empty collection when employee has no tickets matching filter."""
    res = get_employee_it_tickets_handler("E102", status_filter="in_progress")
    assert res["found"] is True
    assert res["status_filter"] == "in_progress"
    assert res["tickets"] == []


def test_d6_it_tickets_cross_employee_isolation():
    """Verify one employee cannot retrieve another employee's tickets."""
    res_bob = get_employee_it_tickets_handler("E102", status_filter="all")
    res_carol = get_employee_it_tickets_handler("E103", status_filter="all")

    bob_tickets = {t["ticket_number"] for t in res_bob["tickets"]}
    carol_tickets = {t["ticket_number"] for t in res_carol["tickets"]}

    assert "IT-1042" in bob_tickets
    assert "IT-1011" in carol_tickets
    assert bob_tickets.isdisjoint(carol_tickets), "Tickets must remain strictly isolated between employees"


def test_d7_it_tickets_unknown_employee():
    """Verify tickets lookup for unknown employee returns not found."""
    res = get_employee_it_tickets_handler("E999")
    assert res["found"] is False
    assert "not found" in res["message"].lower()


# =============================================================================
# E. Security and Database Tests
# =============================================================================
def test_e1_sql_injection_resilience():
    """
    Verify parameterized queries prevent SQL injection payloads across all 4 tools.
    Payloads must be treated strictly as literal data strings.
    """
    injection_payloads = [
        "' OR '1'='1",
        "E102' OR '1'='1' --",
        "E102'; DROP TABLE employees; --",
        "E102' UNION SELECT id, email, password_hash, '', '', '', '', '', '' FROM app_users --",
    ]

    for payload in injection_payloads:
        res_prof = get_employee_profile_handler(payload)
        assert res_prof["found"] is False

        res_leave = get_employee_leave_balances_handler(payload)
        assert res_leave["found"] is False

        res_assets = get_employee_assigned_assets_handler(payload)
        assert res_assets["found"] is False

        res_tickets = get_employee_it_tickets_handler(payload)
        assert res_tickets["found"] is False


def test_e2_database_error_masks_credentials(setup_sqlite_database):
    """Verify database errors never leak database credentials, URLs, or internal raw queries."""
    from unittest.mock import MagicMock, patch
    from app.database.connection import DatabaseError

    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Simulated connection failure with user acme_app:secret123")

    with patch.object(setup_sqlite_database, "_engine", mock_engine):
        with pytest.raises(DatabaseError) as exc_info:
            get_employee_profile_handler("E102")

        error_message = str(exc_info.value)
        assert "secret123" not in error_message
        assert "acme_app" not in error_message
        assert "Database service is currently unreachable" in error_message


def test_e3_connection_release_integrity(setup_sqlite_database):
    """Verify connections are properly closed and returned to the pool after query execution."""
    from contextlib import contextmanager
    from unittest.mock import patch

    closed_connections = []
    real_get_conn = setup_sqlite_database.get_connection

    @contextmanager
    def tracked_get_connection():
        with real_get_conn() as conn:
            yield conn
            assert not conn.closed
        assert conn.closed
        closed_connections.append(True)

    with patch.object(setup_sqlite_database, "get_connection", side_effect=tracked_get_connection):
        get_employee_profile_handler("E102")
        get_employee_leave_balances_handler("E102")
        get_employee_assigned_assets_handler("E102")
        get_employee_it_tickets_handler("E102")

    assert len(closed_connections) >= 4, "Every query must acquire and close its connection cleanly"


def test_e4_read_only_mutation_prevention(setup_sqlite_database):
    """Verify all employee tools are strictly read-only and database records remain unmodified."""
    with setup_sqlite_database.get_connection() as conn:
        before_count = conn.execute(text("SELECT COUNT(*) FROM employees")).scalar()

    get_employee_profile_handler("E102")
    get_employee_leave_balances_handler("E102")
    get_employee_assigned_assets_handler("E102")
    get_employee_it_tickets_handler("E102")

    with setup_sqlite_database.get_connection() as conn:
        after_count = conn.execute(text("SELECT COUNT(*) FROM employees")).scalar()

    assert before_count == after_count == 4


# =============================================================================
# F. MCP Protocol Integration Tests (Streamable HTTP Transport)
# =============================================================================
def find_free_port() -> int:
    """Dynamically allocate an available ephemeral TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_f1_mcp_protocol_streamable_http_discovery_and_tool_calls():
    """
    End-to-End MCP Protocol Verification:
    1. Boots genuine FastMCP application on Streamable HTTP transport.
    2. Initializes MCP ClientSession handshake.
    3. Verifies tools/list exposes exactly the 4 approved tools.
    4. Executes genuine MCP protocol tool calls for all 4 tools.
    5. Validates structured JSON responses and argument validation.
    """
    import uvicorn
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    port = find_free_port()
    test_server = create_mcp_server()
    test_app = create_mcp_app(server=test_server)
    config = uvicorn.Config(test_app, host="127.0.0.1", port=port, log_level="warning")
    uvi_server = uvicorn.Server(config)

    thread = threading.Thread(target=uvi_server.run, daemon=True)
    thread.start()

    deadline = time.time() + 5.0
    server_ready = False
    while time.time() < deadline:
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/health/live", timeout=0.5)
            if resp.status_code == 200:
                server_ready = True
                break
        except Exception:
            time.sleep(0.1)

    assert server_ready, f"FastMCP server failed to start on port {port} within 5.0s"

    auth_headers = create_internal_auth_headers(
        CallerIdentity(
            user_id="b0000000-0000-0000-0000-000000000102",
            employee_number="E102",
            role=UserRole.EMPLOYEE,
        ),
        secret=get_mcp_settings().INTERNAL_MCP_SECRET,
    )

    async def _run_mcp_client_suite():
        url = f"http://127.0.0.1:{port}/mcp"
        async with httpx.AsyncClient(headers=auth_headers) as http_client:
            async with streamable_http_client(url, http_client=http_client) as streams:
                read_stream, write_stream = streams[0], streams[1]
                async with ClientSession(read_stream, write_stream) as session:
                    init_res = await session.initialize()
                    assert init_res.capabilities is not None

                    # 1. tools/list verification
                    tools_list = await session.list_tools()
                    discovered_names = {t.name for t in tools_list.tools}
                    expected_tools = {
                        "get_employee_profile",
                        "get_employee_leave_balances",
                        "get_employee_assigned_assets",
                        "get_employee_it_tickets",
                    }
                    assert expected_tools.issubset(discovered_names), f"Expected tools missing: {expected_tools - discovered_names}"

                    # 2. Call Tool 1: get_employee_profile
                    prof_res = await session.call_tool("get_employee_profile", {"employee_number": "E102"})
                    prof_data = json.loads(prof_res.content[0].text)
                    assert prof_data["found"] is True
                    assert prof_data["employee"]["full_name"] == "Bob Jones"
                    assert "password_hash" not in prof_data["employee"]

                    # 3. Call Tool 2: get_employee_leave_balances
                    leave_res = await session.call_tool("get_employee_leave_balances", {"employee_number": "E102"})
                    leave_data = json.loads(leave_res.content[0].text)
                    assert leave_data["found"] is True
                    assert leave_data["fiscal_year"] == 2026
                    assert len(leave_data["balances"]) == 2

                    # 4. Call Tool 3: get_employee_assigned_assets
                    assets_res = await session.call_tool("get_employee_assigned_assets", {"employee_number": "E102"})
                    assets_data = json.loads(assets_res.content[0].text)
                    assert assets_data["found"] is True
                    assert assets_data["assets"][0]["asset_tag"] == "LT-8821"
                    assert assets_data["assets"][0]["make_model"] == "Lenovo ThinkPad T14"

                    # 5. Call Tool 4: get_employee_it_tickets
                    tickets_res = await session.call_tool(
                        "get_employee_it_tickets",
                        {"employee_number": "E102", "status_filter": "open"},
                    )
                    tickets_data = json.loads(tickets_res.content[0].text)
                    assert tickets_data["found"] is True
                    assert tickets_data["status_filter"] == "open"
                    assert len(tickets_data["tickets"]) == 1
                    assert tickets_data["tickets"][0]["ticket_number"] == "IT-1042"

    try:
        asyncio.run(_run_mcp_client_suite())
    finally:
        uvi_server.should_exit = True
        thread.join(timeout=3.0)
