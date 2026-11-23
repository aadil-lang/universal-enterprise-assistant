"""
Comprehensive FastMCP Transactional Tools Test Suite.
Verifies all 9 transactional capabilities, authorization boundaries,
and database persistence using in-memory SQLite fixture matching Acme schema.
"""

import datetime
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.auth.context import (
    MCPAuthorizationError,
    reset_current_caller,
    set_current_caller,
)
from app.auth.models import CallerIdentity, UserRole
from app.database.connection import DatabaseManager, set_db_manager
from app.tools.transaction_tools import (
    create_hr_service_request_handler,
    create_it_ticket_handler,
    cancel_leave_request_handler,
    get_all_requests_status_handler,
    get_equipment_request_status_handler,
    get_hr_request_status_handler,
    get_it_ticket_status_handler,
    get_leave_request_status_handler,
    get_reimbursement_status_handler,
    submit_equipment_request_handler,
    submit_leave_request_handler,
    submit_reimbursement_request_handler,
    update_employee_contact_handler,
    update_it_ticket_handler,
)


@pytest.fixture(autouse=True)
def setup_transactional_test_db():
    """Sets up an in-memory SQLite database populated with Acme seed data and transactional tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    with engine.connect() as conn:
        # Schema definition
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
                    employment_status TEXT NOT NULL DEFAULT 'active',
                    phone_number TEXT,
                    emergency_contact_name TEXT,
                    emergency_contact_phone TEXT,
                    personal_email TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                    available_days REAL NOT NULL DEFAULT 0.0,
                    fiscal_year INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                    condition_status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                    asset_tag TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE leave_requests (
                    id TEXT PRIMARY KEY,
                    request_number TEXT UNIQUE NOT NULL,
                    employee_id TEXT NOT NULL REFERENCES employees(id),
                    leave_type TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    days_requested REAL NOT NULL,
                    reason TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    cancellation_reason TEXT,
                    cancelled_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE it_ticket_updates (
                    id TEXT PRIMARY KEY,
                    ticket_id TEXT NOT NULL REFERENCES it_tickets(id),
                    employee_id TEXT NOT NULL REFERENCES employees(id),
                    update_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE reimbursement_requests (
                    id TEXT PRIMARY KEY,
                    request_number TEXT UNIQUE NOT NULL,
                    employee_id TEXT NOT NULL REFERENCES employees(id),
                    expense_category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    purchase_date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    vendor TEXT,
                    receipt_filename TEXT,
                    status TEXT NOT NULL DEFAULT 'submitted',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE hr_service_requests (
                    id TEXT PRIMARY KEY,
                    request_number TEXT UNIQUE NOT NULL,
                    employee_id TEXT NOT NULL REFERENCES employees(id),
                    service_category TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    recipient_details TEXT,
                    additional_details TEXT,
                    status TEXT NOT NULL DEFAULT 'submitted',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE equipment_requests (
                    id TEXT PRIMARY KEY,
                    request_number TEXT UNIQUE NOT NULL,
                    employee_id TEXT NOT NULL REFERENCES employees(id),
                    equipment_type TEXT NOT NULL,
                    specifications TEXT,
                    business_justification TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'submitted',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE employee_contact_audit (
                    id TEXT PRIMARY KEY,
                    employee_id TEXT NOT NULL REFERENCES employees(id),
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                ('a0000000-0000-0000-0000-000000000103', 'E103', 'Carol', 'Davis', 'carol@acme.com', 'Marketing Specialist', 'Marketing', '2023-01-10', 'active');
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO leave_balances (id, employee_id, leave_type, accrued_days, used_days, pending_days, available_days, fiscal_year)
                VALUES 
                ('c0000000-0000-0000-0000-000000000103', 'a0000000-0000-0000-0000-000000000102', 'annual', 20.0, 10.0, 2.0, 8.0, 2026),
                ('c0000000-0000-0000-0000-000000000104', 'a0000000-0000-0000-0000-000000000102', 'sick', 10.0, 2.0, 0.0, 8.0, 2026),
                ('c0000000-0000-0000-0000-000000000105', 'a0000000-0000-0000-0000-000000000103', 'annual', 18.0, 4.0, 0.0, 14.0, 2026);
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO it_assets (id, employee_id, asset_tag, device_type, make_model, serial_number, assigned_date, condition_status)
                VALUES 
                ('d0000000-0000-0000-0000-000000000101', 'a0000000-0000-0000-0000-000000000102', 'LT-8821', 'laptop', 'Lenovo ThinkPad T14', 'SN-994821', '2022-06-05', 'active');
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO it_tickets (id, employee_id, ticket_number, title, description, category, priority, status, asset_tag)
                VALUES 
                ('e0000000-0000-0000-0000-000000000101', 'a0000000-0000-0000-0000-000000000102', 'IT-1042', 'VPN connection timeout', 'VPN drops hourly', 'network', 'medium', 'open', 'LT-8821');
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


@pytest.fixture
def bob_caller():
    return CallerIdentity(
        user_id="b0000000-0000-0000-0000-000000000102",
        employee_number="E102",
        role=UserRole.EMPLOYEE,
    )


@pytest.fixture
def alice_caller():
    return CallerIdentity(
        user_id="b0000000-0000-0000-0000-000000000101",
        employee_number="E101",
        role=UserRole.HR_ADMIN,
    )


# =============================================================================
# 1. Capability 1: Apply for Leave
# =============================================================================
def test_submit_leave_request_success(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        res = submit_leave_request_handler(
            employee_number="E102",
            leave_type="annual",
            start_date="2026-12-10",
            end_date="2026-12-12",
            reason="Holiday vacation",
        )
        assert res["success"] is True
        assert res["request_number"].startswith("LV-2026-")
        assert res["status"] == "pending"
        assert res["days_requested"] == 2  # Dec 10 (Thu), Dec 11 (Fri) - Dec 12 is Saturday
        assert res["available_balance_before"] == 8.0
        assert res["projected_available_balance"] == 6.0
    finally:
        reset_current_caller(token)


def test_submit_leave_insufficient_balance(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        res = submit_leave_request_handler(
            employee_number="E102",
            leave_type="annual",
            start_date="2026-12-01",
            end_date="2026-12-21",
        )
        assert res["success"] is False
        assert "Insufficient leave balance" in res["error"]
    finally:
        reset_current_caller(token)


def test_submit_leave_overlapping_dates(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        res1 = submit_leave_request_handler(
            employee_number="E102",
            leave_type="annual",
            start_date="2026-12-10",
            end_date="2026-12-12",
        )
        assert res1["success"] is True

        res2 = submit_leave_request_handler(
            employee_number="E102",
            leave_type="annual",
            start_date="2026-12-11",
            end_date="2026-12-15",
        )
        assert res2["success"] is False
        assert "Overlapping leave request" in res2["error"]
    finally:
        reset_current_caller(token)


# =============================================================================
# 2. Capability 2: Raise IT Support Ticket
# =============================================================================
def test_create_it_ticket_success(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        res = create_it_ticket_handler(
            employee_number="E102",
            title="Broken laptop screen",
            description="Display panel cracked after travel.",
            category="hardware",
            priority="high",
            asset_tag="LT-8821",
        )
        assert res["success"] is True
        assert res["ticket_number"].startswith("IT-")
        assert res["status"] == "open"
        assert res["priority"] == "high"
    finally:
        reset_current_caller(token)


def test_create_it_ticket_invalid_priority(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        with pytest.raises(ValueError, match="Invalid priority"):
            create_it_ticket_handler(
                employee_number="E102",
                title="WiFi drop",
                description="Drops occasionally",
                category="network",
                priority="extreme_critical_bypass",
            )
    finally:
        reset_current_caller(token)


# =============================================================================
# 3. Capability 3: Reimbursement Requests
# =============================================================================
def test_submit_reimbursement_ergonomic_limit(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        # $350 exceeds $300 limit
        res = submit_reimbursement_request_handler(
            employee_number="E102",
            expense_category="ergonomic_stipend",
            amount=350.00,
            purchase_date="2026-11-15",
            description="Ergonomic desk",
        )
        assert res["success"] is False
        assert "exceeds the company ergonomic stipend limit of $300.00" in res["error"]

        # $250 is valid
        res_ok = submit_reimbursement_request_handler(
            employee_number="E102",
            expense_category="ergonomic_stipend",
            amount=250.00,
            purchase_date="2026-11-15",
            description="Ergonomic chair",
            vendor="Office Depot",
            receipt_filename="chair_receipt.pdf",
        )
        assert res_ok["success"] is True
        assert res_ok["request_number"].startswith("EXP-2026-")

        # Second submission of $50 is valid (cumulative total = $300.00)
        res_ok2 = submit_reimbursement_request_handler(
            employee_number="E102",
            expense_category="ergonomic_stipend",
            amount=50.00,
            purchase_date="2026-11-16",
            description="Ergonomic footrest",
        )
        assert res_ok2["success"] is True

        # Third submission of $20 exceeds cumulative $300 limit
        res_exceed = submit_reimbursement_request_handler(
            employee_number="E102",
            expense_category="ergonomic_stipend",
            amount=20.00,
            purchase_date="2026-11-17",
            description="Wrist pad",
        )
        assert res_exceed["success"] is False
        assert "exceeds your remaining ergonomic stipend limit" in res_exceed["error"]
    finally:
        reset_current_caller(token)


# =============================================================================
# 4. Capability 4: HR Service Requests
# =============================================================================
def test_create_hr_service_request(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        res = create_hr_service_request_handler(
            employee_number="E102",
            service_category="employment_verification_letter",
            purpose="Mortgage tenancy verification",
            recipient_details="First National Bank",
        )
        assert res["success"] is True
        assert res["request_number"].startswith("HR-2026-")
        assert res["status"] == "submitted"
    finally:
        reset_current_caller(token)


# =============================================================================
# 5. Capability 5: Check Request Status
# =============================================================================
def test_get_all_requests_status(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        submit_leave_request_handler("E102", "annual", "2026-12-10", "2026-12-11")
        submit_equipment_request_handler("E102", "monitor", "Dual display productivity")

        res = get_all_requests_status_handler("E102", "all")
        assert res["found"] is True
        assert res["total_requests"] >= 2
        # Includes the pre-seeded IT ticket and the 2 new requests
        categories = {r["category"] for r in res["requests"]}
        assert "leave" in categories
        assert "equipment" in categories
        assert "it_ticket" in categories
    finally:
        reset_current_caller(token)


# =============================================================================
# 6. Capability 6: Cancel Pending Leave Request
# =============================================================================
def test_cancel_leave_request(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        sub = submit_leave_request_handler("E102", "annual", "2026-12-10", "2026-12-11")
        req_no = sub["request_number"]

        cancel_res = cancel_leave_request_handler("E102", req_no, cancellation_reason="Changed plans")
        assert cancel_res["success"] is True
        assert cancel_res["status"] == "cancelled"

        # Check status reflects cancelled
        st = get_leave_request_status_handler("E102", request_number=req_no)
        assert st["found"] is True
        assert st["request"]["status"] == "cancelled"

        # Attempt to cancel again -> rejected
        cancel2 = cancel_leave_request_handler("E102", req_no)
        assert cancel2["success"] is False
        assert "cannot be cancelled because its current status is 'cancelled'" in cancel2["error"]
    finally:
        reset_current_caller(token)


def test_leave_balance_deduction_and_restoration_lifecycle(bob_caller):
    """
    Critical Acceptance Verification:
    1. Submitting leave reserves/deducts available days from leave_balances.
    2. Subsequent non-overlapping requests cannot exceed the updated available balance.
    3. Cancelling restores the balance exactly once.
    4. Duplicate cancellation attempts do not cause double-restoration.
    """
    token = set_current_caller(bob_caller)
    try:
        from app.tools.employee_tools import get_employee_leave_balances_handler

        # Initial available balance: 8.0 annual days
        bals0 = get_employee_leave_balances_handler("E102", fiscal_year=2026)
        annual0 = next(b for b in bals0["balances"] if b["leave_type"] == "annual")
        initial_avail = annual0["available_days"]
        assert initial_avail == 8.0

        # 1. Submit 5 working days: Dec 1 (Tue) to Dec 7 (Mon) = 5 working days
        sub = submit_leave_request_handler("E102", "annual", "2026-12-01", "2026-12-07")
        assert sub["success"] is True
        assert sub["days_requested"] == 5

        # Verify DB balance deducted
        bals1 = get_employee_leave_balances_handler("E102", fiscal_year=2026)
        annual1 = next(b for b in bals1["balances"] if b["leave_type"] == "annual")
        assert annual1["available_days"] == 3.0
        assert annual1["pending_days"] == 7.0  # 2 pre-seeded + 5 new

        # 2. Attempt a second request for 5 working days on non-overlapping dates: Dec 15 to Dec 21
        sub2 = submit_leave_request_handler("E102", "annual", "2026-12-15", "2026-12-21")
        assert sub2["success"] is False
        assert "Insufficient leave balance" in sub2["error"]

        # 3. Cancel the first request -> balance restored
        cancel = cancel_leave_request_handler("E102", sub["request_number"])
        assert cancel["success"] is True

        bals2 = get_employee_leave_balances_handler("E102", fiscal_year=2026)
        annual2 = next(b for b in bals2["balances"] if b["leave_type"] == "annual")
        assert annual2["available_days"] == 8.0
        assert annual2["pending_days"] == 2.0

        # 4. Attempt second cancellation -> rejected, no extra restoration
        cancel_dup = cancel_leave_request_handler("E102", sub["request_number"])
        assert cancel_dup["success"] is False

        bals3 = get_employee_leave_balances_handler("E102", fiscal_year=2026)
        annual3 = next(b for b in bals3["balances"] if b["leave_type"] == "annual")
        assert annual3["available_days"] == 8.0
    finally:
        reset_current_caller(token)


# =============================================================================
# 7. Capability 7: Update IT Ticket
# =============================================================================
def test_update_it_ticket(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        upd = update_it_ticket_handler(
            employee_number="E102",
            ticket_number="IT-1042",
            update_text_val="VPN also disconnects when switching from WiFi to Ethernet.",
        )
        assert upd["success"] is True

        st = get_it_ticket_status_handler("E102", ticket_number="IT-1042")
        assert st["found"] is True
        assert len(st["ticket"]["updates"]) == 1
        assert "switching from WiFi to Ethernet" in st["ticket"]["updates"][0]["update_text"]
    finally:
        reset_current_caller(token)


# =============================================================================
# 8. Capability 8: Equipment Requisition
# =============================================================================
def test_submit_equipment_request(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        res = submit_equipment_request_handler(
            employee_number="E102",
            equipment_type="monitor",
            business_justification="Need external monitor for software development",
            specifications="27 inch 4K display",
        )
        assert res["success"] is True
        assert res["request_number"].startswith("EQ-2026-")
        assert res["status"] == "submitted"
    finally:
        reset_current_caller(token)


# =============================================================================
# 9. Capability 9: Update Contact Information
# =============================================================================
def test_update_contact_permitted_field(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        res = update_employee_contact_handler(
            employee_number="E102",
            field_name="emergency_contact_phone",
            new_value="+1-555-0199",
        )
        assert res["success"] is True
        assert res["new_value"] == "+1-555-0199"
    finally:
        reset_current_caller(token)


def test_update_contact_protected_field_rejected(bob_caller):
    token = set_current_caller(bob_caller)
    try:
        with pytest.raises(ValueError, match="protected and cannot be modified"):
            update_employee_contact_handler(
                employee_number="E102",
                field_name="salary",
                new_value="180000",
            )
        with pytest.raises(ValueError, match="protected and cannot be modified"):
            update_employee_contact_handler(
                employee_number="E102",
                field_name="role",
                new_value="hr_admin",
            )
        with pytest.raises(ValueError, match="protected and cannot be modified"):
            update_employee_contact_handler(
                employee_number="E102",
                field_name="corporate_email",
                new_value="bob.new@acme.com",
            )
    finally:
        reset_current_caller(token)


# =============================================================================
# 10. Security & Authorization Boundary Tests (Section 10)
# =============================================================================
def test_peer_access_boundary_enforced(bob_caller):
    """Bob (E102) cannot submit transactions on behalf of Carol (E103)."""
    token = set_current_caller(bob_caller)
    try:
        with pytest.raises(MCPAuthorizationError, match="not authorized|Forbidden"):
            submit_leave_request_handler("E103", "annual", "2026-12-10", "2026-12-11")
    finally:
        reset_current_caller(token)


def test_hr_admin_cross_employee_permission(alice_caller):
    """Alice (HR Admin) can access employee records and status."""
    token = set_current_caller(alice_caller)
    try:
        res = get_all_requests_status_handler("E102", "all")
        assert res["found"] is True
    finally:
        reset_current_caller(token)
