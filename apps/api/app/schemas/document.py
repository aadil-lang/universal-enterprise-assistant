"""
Pydantic schemas for Document Ingestion and Indexing lifecycle.
Aligns with the PostgreSQL documents table and ChromaDB company_policies collection.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class DocumentStatus(str, Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentCategory(str, Enum):
    HR = "HR"
    IT = "IT"


class DocumentChunk(BaseModel):
    """Represents a text chunk produced during document processing."""
    chunk_id: str = Field(
        ...,
        description="Deterministic version-specific identifier {document_id}_{full_document_sha256}_{chunk_index}",
    )
    document_id: str = Field(..., description="UUID of the parent document")
    document_checksum: str = Field(..., description="Full 64-character SHA-256 hash of the parent document")
    chunk_index: int = Field(..., description="0-indexed position within the document")
    text: str = Field(..., description="Normalized text content of the chunk")
    section: str = Field(default="General", description="Section heading context if detected")
    page_number: int = Field(default=0, description="1-indexed page number for PDFs, 0 if not applicable")
    content_hash: str = Field(..., description="SHA-256 hash of the chunk text")


class DocumentUploadResponse(BaseModel):
    """Response returned upon document upload and ingestion triggering."""
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    filename: str
    title: str
    category: str
    status: DocumentStatus
    checksum_sha256: str
    chunk_count: int
    message: str


class DocumentDetailResponse(BaseModel):
    """Detailed metadata representing a registered document record."""
    model_config = ConfigDict(from_attributes=True)

    id: Union[str, uuid.UUID]
    title: str
    filename: str
    file_path: str
    category: str
    status: DocumentStatus
    checksum_sha256: str
    chunk_count: int
    uploaded_at: datetime
    indexed_at: Optional[datetime] = None
    updated_at: datetime
