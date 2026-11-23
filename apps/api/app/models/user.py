"""
SQLAlchemy ORM models for employees and app_users tables.
Maps the approved Phase 0 v1.7.0 and 001_schema.sql database foundation.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BOOLEAN,
    DATE,
    VARCHAR,
    DateTime,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.document import Base


class EmployeeModel(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    employee_number: Mapped[str] = mapped_column(VARCHAR(32), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    last_name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    corporate_email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    job_title: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    department: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    hire_date: Mapped[date] = mapped_column(DATE, nullable=False)
    employment_status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )

    user: Mapped[Optional["AppUserModel"]] = relationship("AppUserModel", back_populates="employee", uselist=False)

    __table_args__ = (
        Index("uq_employees_email_lower", text("LOWER(corporate_email)"), unique=True),
    )


class AppUserModel(Base):
    __tablename__ = "app_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    role: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="employee")
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )

    employee: Mapped[EmployeeModel] = relationship("EmployeeModel", back_populates="user")

    __table_args__ = (
        Index("uq_app_users_email_lower", text("LOWER(email)"), unique=True),
    )
