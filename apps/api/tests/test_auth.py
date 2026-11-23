"""
Comprehensive unit tests for API authentication and session management.
Direct unit testing of login and profile retrieval handlers:
- Successful employee authentication (Bob Jones E102)
- Successful HR admin authentication (Alice Smith E101)
- Correct password verification with bcrypt
- Invalid password rejection (HTTP 401)
- Unknown email rejection (HTTP 401)
- Deactivated account rejection (David Miller E104 -> HTTP 401)
- JWT token payload validation (claims sub, employee_number, role)
- Profile retrieval (get_me)
"""

from datetime import datetime
import uuid

import bcrypt
from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import CallerIdentity, UserRole, decode_access_token, set_auth_session_factory
from app.models.document import Base
from app.models.user import AppUserModel, EmployeeModel
from app.routers.auth import LoginRequest, _execute_get_me, _execute_login

BCRYPT_HASH = bcrypt.hashpw(b"Password123!", bcrypt.gensalt(4)).decode("utf-8")


@pytest.fixture
def auth_database():
    """Provides an isolated SQLite database populated with Acme seed accounts."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    set_auth_session_factory(factory)

    with factory() as session:
        # Seed Alice (HR Admin)
        alice_emp = EmployeeModel(
            id=uuid.UUID("a0000000-0000-0000-0000-000000000101"),
            employee_number="E101",
            first_name="Alice",
            last_name="Smith",
            corporate_email="alice@acme.com",
            job_title="HR Director",
            department="Human Resources",
            hire_date=datetime(2021, 3, 15).date(),
            employment_status="active",
        )
        alice_user = AppUserModel(
            id=uuid.UUID("b0000000-0000-0000-0000-000000000101"),
            email="alice@acme.com",
            password_hash=BCRYPT_HASH,
            role="hr_admin",
            employee_id=alice_emp.id,
            is_active=True,
        )

        # Seed Bob (Employee)
        bob_emp = EmployeeModel(
            id=uuid.UUID("a0000000-0000-0000-0000-000000000102"),
            employee_number="E102",
            first_name="Bob",
            last_name="Jones",
            corporate_email="bob@acme.com",
            job_title="Senior Software Engineer",
            department="Engineering",
            hire_date=datetime(2022, 6, 1).date(),
            employment_status="active",
        )
        bob_user = AppUserModel(
            id=uuid.UUID("b0000000-0000-0000-0000-000000000102"),
            email="bob@acme.com",
            password_hash=BCRYPT_HASH,
            role="employee",
            employee_id=bob_emp.id,
            is_active=True,
        )

        # Seed David (Deactivated Employee)
        david_emp = EmployeeModel(
            id=uuid.UUID("a0000000-0000-0000-0000-000000000104"),
            employee_number="E104",
            first_name="David",
            last_name="Miller",
            corporate_email="david@acme.com",
            job_title="Operations Specialist",
            department="Operations",
            hire_date=datetime(2020, 1, 10).date(),
            employment_status="terminated",
        )
        david_user = AppUserModel(
            id=uuid.UUID("b0000000-0000-0000-0000-000000000104"),
            email="david@acme.com",
            password_hash=BCRYPT_HASH,
            role="employee",
            employee_id=david_emp.id,
            is_active=False,  # DEACTIVATED
        )

        session.add_all([alice_emp, alice_user, bob_emp, bob_user, david_emp, david_user])
        session.commit()

    yield factory


def test_login_success_employee(auth_database):
    """Test successful employee login returning valid token and profile."""
    req = LoginRequest(email="bob@acme.com", password="Password123!")
    res = _execute_login(req, session_factory=auth_database)

    assert res.access_token is not None
    assert res.token_type == "bearer"
    assert res.user.email == "bob@acme.com"
    assert res.user.employee_number == "E102"
    assert res.user.role == "employee"

    # Decode and verify JWT claims
    payload = decode_access_token(res.access_token)
    assert payload["employee_number"] == "E102"
    assert payload["role"] == "employee"


def test_login_success_hr_admin(auth_database):
    """Test successful HR admin login."""
    req = LoginRequest(email="alice@acme.com", password="Password123!")
    res = _execute_login(req, session_factory=auth_database)

    assert res.user.role == "hr_admin"
    assert res.user.employee_number == "E101"

    payload = decode_access_token(res.access_token)
    assert payload["employee_number"] == "E101"
    assert payload["role"] == "hr_admin"


def test_login_invalid_password(auth_database):
    """Test rejection on incorrect password."""
    req = LoginRequest(email="bob@acme.com", password="WrongPassword!")
    with pytest.raises(HTTPException) as exc_info:
        _execute_login(req, session_factory=auth_database)
    assert exc_info.value.status_code == 401
    assert "Invalid email or password" in exc_info.value.detail


def test_login_unknown_user(auth_database):
    """Test rejection on nonexistent user."""
    req = LoginRequest(email="nonexistent@acme.com", password="Password123!")
    with pytest.raises(HTTPException) as exc_info:
        _execute_login(req, session_factory=auth_database)
    assert exc_info.value.status_code == 401
    assert "Invalid email or password" in exc_info.value.detail


def test_login_deactivated_user(auth_database):
    """Test rejection for deactivated user accounts."""
    req = LoginRequest(email="david@acme.com", password="Password123!")
    with pytest.raises(HTTPException) as exc_info:
        _execute_login(req, session_factory=auth_database)
    assert exc_info.value.status_code == 401
    assert "deactivated" in exc_info.value.detail.lower()


def test_get_me_success(auth_database):
    """Test retrieving caller profile with active session."""
    caller = CallerIdentity(
        user_id="b0000000-0000-0000-0000-000000000102",
        employee_number="E102",
        role=UserRole.EMPLOYEE,
    )
    profile = _execute_get_me(caller, session_factory=auth_database)
    assert profile.employee_number == "E102"
    assert profile.email == "bob@acme.com"
    assert profile.role == "employee"
