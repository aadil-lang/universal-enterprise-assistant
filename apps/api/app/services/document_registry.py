"""
Document Registry Repository.
Manages database persistence, lifecycle status transitions,
and duplicate detection in the PostgreSQL documents table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings
from app.models.document import DocumentModel


class DocumentRegistry:
    """Repository handling CRUD and status transitions for document records."""

    def __init__(self, session_factory=None):
        self.settings = get_settings()
        if session_factory:
            self.session_factory = session_factory
        else:
            from app.core.auth import get_auth_session_factory
            auth_factory = get_auth_session_factory()
            if auth_factory is not None:
                self.session_factory = auth_factory
            else:
                engine = create_engine(self.settings.DATABASE_URL, pool_pre_ping=True)
                self.session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def get_document_by_id(self, document_id: str) -> Optional[DocumentModel]:
        """Retrieves a document record by UUID."""
        with self.session_factory() as session:
            stmt = select(DocumentModel).where(DocumentModel.id == uuid.UUID(str(document_id)))
            return session.scalars(stmt).first()

    def get_document_by_checksum(self, checksum_sha256: str) -> Optional[DocumentModel]:
        """Retrieves an existing document by its SHA-256 content checksum."""
        with self.session_factory() as session:
            stmt = select(DocumentModel).where(DocumentModel.checksum_sha256 == checksum_sha256)
            return session.scalars(stmt).first()

    def get_document_by_filename(self, filename: str) -> Optional[DocumentModel]:
        """Retrieves an existing document by filename."""
        with self.session_factory() as session:
            stmt = select(DocumentModel).where(DocumentModel.filename == filename)
            return session.scalars(stmt).first()

    def register_or_update_document(
        self,
        filename: str,
        title: str,
        category: str,
        file_path: str,
        checksum_sha256: str,
    ) -> DocumentModel:
        """
        Registers a new document or updates an existing document with the same filename.
        Sets initial status to 'indexing'.
        """
        with self.session_factory() as session:
            stmt = select(DocumentModel).where(DocumentModel.filename == filename)
            doc = session.scalars(stmt).first()

            now = datetime.now(timezone.utc)
            if doc is None:
                doc = DocumentModel(
                    id=uuid.uuid4(),
                    filename=filename,
                    title=title,
                    category=category,
                    file_path=file_path,
                    checksum_sha256=checksum_sha256,
                    status="indexing",
                    chunk_count=0,
                    uploaded_at=now,
                    updated_at=now,
                )
                session.add(doc)
            else:
                doc.title = title
                doc.category = category
                doc.file_path = file_path
                # In Phase 2.1B: Do NOT overwrite checksum_sha256 or chunk_count during registration.
                # checksum_sha256 serves as the authoritative active-version pointer and is updated
                # only upon successful ChromaDB verification via mark_indexed().
                doc.status = "indexing"
                doc.updated_at = now

            session.commit()
            session.refresh(doc)
            return doc

    def mark_indexed(
        self,
        document_id: str,
        chunk_count: int,
        checksum_sha256: Optional[str] = None,
    ) -> DocumentModel:
        """
        Updates document status to 'indexed' with final chunk count and indexed_at timestamp.
        Atomically updates checksum_sha256 to point to the verified active version if provided.
        """
        with self.session_factory() as session:
            stmt = select(DocumentModel).where(DocumentModel.id == uuid.UUID(str(document_id)))
            doc = session.scalars(stmt).one()

            now = datetime.now(timezone.utc)
            doc.status = "indexed"
            doc.chunk_count = chunk_count
            if checksum_sha256 is not None:
                doc.checksum_sha256 = checksum_sha256
            doc.indexed_at = now
            doc.updated_at = now

            session.commit()
            session.refresh(doc)
            return doc

    def mark_failed(self, document_id: str) -> DocumentModel:
        """Updates document status to 'failed' upon processing failure."""
        with self.session_factory() as session:
            stmt = select(DocumentModel).where(DocumentModel.id == uuid.UUID(str(document_id)))
            doc = session.scalars(stmt).one()

            doc.status = "failed"
            doc.updated_at = datetime.now(timezone.utc)

            session.commit()
            session.refresh(doc)
            return doc

    def get_active_documents(self):
        """Retrieves all documents currently marked as 'indexed'."""
        with self.session_factory() as session:
            stmt = select(DocumentModel).where(DocumentModel.status == "indexed")
            return list(session.scalars(stmt).all())
