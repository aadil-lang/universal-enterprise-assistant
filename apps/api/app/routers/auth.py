"""
Authentication router providing login and user identity endpoints.
Enforces Phase 0 Architecture v1.7.0 §4.1:
- Validates user credentials via bcrypt against app_users.
- Validates account active status (is_active == True).
- Returns signed HS256 JWT access token with role and employee claims.
"""

import logging
from typing import Optional
import uuid

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select

from app.config.settings import get_settings
from app.core.auth import (
    CallerIdentity,
    create_access_token,
    get_auth_session_factory,
    get_current_active_user,
)
from app.models.user import AppUserModel, EmployeeModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

# Verified bcrypt hash (cost factor 12) for timing attack defense on unknown email
DUMMY_BCRYPT_HASH = b"$2b$12$HR9/qU.SPsgPCEpBQjCzjuZwrjRv1a2RBB5URZtpeF73bvbOlQs86"


class LoginRequest(BaseModel):
    """User credentials for authentication."""
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., description="Corporate email address")
    password: str = Field(..., min_length=1, description="Account password")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v


class UserResponse(BaseModel):
    """Public user identity information."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique user account UUID")
    email: str = Field(..., description="Corporate email address")
    employee_number: str = Field(..., description="Employee identifier (e.g. E101, E102)")
    first_name: str = Field(..., description="Employee given name")
    last_name: str = Field(..., description="Employee surname")
    role: str = Field(..., description="System authorization role ('employee' or 'hr_admin')")


class LoginResponse(BaseModel):
    """Authentication response containing JWT bearer token and user metadata."""
    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(..., description="Signed HS256 JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="Authenticated user profile")


def _execute_login(
    request: LoginRequest,
    session_factory,
    response: Optional[Response] = None,
) -> LoginResponse:
    """Core login authentication logic."""
    email_clean = request.email.strip().lower()
    password_bytes = request.password.encode("utf-8")

    try:
        with session_factory() as session:
            stmt = (
                select(AppUserModel, EmployeeModel)
                .join(EmployeeModel, AppUserModel.employee_id == EmployeeModel.id)
                .where(func.lower(AppUserModel.email) == email_clean)
            )
            result = session.execute(stmt).first()

            if not result:
                logger.warning("Authentication failed: user '%s' not found.", email_clean)
                # Normalize timing against user enumeration using verified cost-12 dummy hash
                bcrypt.checkpw(password_bytes, DUMMY_BCRYPT_HASH)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_model, emp_model = result

            # Verify password hash using bcrypt
            stored_hash = user_model.password_hash.encode("utf-8")
            if not bcrypt.checkpw(password_bytes, stored_hash):
                logger.warning("Authentication failed: invalid password for '%s'.", email_clean)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check account active status
            if not user_model.is_active:
                logger.warning("Authentication failed: account '%s' is deactivated.", email_clean)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is deactivated. Access revoked.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Generate JWT token
            token = create_access_token(
                user_id=str(user_model.id),
                employee_number=str(emp_model.employee_number),
                role=str(user_model.role),
            )

            # Set HttpOnly, secure cookie for browser transport (DEF-03)
            if response is not None:
                settings = get_settings()
                max_age = int(getattr(settings, "JWT_EXPIRATION_MINUTES", 60) * 60)
                response.set_cookie(
                    key="acme_access_token",
                    value=token,
                    httponly=True,
                    samesite="lax",
                    secure=False,
                    max_age=max_age,
                    path="/",
                )

            return LoginResponse(
                access_token=token,
                token_type="bearer",
                user=UserResponse(
                    id=str(user_model.id),
                    email=str(user_model.email),
                    employee_number=str(emp_model.employee_number),
                    first_name=str(emp_model.first_name),
                    last_name=str(emp_model.last_name),
                    role=str(user_model.role),
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Database error during login authentication: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service temporarily unavailable.",
        )


@router.post(
    "/api/v1/auth/login",
    response_model=LoginResponse,
    summary="Authenticate user and issue JWT session token",
)
def login(
    request: LoginRequest,
    response: Response,
    session_factory=Depends(get_auth_session_factory),
) -> LoginResponse:
    """Authenticate employee or HR administrator using corporate email and password."""
    return _execute_login(request, session_factory, response=response)


@router.post(
    "/api/auth/login",
    response_model=LoginResponse,
    include_in_schema=False,
)
def login_api_alias(
    request: LoginRequest,
    response: Response,
    session_factory=Depends(get_auth_session_factory),
) -> LoginResponse:
    """Alias for /api/v1/auth/login."""
    return _execute_login(request, session_factory, response=response)


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    include_in_schema=False,
)
def login_auth_alias(
    request: LoginRequest,
    response: Response,
    session_factory=Depends(get_auth_session_factory),
) -> LoginResponse:
    """Alias for /api/v1/auth/login."""
    return _execute_login(request, session_factory, response=response)


@router.post(
    "/api/v1/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="Clear authenticated session and HttpOnly cookies",
)
@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def logout(response: Response):
    """Clears the HttpOnly access token cookie."""
    response.delete_cookie(key="acme_access_token", path="/")
    return {"detail": "Logged out successfully"}


def _execute_get_me(
    current_user: CallerIdentity,
    session_factory,
) -> UserResponse:
    """Core logic to retrieve current caller profile."""
    try:
        user_uuid = uuid.UUID(current_user.user_id)
    except ValueError:
        user_uuid = current_user.user_id

    try:
        with session_factory() as session:
            stmt = (
                select(AppUserModel, EmployeeModel)
                .join(EmployeeModel, AppUserModel.employee_id == EmployeeModel.id)
                .where(AppUserModel.id == user_uuid)
            )
            result = session.execute(stmt).first()
            if result:
                user_model, emp_model = result
                if not user_model.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User account is deactivated. Access revoked.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                return UserResponse(
                    id=str(user_model.id),
                    email=str(user_model.email),
                    employee_number=str(emp_model.employee_number),
                    first_name=str(emp_model.first_name),
                    last_name=str(emp_model.last_name),
                    role=str(user_model.role),
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Database lookup failed in get_me: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service temporarily unavailable.",
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User account not found.",
    )


@router.get(
    "/api/v1/auth/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
def get_me(
    current_user: CallerIdentity = Depends(get_current_active_user),
    session_factory=Depends(get_auth_session_factory),
) -> UserResponse:
    """Retrieve caller's profile and active session information."""
    return _execute_get_me(current_user, session_factory)


@router.get(
    "/api/auth/me",
    response_model=UserResponse,
    include_in_schema=False,
)
def get_me_alias(
    current_user: CallerIdentity = Depends(get_current_active_user),
    session_factory=Depends(get_auth_session_factory),
) -> UserResponse:
    """Alias for /api/v1/auth/me."""
    return _execute_get_me(current_user, session_factory)
