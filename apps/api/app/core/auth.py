"""
Authentication, JWT session management, and live database caller verification.
Enforces Phase 0 Architecture v1.7.0 §4.1 contract:
1. Verifies signed HS256 JWT tokens with environment-driven secret.
2. Validates live database record (app_users JOIN employees) on every authenticated call.
3. Asserts account is active (is_active == True) and updates role/employee_number to live DB values.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
import logging
from typing import Any, Dict, Optional
import uuid

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings
from app.models.user import AppUserModel, EmployeeModel

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """Permitted user roles in the application."""
    EMPLOYEE = "employee"
    HR_ADMIN = "hr_admin"


class CallerIdentity(BaseModel):
    """
    Immutable caller identity structure for request execution and MCP propagation.
    Strictly forbids unexpected extra fields.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str = Field(..., description="UUID of the app_user account")
    employee_number: str = Field(..., description="Unique employee identifier (e.g. E101, E102)")
    role: UserRole = Field(..., description="Verified system authorization role ('employee' or 'hr_admin')")


# Global database session factory for authentication
_AUTH_SESSION_FACTORY = None


def get_auth_session_factory():
    """Returns the session factory for auth database queries."""
    global _AUTH_SESSION_FACTORY
    if _AUTH_SESSION_FACTORY is None:
        settings = get_settings()
        connect_args = {}
        pool_kwargs = {"pool_pre_ping": True}
        if "postgresql" in settings.DATABASE_URL:
            connect_args["connect_timeout"] = 10
            pool_kwargs["pool_size"] = 5
            pool_kwargs["max_overflow"] = 10
            pool_kwargs["pool_recycle"] = 300
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            **pool_kwargs,
        )
        _AUTH_SESSION_FACTORY = sessionmaker(bind=engine, expire_on_commit=False)
    return _AUTH_SESSION_FACTORY


def set_auth_session_factory(factory):
    """Injects a custom session factory (e.g., for SQLite in-memory tests)."""
    global _AUTH_SESSION_FACTORY
    _AUTH_SESSION_FACTORY = factory


def create_access_token(
    user_id: str,
    employee_number: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Creates a signed HS256 session JWT token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_EXPIRATION_MINUTES))

    payload = {
        "sub": str(user_id),
        "employee_number": str(employee_number),
        "role": str(role),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a session JWT token.
    Raises HTTPException(401) on expired, malformed, or invalid signatures.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as err:
        logger.warning("JWT verification failed: %s", err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    session_factory=Depends(get_auth_session_factory),
) -> CallerIdentity:
    """
    FastAPI dependency validating the caller's session token and live database state.
    Supports both Authorization: Bearer <token> headers and HttpOnly acme_access_token cookies.
    Enforces active account status and live role/employee mapping.
    """
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif request and "acme_access_token" in request.cookies:
        token = request.cookies.get("acme_access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject principal.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(str(user_id_str))
    except ValueError:
        user_uuid = str(user_id_str)

    # Perform live database lookup: app_users JOIN employees
    try:
        with session_factory() as session:
            stmt = (
                select(AppUserModel, EmployeeModel)
                .join(EmployeeModel, AppUserModel.employee_id == EmployeeModel.id)
                .where(AppUserModel.id == user_uuid)
            )
            result = session.execute(stmt).first()

            if not result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account not found.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_model, emp_model = result

            if not user_model.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is deactivated. Access revoked.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return CallerIdentity(
                user_id=str(user_model.id),
                employee_number=str(emp_model.employee_number),
                role=UserRole(str(user_model.role)),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Database error during live session authentication: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable.",
            headers={"WWW-Authenticate": "Bearer"},
        )
