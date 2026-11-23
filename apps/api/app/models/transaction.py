"""
SQLAlchemy ORM models for transactional enterprise assistant workflows.
Maps normalized PostgreSQL 16 transactional schema for all 9 capabilities:
- Leave requests & cancellation
- IT ticket updates history
- Expense & reimbursement requests
- HR service requests
- Equipment requests
- Employee contact audit
- Transaction confirmation & idempotency records
- Transaction audit events
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    CHAR,
    DATE,
    NUMERIC,
    VARCHAR,
    DateTime,
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.document import Base


class LeaveBalanceModel(Base):
    __tablename__ = "leave_balances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    leave_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    accrued_days: Mapped[float] = mapped_column(NUMERIC(5, 2), nullable=False, default=0.0)
    used_days: Mapped[float] = mapped_column(NUMERIC(5, 2), nullable=False, default=0.0)
    pending_days: Mapped[float] = mapped_column(NUMERIC(5, 2), nullable=False, default=0.0)
    available_days: Mapped[float] = mapped_column(NUMERIC(5, 2), nullable=False, default=0.0)
    fiscal_year: Mapped[int] = mapped_column(nullable=False)
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


class ITAssetModel(Base):
    __tablename__ = "it_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    asset_tag: Mapped[str] = mapped_column(VARCHAR(64), unique=True, nullable=False)
    device_type: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    make_model: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    serial_number: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    assigned_date: Mapped[Optional[date]] = mapped_column(DATE, nullable=True)
    condition_status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )


class ITTicketModel(Base):
    __tablename__ = "it_tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticket_number: Mapped[str] = mapped_column(VARCHAR(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    priority: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="open")
    asset_tag: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
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


class LeaveRequestModel(Base):
    __tablename__ = "leave_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    request_number: Mapped[str] = mapped_column(VARCHAR(32), unique=True, nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    leave_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)  # 'annual' or 'sick'
    start_date: Mapped[date] = mapped_column(DATE, nullable=False)
    end_date: Mapped[date] = mapped_column(DATE, nullable=False)
    days_requested: Mapped[float] = mapped_column(NUMERIC(5, 2), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="pending")
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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


class ITTicketUpdateModel(Base):
    __tablename__ = "it_ticket_updates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("it_tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    update_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )


class ReimbursementRequestModel(Base):
    __tablename__ = "reimbursement_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    request_number: Mapped[str] = mapped_column(VARCHAR(32), unique=True, nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    expense_category: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    amount: Mapped[float] = mapped_column(NUMERIC(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(VARCHAR(8), nullable=False, default="USD")
    purchase_date: Mapped[date] = mapped_column(DATE, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    vendor: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    receipt_filename: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    receipt_path: Mapped[Optional[str]] = mapped_column(VARCHAR(512), nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="submitted")
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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


class HRServiceRequestModel(Base):
    __tablename__ = "hr_service_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    request_number: Mapped[str] = mapped_column(VARCHAR(32), unique=True, nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_category: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="submitted")
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


class EquipmentRequestModel(Base):
    __tablename__ = "equipment_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    request_number: Mapped[str] = mapped_column(VARCHAR(32), unique=True, nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_type: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    specifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_justification: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="submitted")
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


class EmployeeContactAuditModel(Base):
    __tablename__ = "employee_contact_audit"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )


class TransactionConfirmationModel(Base):
    __tablename__ = "transaction_confirmations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    confirmation_token: Mapped[str] = mapped_column(VARCHAR(64), unique=True, nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_type: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="awaiting_confirmation")
    idempotency_key: Mapped[Optional[str]] = mapped_column(VARCHAR(128), unique=True, nullable=True)
    executed_request_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TransactionAuditModel(Base):
    __tablename__ = "transaction_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    request_number: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )
