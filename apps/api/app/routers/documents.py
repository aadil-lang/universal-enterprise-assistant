"""
Document Ingestion & Management Router.
Provides upload and status inspection endpoints for enterprise policy documents.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.auth import CallerIdentity, UserRole, get_current_active_user
from app.schemas.document import DocumentDetailResponse, DocumentUploadResponse
from app.services.document_registry import DocumentRegistry
from app.services.document_validation import (
    DocumentValidationError,
    EmptyDocumentError,
    MalformedDocumentError,
    UnsupportedFormatError,
)
from app.services.ingestion_pipeline import IngestionPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


def get_pipeline() -> IngestionPipeline:
    """Dependency provider for IngestionPipeline."""
    return IngestionPipeline()


def get_registry() -> DocumentRegistry:
    """Dependency provider for DocumentRegistry."""
    return DocumentRegistry()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest enterprise policy document",
)
def upload_document(
    file: UploadFile = File(..., description="Document file to ingest (.pdf, .docx, .md)"),
    title: Optional[str] = Form(None, description="Optional custom title for the document"),
    category: str = Form("HR", description="Document category ('HR' or 'IT')"),
    current_user: CallerIdentity = Depends(get_current_active_user),
    pipeline: IngestionPipeline = Depends(get_pipeline),
) -> DocumentUploadResponse:
    """
    Accepts multipart file upload, validates format and content,
    extracts text, chunks, embeds, indexes into ChromaDB, and records in PostgreSQL.
    Enforces authorization: Only callers with the 'hr_admin' role are permitted.
    """
    if current_user.role != UserRole.HR_ADMIN:
        logger.warning(
            "Unauthorized document upload attempt by employee %s with role '%s'",
            current_user.employee_number,
            current_user.role.value if hasattr(current_user.role, 'value') else current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only HR Administrators are authorized to upload policy documents.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    try:
        content = file.file.read()
    except Exception as e:
        logger.error("Failed to read uploaded file stream: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file stream.",
        )

    try:
        response = pipeline.ingest_document(
            filename=file.filename,
            content=content,
            title=title,
            category=category,
        )
        return response
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except EmptyDocumentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MalformedDocumentError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except DocumentValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during document ingestion: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal processing error occurred during document ingestion. Please verify the document format or try again later.",
        )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document processing status and metadata",
)
def get_document_status(
    document_id: str,
    registry: DocumentRegistry = Depends(get_registry),
) -> DocumentDetailResponse:
    """Retrieves document record from PostgreSQL registry by UUID."""
    doc = registry.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    return DocumentDetailResponse.model_validate(doc)
