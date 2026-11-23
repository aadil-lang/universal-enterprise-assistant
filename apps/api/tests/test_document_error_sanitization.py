"""
Regression test for Phase 5B.4:
Sanitize document-ingestion error responses.
Ensures raw internal exceptions, filesystem paths, database credentials,
and stack traces are never returned to clients in HTTP 500 responses.
"""

from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException, UploadFile

from app.core.auth import CallerIdentity, UserRole
from app.routers.documents import upload_document


def test_document_ingestion_internal_error_sanitized():
    """
    Verifies that when an unexpected error occurs during document ingestion,
    the client receives a generic sanitized message and internal diagnostic
    details (e.g. filesystem paths, internal hosts, stack traces) are suppressed.
    """
    sensitive_internal_error = "OperationalError: connection to 10.128.0.4:5432 failed: password authentication failed for user 'acme_admin' at /etc/ssl/certs/db.key"

    mock_pipeline = MagicMock()
    mock_pipeline.ingest_document.side_effect = RuntimeError(sensitive_internal_error)

    import io
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "sensitive_policy.pdf"
    mock_file.file = io.BytesIO(b"%PDF-1.4 dummy content")

    hr_admin = CallerIdentity(
        user_id="b0000000-0000-0000-0000-000000000101",
        employee_number="E101",
        role=UserRole.HR_ADMIN,
    )

    with pytest.raises(HTTPException) as exc_info:
        upload_document(
            file=mock_file,
            title="Sensitive Policy",
            category="HR",
            current_user=hr_admin,
            pipeline=mock_pipeline,
        )

    assert exc_info.value.status_code == 500
    assert "internal processing error occurred" in exc_info.value.detail
    # Verify sensitive error details are completely absent
    assert "10.128.0.4" not in exc_info.value.detail
    assert "acme_admin" not in exc_info.value.detail
    assert "/etc/ssl/certs" not in exc_info.value.detail
    assert "password" not in exc_info.value.detail.lower()
    assert "OperationalError" not in exc_info.value.detail
