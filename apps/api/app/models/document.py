"""
SQLAlchemy ORM model for the documents table.
Maps the approved Phase 0 v1.7.0 document registry schema.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CHAR, INT, VARCHAR, DateTime, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    filename: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    file_path: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    category: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="pending")
    checksum_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    chunk_count: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )
    indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("NOW()"),
    )

    __table_args__ = (
        CheckConstraint("category IN ('HR', 'IT')", name="chk_doc_category"),
        CheckConstraint("status IN ('pending', 'indexing', 'indexed', 'failed')", name="chk_doc_status"),
    )
