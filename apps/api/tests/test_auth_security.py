"""
Tests for Phase 5A.2, 5B.3, and 5B.5:
- 5A.2: Removal of test authentication bypasses, database verification, deactivated accounts rejected.
- 5B.3: Authentication failure timing normalization via cost-12 dummy bcrypt hash.
- 5B.5: Production secret enforcement and test environment safeguards.
"""

from datetime import datetime, date
import os
import time
import uuid
import bcrypt
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.settings import Settings
from app.core.auth import CallerIdentity, UserRole
from app.models.document import Base
from app.models.user import AppUserModel, EmployeeModel
from app.routers.auth import LoginRequest, _execute_get_me, _execute_login


@pytest.fixture
def auth_security_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as session:
        # Cost 12 hash for authentic test employee to match production cost
        pw_hash = bcrypt.hashpw(b"CorrectPassword123!", bcrypt.gensalt(12)).decode("utf-8")

        emp_active = EmployeeModel(
            id=uuid.UUID("a0000000-0000-0000-0000-000000000001"),
            employee_number="E001",
            first_name="Active",
            last_name="User",
            corporate_email="active@acme.com",
            job_title="Engineer",
            department="Engineering",
            hire_date=date(2022, 1, 1),
            employment_status="active",
        )
        user_active = AppUserModel(
            id=uuid.UUID("b0000000-0000-0000-0000-000000000001"),
            email="active@acme.com",
            password_hash=pw_hash,
            role="employee",
            employee_id=emp_active.id,
            is_active=True,
        )

        emp_deact = EmployeeModel(
            id=uuid.UUID("a0000000-0000-0000-0000-000000000002"),
            employee_number="E002",
            first_name="Deactivated",
            last_name="User",
            corporate_email="deactivated@acme.com",
            job_title="Analyst",
            department="Operations",
            hire_date=date(2020, 5, 10),
            employment_status="terminated",
        )
        user_deact = AppUserModel(
            id=uuid.UUID("b0000000-0000-0000-0000-000000000002"),
            email="deactivated@acme.com",
            password_hash=pw_hash,
            role="employee",
            employee_id=emp_deact.id,
            is_active=False,
        )

        session.add_all([emp_active, user_active, emp_deact, user_deact])
        session.commit()

    return factory


def test_login_timing_normalization_and_identical_error(auth_security_db):
    """
    Verifies that unknown email and incorrect password both perform bcrypt verification
    and return identical HTTP 401 error responses with no account existence leakage.
    """
    # 1. Nonexistent user
    req_unknown = LoginRequest(email="unknown_user@acme.com", password="SomePassword123!")
    t0 = time.perf_counter()
    with pytest.raises(HTTPException) as exc_unknown:
        _execute_login(req_unknown, session_factory=auth_security_db)
    unknown_duration = time.perf_counter() - t0

    assert exc_unknown.value.status_code == 401
    assert exc_unknown.value.detail == "Invalid email or password."
    # Timing should include cost-12 dummy bcrypt calculation (> 0.05s)
    assert unknown_duration > 0.05, f"Dummy hash timing was too fast: {unknown_duration:.4f}s"

    # 2. Existing user with wrong password
    req_wrong_pw = LoginRequest(email="active@acme.com", password="WrongPassword123!")
    t0 = time.perf_counter()
    with pytest.raises(HTTPException) as exc_wrong_pw:
        _execute_login(req_wrong_pw, session_factory=auth_security_db)
    wrong_pw_duration = time.perf_counter() - t0

    assert exc_wrong_pw.value.status_code == 401
    assert exc_wrong_pw.value.detail == "Invalid email or password."
    assert wrong_pw_duration > 0.05, f"Password hash timing was too fast: {wrong_pw_duration:.4f}s"

    # Both errors are strictly identical
    assert exc_unknown.value.detail == exc_wrong_pw.value.detail


def test_get_me_nonexistent_user_returns_404(auth_security_db):
    """Verifies that nonexistent database records in get_me return 404 rather than synthetic accounts."""
    ghost = CallerIdentity(
        user_id="b9999999-9999-9999-9999-999999999999",
        employee_number="E999",
        role=UserRole.EMPLOYEE,
    )
    with pytest.raises(HTTPException) as exc:
        _execute_get_me(ghost, session_factory=auth_security_db)
    assert exc.value.status_code == 404
    assert "User account not found" in exc.value.detail


def test_get_me_deactivated_user_returns_401(auth_security_db):
    """Verifies that deactivated database records in get_me return 401."""
    deact = CallerIdentity(
        user_id="b0000000-0000-0000-0000-000000000002",
        employee_number="E002",
        role=UserRole.EMPLOYEE,
    )
    with pytest.raises(HTTPException) as exc:
        _execute_get_me(deact, session_factory=auth_security_db)
    assert exc.value.status_code == 401
    assert "deactivated" in exc.value.detail.lower()


def test_settings_production_rejects_insecure_or_short_secrets():
    """Verifies that non-development environments strictly reject default or short secrets."""
    # Insecure default JWT secret
    with pytest.raises(ValidationError) as exc:
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="dev_insecure_jwt_secret_key_min_32_chars_12345",
            INTERNAL_MCP_SECRET="a" * 32,
            POSTGRES_PASSWORD="strong_random_password_2026!",
        )
    assert "JWT_SECRET_KEY" in str(exc.value)

    # Short JWT secret
    with pytest.raises(ValidationError) as exc:
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="too_short",
            INTERNAL_MCP_SECRET="a" * 32,
            POSTGRES_PASSWORD="strong_random_password_2026!",
        )
    assert "JWT_SECRET_KEY" in str(exc.value)

    # Insecure internal MCP secret
    with pytest.raises(ValidationError) as exc:
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="valid_strong_production_jwt_secret_key_32_chars!",
            INTERNAL_MCP_SECRET="dev_insecure_internal_mcp_hmac_secret_min_32",
            POSTGRES_PASSWORD="strong_random_password_2026!",
        )
    assert "INTERNAL_MCP_SECRET" in str(exc.value)

    # Default Postgres password
    with pytest.raises(ValidationError) as exc:
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="valid_strong_production_jwt_secret_key_32_chars!",
            INTERNAL_MCP_SECRET="valid_strong_internal_mcp_secret_key_32_chars!",
            POSTGRES_PASSWORD="acme_secure_dev_pw_2026",
        )
    assert "POSTGRES_PASSWORD" in str(exc.value)


def test_settings_production_accepts_valid_secrets():
    """Verifies that non-development environments accept valid custom secrets."""
    s = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="valid_strong_production_jwt_secret_key_32_chars!",
        INTERNAL_MCP_SECRET="valid_strong_internal_mcp_secret_key_32_chars!",
        POSTGRES_PASSWORD="StrongProductionPassword2026!",
    )
    assert s.APP_ENV == "production"


def test_settings_prevents_test_env_in_production(monkeypatch):
    """Verifies that APP_ENV='test' is rejected if production environment markers are present."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="test")
    assert "cannot be used in a production" in str(exc.value)
