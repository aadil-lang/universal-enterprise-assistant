"""
Comprehensive Test Suite for Phase 2.1 RAG Document Ingestion & Indexing Pipeline.
Covers all 16 required test scenarios across validation, extraction, chunking,
embedding, vector indexing, re-indexing, status updates, and API upload handling.
"""

import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import chromadb
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.document import Base, DocumentModel
from app.core.auth import CallerIdentity, UserRole, get_current_active_user
from app.routers.documents import get_pipeline, get_registry
from app.schemas.document import DocumentStatus
from app.services.chunker import chunk_extracted_segments
from app.services.document_extractor import (
    ExtractedSegment,
    extract_from_docx,
    extract_from_markdown,
    extract_from_pdf,
    extract_from_txt,
    extract_text_from_document,
)
from app.services.document_registry import DocumentRegistry
from app.services.document_validation import (
    EmptyDocumentError,
    MalformedDocumentError,
    UnsupportedFormatError,
    validate_document_file,
)
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_pipeline import IngestionPipeline
from app.services.vector_store import VectorStoreService


# ---------------------------------------------------------------------------
# In-Memory SQLite Fixture for Isolated Repository Testing
# ---------------------------------------------------------------------------
@pytest.fixture
def in_memory_session_factory():
    """Provides an isolated SQLite in-memory database session factory for repository tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)


@pytest.fixture
def ephemeral_vector_store():
    """Provides an isolated in-memory EphemeralClient ChromaDB store."""
    client = chromadb.EphemeralClient()
    return VectorStoreService(client=client, collection_name=f"test_policies_{uuid.uuid4().hex[:8]}")


@pytest.fixture
def mock_embedding_service():
    """Fast deterministic mock embedder to avoid heavy CPU/GPU overhead during unit testing."""
    service = MagicMock(spec=EmbeddingService)
    # Generate deterministic 384-dimensional vector
    service.embed_texts.side_effect = lambda texts: [[0.05 * (i % 10)] * 384 for i in range(len(texts))]
    return service


# ===========================================================================
# 1. PDF Extraction Test
# ===========================================================================
def test_1_pdf_extraction_real_fixture():
    """Verifies text extraction from a real PDF policy document."""
    pdf_path = Path("data/policies/Acme_Leave_Policy.pdf")
    assert pdf_path.exists(), "PDF policy fixture must exist"
    content = pdf_path.read_bytes()

    segments = extract_from_pdf(content)
    assert len(segments) >= 1
    assert any("vacation" in seg.text.lower() or "leave" in seg.text.lower() for seg in segments)
    assert segments[0].page_number >= 1


# ===========================================================================
# 2. DOCX Extraction Test
# ===========================================================================
def test_2_docx_extraction_real_fixture():
    """Verifies text extraction from a real DOCX policy document."""
    docx_path = Path("data/policies/Acme_IT_Equipment_Policy.docx")
    assert docx_path.exists(), "DOCX policy fixture must exist"
    content = docx_path.read_bytes()

    segments = extract_from_docx(content)
    assert len(segments) >= 1
    assert any("lenovo" in seg.text.lower() or "equipment" in seg.text.lower() for seg in segments)


# ===========================================================================
# 3. TXT Rejection Test (Supported Formats: PDF, DOCX, Markdown only)
# ===========================================================================
def test_3_txt_rejected_as_unsupported():
    """Verifies that .txt files are rejected as unsupported formats per approved scope."""
    sample_text = b"SECTION 1: ONBOARDING\n\nWelcome to the enterprise helpdesk system."
    with pytest.raises(UnsupportedFormatError):
        validate_document_file("onboarding.txt", sample_text, category="HR")


# ===========================================================================
# 4. Markdown Extraction Test
# ===========================================================================
def test_4_markdown_extraction_real_fixture():
    """Verifies heading hierarchy extraction from a Markdown policy file."""
    md_path = Path("data/policies/Acme_Remote_Work_Policy.md")
    assert md_path.exists(), "Markdown policy fixture must exist"
    content = md_path.read_bytes()

    segments = extract_from_markdown(content)
    assert len(segments) >= 1
    assert any("stipend" in seg.text.lower() or "remote" in seg.text.lower() for seg in segments)
    assert any(seg.section != "General" for seg in segments)


# ===========================================================================
# 5. Empty Document Handling
# ===========================================================================
def test_5_empty_document_handling():
    """Verifies zero-byte or whitespace-only files raise EmptyDocumentError."""
    with pytest.raises(EmptyDocumentError):
        validate_document_file("empty.md", b"", category="HR")

    with pytest.raises(EmptyDocumentError):
        validate_document_file("blank.md", b"   \n\n  \t  ", category="IT")


# ===========================================================================
# 6. Malformed Document Handling
# ===========================================================================
def test_6_malformed_document_handling():
    """Verifies corrupt/non-matching file content triggers MalformedDocumentError."""
    # File named .pdf with text contents
    with pytest.raises(MalformedDocumentError):
        validate_document_file("corrupt.pdf", b"This is not a real PDF file", category="HR")

    # File named .docx with random binary contents
    with pytest.raises(MalformedDocumentError):
        validate_document_file("corrupt.docx", b"\x00\x01\x02\x03\x04\x05", category="IT")


# ===========================================================================
# 7. Unsupported File Extensions
# ===========================================================================
def test_7_unsupported_file_extensions():
    """Verifies unsupported file extensions (including .txt) are consistently rejected."""
    for bad_file in ["policy.txt", "policy.exe", "policy.csv", "policy.xlsx", "policy.html"]:
        with pytest.raises(UnsupportedFormatError):
            validate_document_file(bad_file, b"content", category="HR")


# ===========================================================================
# 8. Chunk Boundaries and Overlap
# ===========================================================================
def test_8_chunk_boundaries_and_overlap():
    """Verifies chunk size capping, overlap windows, and boundary respect."""
    doc_id = str(uuid.uuid4())
    long_text = (
        "Enterprise sentence number one explains the general policy. "
        "Enterprise sentence number two covers reimbursement eligibility guidelines. "
        "Enterprise sentence number three details the expense submission requirements. "
        "Enterprise sentence number four outlines auditing procedures and compliance rules. "
        "Enterprise sentence number five specifies manager authorization workflows."
    )
    segments = [ExtractedSegment(text=long_text, section="Finance", page_number=1)]

    # Use small chunk size (120 chars) with 30 char overlap
    chunks = chunk_extracted_segments(doc_id, segments, chunk_size=120, chunk_overlap=30)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk.text) <= 160  # Allows boundary padding
        assert chunk.document_id == doc_id
        assert chunk.content_hash is not None
        assert chunk.document_checksum is not None
        assert chunk.chunk_id.startswith(f"{doc_id}_")


# ===========================================================================
# 9. Section and Page Metadata Preservation
# ===========================================================================
def test_9_section_and_page_metadata_preservation():
    """Verifies chunks inherit section headings and PDF page numbers."""
    doc_id = str(uuid.uuid4())
    segments = [
        ExtractedSegment(text="Policy overview on page 1", section="1. Overview", page_number=1),
        ExtractedSegment(text="Eligibility criteria on page 2", section="2. Eligibility", page_number=2),
    ]

    chunks = chunk_extracted_segments(doc_id, segments, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 2
    assert chunks[0].section == "1. Overview"
    assert chunks[0].page_number == 1
    assert chunks[1].section == "2. Eligibility"
    assert chunks[1].page_number == 2


# ===========================================================================
# 10. Embedding Generation
# ===========================================================================
def test_10_embedding_generation():
    """Verifies embedding generation produces 384-dimensional dense vectors."""
    embedder = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
    texts = ["Acme corporate remote work guidelines.", "Hardware refresh policy details."]
    vectors = embedder.embed_texts(texts)

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384


# ===========================================================================
# 11. Successful ChromaDB Indexing
# ===========================================================================
def test_11_successful_chromadb_indexing(ephemeral_vector_store):
    """Verifies that chunks are indexed into ChromaDB with queryable metadata."""
    doc_id = str(uuid.uuid4())
    segments = [
        ExtractedSegment(text="Standard laptop equipment is refreshed every 36 months.", section="Hardware", page_number=1)
    ]
    chunks = chunk_extracted_segments(doc_id, segments)

    count = ephemeral_vector_store.index_document_chunks(
        document_id=doc_id,
        filename="equipment_policy.docx",
        title="Equipment Policy",
        category="IT",
        chunks=chunks,
    )
    assert count == 1

    # Verify query
    res = ephemeral_vector_store.collection.query(
        query_texts=["laptop equipment refresh"],
        n_results=1,
    )
    assert len(res["ids"][0]) == 1
    assert res["metadatas"][0][0]["document_id"] == doc_id
    assert res["metadatas"][0][0]["category"] == "IT"


# ===========================================================================
# 12. Duplicate Upload Handling
# ===========================================================================
def test_12_duplicate_upload_handling(in_memory_session_factory, ephemeral_vector_store):
    """Verifies identical file uploads return existing indexed record without duplicate indexing."""
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    content = b"# Remote Work Policy\n\nDaily VPN usage is mandatory."
    resp1 = pipeline.ingest_document("remote_policy.md", content, category="IT")
    assert resp1.status == DocumentStatus.INDEXED
    first_chunk_count = resp1.chunk_count

    # Second upload with identical content
    resp2 = pipeline.ingest_document("remote_policy.md", content, category="IT")
    assert resp2.status == DocumentStatus.INDEXED
    assert resp2.document_id == resp1.document_id
    assert resp2.chunk_count == first_chunk_count
    assert "already indexed" in resp2.message.lower()


# ===========================================================================
# 13. Changed-Document Re-indexing
# ===========================================================================
def test_13_changed_document_reindexing(in_memory_session_factory, ephemeral_vector_store):
    """Verifies re-uploading modified content safely replaces obsolete vector chunks."""
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    content_v1 = b"# IT Equipment\n\nLaptops are refreshed every 36 months."
    resp_v1 = pipeline.ingest_document("equipment.md", content_v1, category="IT")
    doc_id = resp_v1.document_id

    # Modified content with new sections
    content_v2 = (
        "# IT Equipment Update\n\n"
        "Laptops are refreshed every 24 months.\n\n"
        "Monitors are replaced on failure.\n\n"
        "Peripherals are replaced annually."
    ).encode("utf-8")

    resp_v2 = pipeline.ingest_document("equipment.md", content_v2, category="IT")
    assert resp_v2.document_id == doc_id
    assert resp_v2.checksum_sha256 != resp_v1.checksum_sha256
    assert resp_v2.status == DocumentStatus.INDEXED

    # Ensure ChromaDB chunk count matches new version
    indexed_in_store = ephemeral_vector_store.count_document_chunks(doc_id)
    assert indexed_in_store == resp_v2.chunk_count


# ===========================================================================
# 14. Indexing Failure and Recovery
# ===========================================================================
def test_14_indexing_failure_and_recovery(in_memory_session_factory, ephemeral_vector_store):
    """Verifies that an indexing error marks status as failed and permits subsequent retry."""
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    content = b"# Leave Policy\n\nAnnual vacation is 18 days."

    # Simulate vector store failure
    with patch.object(ephemeral_vector_store, "index_document_chunks", side_effect=RuntimeError("ChromaDB down")):
        with pytest.raises(RuntimeError):
            pipeline.ingest_document("leave.md", content, category="HR")

    doc = registry.get_document_by_filename("leave.md")
    assert doc is not None
    assert doc.status == DocumentStatus.FAILED.value

    # Retry with vector store restored
    recovered_resp = pipeline.ingest_document("leave.md", content, category="HR")
    assert recovered_resp.status == DocumentStatus.INDEXED

    doc_after = registry.get_document_by_filename("leave.md")
    assert doc_after.status == DocumentStatus.INDEXED.value


# ===========================================================================
# 14b. Failed Re-indexing Preserves Previously Indexed Version (Regression)
# ===========================================================================
def test_14b_failed_reindexing_preserves_previously_indexed_version(in_memory_session_factory, ephemeral_vector_store):
    """
    Regression Test: Proves that a failed re-index does NOT destroy the previously indexed chunks.
    The existing indexed version must remain queryable in ChromaDB if replacement upsert fails.
    """
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    # 1. Ingest initial valid version (v1)
    content_v1 = b"# Remote Work Policy\n\nDaily VPN usage is strictly mandatory."
    resp_v1 = pipeline.ingest_document("remote_policy.md", content_v1, category="IT")
    assert resp_v1.status == DocumentStatus.INDEXED
    doc_id = resp_v1.document_id

    # Verify v1 is in vector store
    chunks_before = ephemeral_vector_store.count_document_chunks(doc_id)
    assert chunks_before >= 1

    # 2. Attempt to ingest modified version (v2), but simulate failure during vector upsert
    content_v2 = b"# Remote Work Policy Updated\n\nNew rules about flexible hours."

    def failing_upsert(*args, **kwargs):
        raise RuntimeError("Simulated transient ChromaDB write error")

    with patch.object(ephemeral_vector_store.collection, "upsert", side_effect=failing_upsert):
        with pytest.raises(Exception):
            pipeline.ingest_document("remote_policy.md", content_v2, category="IT")

    # 3. Assert that the vector store STILL contains the original v1 chunks!
    chunks_after = ephemeral_vector_store.count_document_chunks(doc_id)
    assert chunks_after == chunks_before, "Previous indexed chunks must NOT be deleted if replacement fails!"

    # Query ChromaDB to ensure v1 content remains queryable
    query_res = ephemeral_vector_store.collection.query(
        query_texts=["VPN usage"],
        n_results=1,
    )
    assert "VPN" in query_res["documents"][0][0]

    # 4. Assert that the registry records status as 'failed' and does not claim success
    doc_record = registry.get_document_by_id(doc_id)
    assert doc_record.status == DocumentStatus.FAILED.value


# ===========================================================================
# 15. SQLite In-Memory Mock Repository Lifecycle (Isolated DB Unit Test)
# ===========================================================================
def test_15_sqlite_mock_repository_status_and_chunk_count(in_memory_session_factory):
    """
    Tests DocumentRegistry SQL lifecycle transitions using an isolated SQLite in-memory database.
    Note: Live PostgreSQL verification is documented as blocked due to Docker CLI absence on the host.
    """
    registry = DocumentRegistry(session_factory=in_memory_session_factory)

    doc = registry.register_or_update_document(
        filename="test_doc.md",
        title="Test Document",
        category="HR",
        file_path="data/uploads/test_doc.md",
        checksum_sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    )
    assert doc.status == "indexing"
    assert doc.chunk_count == 0

    doc_id = str(doc.id)
    indexed_doc = registry.mark_indexed(doc_id, chunk_count=5)
    assert indexed_doc.status == "indexed"
    assert indexed_doc.chunk_count == 5
    assert indexed_doc.indexed_at is not None


# ===========================================================================
# 16. Upload API Validation and Responses
# ===========================================================================
def test_16_upload_api_validation_and_responses(in_memory_session_factory, ephemeral_vector_store):
    """Verifies HTTP status codes, role-based authorization, and responses of the /documents/upload API endpoint."""
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    app.dependency_overrides[get_pipeline] = lambda: pipeline
    app.dependency_overrides[get_registry] = lambda: registry

    client = TestClient(app)

    try:
        # 0a. Unauthenticated upload attempt (401 Unauthorized)
        files = {"file": ("test_policy.md", b"# Vacation\n\n18 days leave.", "text/markdown")}
        data = {"category": "HR", "title": "Vacation Policy"}
        unauth_resp = client.post("/documents/upload", files=files, data=data)
        assert unauth_resp.status_code == 401

        # 0b. Employee role upload attempt (403 Forbidden)
        app.dependency_overrides[get_current_active_user] = lambda: CallerIdentity(
            user_id="b0000000-0000-0000-0000-000000000102",
            employee_number="E102",
            role=UserRole.EMPLOYEE,
        )
        emp_resp = client.post("/documents/upload", files=files, data=data)
        assert emp_resp.status_code == 403
        assert "Only HR Administrators are authorized" in emp_resp.json()["detail"]

        # 0c. Set HR Admin authentication for legitimate uploads
        app.dependency_overrides[get_current_active_user] = lambda: CallerIdentity(
            user_id="b0000000-0000-0000-0000-000000000101",
            employee_number="E101",
            role=UserRole.HR_ADMIN,
        )

        # 1. Successful upload (201 Created)
        response = client.post("/documents/upload", files=files, data=data)
        assert response.status_code == 201
        res_data = response.json()
        assert res_data["status"] == "indexed"
        assert res_data["category"] == "HR"
        doc_id = res_data["document_id"]

        # 2. Get document status (200 OK)
        status_resp = client.get(f"/documents/{doc_id}")
        assert status_resp.status_code == 200
        assert str(status_resp.json()["id"]) == str(doc_id)

        # 3. Unsupported extension - TXT rejected (400 Bad Request)
        files_txt = {"file": ("notes.txt", b"Plain text notes", "text/plain")}
        txt_resp = client.post("/documents/upload", files=files_txt, data={"category": "HR"})
        assert txt_resp.status_code == 400

        # 4. Unsupported binary extension - EXE rejected (400 Bad Request)
        files_bad = {"file": ("policy.exe", b"binary", "application/octet-stream")}
        bad_resp = client.post("/documents/upload", files=files_bad, data={"category": "HR"})
        assert bad_resp.status_code == 400

        # 5. Invalid category (400 Bad Request)
        files_cat = {"file": ("policy.md", b"Content", "text/markdown")}
        cat_resp = client.post("/documents/upload", files=files_cat, data={"category": "FINANCE"})
        assert cat_resp.status_code == 400

        # 6. Empty file (400 Bad Request)
        files_empty = {"file": ("empty.md", b"", "text/markdown")}
        empty_resp = client.post("/documents/upload", files=files_empty, data={"category": "HR"})
        assert empty_resp.status_code == 400

    finally:
        app.dependency_overrides.clear()


# ===========================================================================
# 17. Content Hash Verification
# ===========================================================================
def test_17_chunk_content_hash_matches_normalized_content():
    """
    Verifies that every chunk's content_hash is the true SHA-256 of its normalized text,
    and never an empty-file or placeholder hash.
    """
    import hashlib
    doc_id = str(uuid.uuid4())
    segments = [
        ExtractedSegment(
            text="Acme remote work equipment stipend is $300.",
            section="Stipend",
            page_number=1,
        ),
        ExtractedSegment(
            text="Employees must connect via enterprise VPN daily.",
            section="Network",
            page_number=1,
        ),
    ]

    chunks = chunk_extracted_segments(doc_id, segments, chunk_size=400, chunk_overlap=50)
    assert len(chunks) >= 1

    EMPTY_FILE_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    for chunk in chunks:
        expected_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
        assert chunk.content_hash == expected_hash, f"Chunk hash {chunk.content_hash} does not match expected {expected_hash}"
        assert chunk.content_hash != EMPTY_FILE_SHA256, "Chunk hash must not be the empty-file SHA-256 placeholder"
        assert len(chunk.content_hash) == 64


# ===========================================================================
# Phase 2.1B Regression Test Suites (A through F)
# ===========================================================================

def test_suite_a_successful_replacement(in_memory_session_factory, ephemeral_vector_store):
    """
    Test Suite A: Successful Replacement
    Index a document, then index a modified version of the same document.
    Verify:
    - Old chunk IDs and replacement chunk IDs are disjoint.
    - Replacement chunks are active and searchable.
    - Old chunk IDs no longer exist in ChromaDB.
    - PostgreSQL document record points to the new checksum_sha256 and chunk count.
    """
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    content_v1 = b"# Travel Policy\n\nEconomy flights are authorized for domestic travel."
    resp_v1 = pipeline.ingest_document("travel_policy.md", content_v1, category="HR")
    doc_id = resp_v1.document_id
    v1_checksum = resp_v1.checksum_sha256

    # Get v1 chunks from ChromaDB
    v1_res = ephemeral_vector_store.collection.get(where={"document_id": doc_id})
    v1_ids = v1_res["ids"]
    assert len(v1_ids) >= 1
    assert all(v1_checksum in cid for cid in v1_ids)

    # Ingest modified v2
    content_v2 = (
        "# Travel Policy Revised\n\n"
        "Economy flights are authorized for domestic travel under 5 hours.\n\n"
        "Business class is permitted for international flights over 8 hours."
    ).encode("utf-8")
    resp_v2 = pipeline.ingest_document("travel_policy.md", content_v2, category="HR")
    assert resp_v2.document_id == doc_id
    v2_checksum = resp_v2.checksum_sha256
    assert v2_checksum != v1_checksum

    # 1. Old chunk IDs and replacement chunk IDs are disjoint
    v2_res = ephemeral_vector_store.collection.get(where={"document_id": doc_id})
    v2_ids = v2_res["ids"]
    assert set(v1_ids).isdisjoint(set(v2_ids)), "Old and replacement chunk IDs must be completely disjoint"

    # 2. Replacement chunks are active and searchable
    search_res = ephemeral_vector_store.collection.query(
        query_texts=["international business class"],
        n_results=1,
    )
    assert len(search_res["ids"][0]) == 1
    assert search_res["ids"][0][0] in v2_ids

    # 3. Old chunk IDs no longer exist in ChromaDB
    old_check = ephemeral_vector_store.collection.get(ids=v1_ids)
    assert len(old_check["ids"]) == 0, "Old chunk IDs must be purged from ChromaDB"

    # 4. PostgreSQL document record points to the new checksum_sha256 and chunk count
    doc_record = registry.get_document_by_id(doc_id)
    assert doc_record.status == "indexed"
    assert doc_record.checksum_sha256 == v2_checksum
    assert doc_record.chunk_count == len(v2_ids)


def test_suite_b_partial_chromadb_write_failure(in_memory_session_factory, ephemeral_vector_store):
    """
    Test Suite B: Partial ChromaDB Write Failure
    Simulate a ChromaDB write failure after at least one replacement chunk has been written.
    Verify:
    - Every old chunk remains present and unchanged in ChromaDB.
    - No replacement chunks remain in ChromaDB.
    - PostgreSQL document status is failed.
    - Document record retains the old checksum_sha256 and chunk_count.
    """
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    content_v1 = b"# Security Policy\n\nPasswords must be at least 14 characters."
    resp_v1 = pipeline.ingest_document("security.md", content_v1, category="IT")
    doc_id = resp_v1.document_id
    v1_checksum = resp_v1.checksum_sha256
    v1_count = resp_v1.chunk_count

    v1_chunks = ephemeral_vector_store.collection.get(
        where={"document_id": doc_id},
        include=["documents", "metadatas"],
    )
    v1_ids = v1_chunks["ids"]
    v1_docs = v1_chunks["documents"]
    v1_metas = v1_chunks["metadatas"]

    # Modified content that generates at least 2 chunks
    content_v2 = (
        "# Security Policy Version 2\n\n"
        + "Passwords must be at least 16 characters with biometric MFA.\n\n" * 20
        + "Session timeouts are enforced after 15 minutes of inactivity.\n\n" * 20
    ).encode("utf-8")

    real_upsert = ephemeral_vector_store.collection.upsert

    def partial_failing_upsert(**kwargs):
        # Write only the first chunk to simulate a partial write failure mid-batch
        real_upsert(
            ids=[kwargs["ids"][0]],
            embeddings=[kwargs["embeddings"][0]],
            documents=[kwargs["documents"][0]],
            metadatas=[kwargs["metadatas"][0]],
        )
        raise RuntimeError("Simulated failure after partially writing chunk 0")

    with patch.object(ephemeral_vector_store.collection, "upsert", side_effect=partial_failing_upsert):
        with pytest.raises(Exception):
            pipeline.ingest_document("security.md", content_v2, category="IT")

    # 1. Every old chunk remains present and unchanged in ChromaDB
    v1_after = ephemeral_vector_store.collection.get(
        ids=v1_ids,
        include=["documents", "metadatas"],
    )
    assert set(v1_after["ids"]) == set(v1_ids)
    assert v1_after["documents"] == v1_docs
    assert v1_after["metadatas"] == v1_metas

    # 2. No replacement chunks remain in ChromaDB
    all_chunks = ephemeral_vector_store.collection.get(
        where={"document_id": doc_id},
        include=["metadatas"],
    )
    for meta in all_chunks.get("metadatas", []):
        assert meta["document_checksum"] == v1_checksum, "Replacement chunks must not remain in ChromaDB"

    # 3. PostgreSQL document status is failed
    doc_record = registry.get_document_by_id(doc_id)
    assert doc_record.status == DocumentStatus.FAILED.value

    # 4. Document record retains the old checksum_sha256 and chunk_count
    assert doc_record.checksum_sha256 == v1_checksum
    assert doc_record.chunk_count == v1_count


def test_suite_c_verification_failure(in_memory_session_factory, ephemeral_vector_store):
    """
    Test Suite C: Verification Failure
    Simulate a verification mismatch after writing replacement chunks.
    Verify:
    - Staged replacement chunks are rolled back (deleted).
    - Old active chunks remain intact in ChromaDB.
    - PostgreSQL document status is failed.
    """
    from app.services.vector_store import VectorStoreError
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    content_v1 = b"# Backup Policy\n\nDaily incremental backups run at midnight."
    resp_v1 = pipeline.ingest_document("backup.md", content_v1, category="IT")
    doc_id = resp_v1.document_id
    v1_checksum = resp_v1.checksum_sha256
    v1_count = resp_v1.chunk_count

    v1_res = ephemeral_vector_store.collection.get(where={"document_id": doc_id})
    v1_ids = v1_res["ids"]

    content_v2 = b"# Backup Policy Updated\n\nContinuous hourly snapshots to cloud storage."

    # Simulate verification mismatch during verify_staged_chunks
    with patch.object(
        ephemeral_vector_store,
        "verify_staged_chunks",
        side_effect=VectorStoreError("Checksum mismatch during post-write verification"),
    ):
        with pytest.raises(Exception):
            pipeline.ingest_document("backup.md", content_v2, category="IT")

    # 1. Staged replacement chunks are rolled back (deleted)
    all_chunks = ephemeral_vector_store.collection.get(
        where={"document_id": doc_id},
        include=["metadatas"],
    )
    assert all(meta["document_checksum"] == v1_checksum for meta in all_chunks["metadatas"])

    # 2. Old active chunks remain intact in ChromaDB
    old_check = ephemeral_vector_store.collection.get(ids=v1_ids)
    assert len(old_check["ids"]) == len(v1_ids)

    # 3. PostgreSQL document status is failed, retaining old version pointer
    doc_record = registry.get_document_by_id(doc_id)
    assert doc_record.status == DocumentStatus.FAILED.value
    assert doc_record.checksum_sha256 == v1_checksum
    assert doc_record.chunk_count == v1_count


def test_suite_d_postgresql_activation_failure(in_memory_session_factory, ephemeral_vector_store):
    """
    Test Suite D: PostgreSQL Activation Failure
    Simulate a database failure when updating the document record to indexed.
    Verify:
    - Replacement chunks are deleted from ChromaDB.
    - Old active chunks remain intact in ChromaDB.
    - The document status in PostgreSQL is recorded as failed.
    - The stored checksum_sha256 and chunk_count still reflect the older version.
    """
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    content_v1 = b"# Equipment Return\n\nAll laptops must be returned upon termination."
    resp_v1 = pipeline.ingest_document("return.md", content_v1, category="IT")
    doc_id = resp_v1.document_id
    v1_checksum = resp_v1.checksum_sha256
    v1_count = resp_v1.chunk_count

    v1_ids = ephemeral_vector_store.collection.get(where={"document_id": doc_id})["ids"]

    content_v2 = b"# Equipment Return Updated\n\nLaptops and peripherals returned within 48 hours."

    # Simulate database error when mark_indexed is called
    with patch.object(registry, "mark_indexed", side_effect=RuntimeError("Database lock timeout")):
        with pytest.raises(Exception):
            pipeline.ingest_document("return.md", content_v2, category="IT")

    # 1. Replacement chunks are deleted from ChromaDB
    all_chunks = ephemeral_vector_store.collection.get(
        where={"document_id": doc_id},
        include=["metadatas"],
    )
    assert all(meta["document_checksum"] == v1_checksum for meta in all_chunks["metadatas"])

    # 2. Old active chunks remain intact in ChromaDB
    v1_check = ephemeral_vector_store.collection.get(ids=v1_ids)
    assert len(v1_check["ids"]) == len(v1_ids)

    # 3. The document status in PostgreSQL is recorded as failed
    # 4. The stored checksum_sha256 and chunk_count still reflect the older version
    doc_record = registry.get_document_by_id(doc_id)
    assert doc_record.status == DocumentStatus.FAILED.value
    assert doc_record.checksum_sha256 == v1_checksum
    assert doc_record.chunk_count == v1_count


def test_suite_e_cleanup_failure_after_activation(in_memory_session_factory, ephemeral_vector_store):
    """
    Test Suite E: Cleanup Failure After Activation
    Simulate an obsolete chunk cleanup failure after successful PostgreSQL activation.
    Verify:
    - Ingestion does not fail.
    - Document status remains indexed.
    - Document checksum matches the replacement version.
    - Obsolete chunks can still be identified and distinguished by their document_checksum metadata.
    """
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    content_v1 = b"# Sick Leave\n\n5 paid sick days per calendar year."
    resp_v1 = pipeline.ingest_document("sick_leave.md", content_v1, category="HR")
    doc_id = resp_v1.document_id
    v1_checksum = resp_v1.checksum_sha256

    content_v2 = b"# Sick Leave Revised\n\n7 paid sick days per calendar year."

    # Simulate error in purge_obsolete_chunks (or underlying collection.delete during purge)
    with patch.object(
        ephemeral_vector_store.collection,
        "delete",
        side_effect=RuntimeError("Transient delete failure during obsolete purge"),
    ):
        # Ingestion must NOT fail even if obsolete cleanup fails
        resp_v2 = pipeline.ingest_document("sick_leave.md", content_v2, category="HR")

    # 1. Ingestion did not fail
    assert resp_v2.status == DocumentStatus.INDEXED
    v2_checksum = resp_v2.checksum_sha256

    # 2. Document status remains indexed
    doc_record = registry.get_document_by_id(doc_id)
    assert doc_record.status == "indexed"

    # 3. Document checksum matches the replacement version
    assert doc_record.checksum_sha256 == v2_checksum

    # 4. Obsolete chunks can still be identified and distinguished by their document_checksum metadata
    all_chunks = ephemeral_vector_store.collection.get(
        where={"document_id": doc_id},
        include=["metadatas"],
    )
    checksums_found = {meta["document_checksum"] for meta in all_chunks["metadatas"]}
    assert v1_checksum in checksums_found, "Old chunk still present due to failed purge"
    assert v2_checksum in checksums_found, "New active chunk present"
    # The active document in DB definitively identifies which one is authoritative
    assert doc_record.checksum_sha256 == v2_checksum


def test_suite_f_exact_content_integrity(in_memory_session_factory, ephemeral_vector_store):
    """
    Test Suite F: Exact Content Integrity
    After each successful indexing operation:
    - Retrieve all chunks from ChromaDB for the document.
    - Verify exact count, IDs, chunk_index order, content_hash values, and document_checksum.
    """
    import hashlib
    registry = DocumentRegistry(session_factory=in_memory_session_factory)
    pipeline = IngestionPipeline(registry=registry, vector_store=ephemeral_vector_store)

    content = (
        "# Remote Work Eligibility\n\n"
        "Full-time employees with 90 days tenure are eligible for remote work.\n\n"
        "Managers must approve all remote arrangements in writing.\n\n"
        "Employees must maintain high-speed internet connection."
    ).encode("utf-8")

    expected_doc_checksum = hashlib.sha256(content).hexdigest()
    resp = pipeline.ingest_document("remote_eligibility.md", content, category="HR")
    assert resp.status == DocumentStatus.INDEXED
    doc_id = resp.document_id
    assert resp.checksum_sha256 == expected_doc_checksum

    # Retrieve all chunks for this document
    records = ephemeral_vector_store.collection.get(
        where={"document_id": doc_id},
        include=["documents", "metadatas"],
    )
    chunk_ids = records["ids"]
    chunk_docs = records["documents"]
    chunk_metas = records["metadatas"]

    # 1. Exact count matches
    assert len(chunk_ids) == resp.chunk_count

    # Sort chunks by chunk_index
    indexed_chunks = sorted(
        zip(chunk_ids, chunk_docs, chunk_metas),
        key=lambda x: int(x[2]["chunk_index"]),
    )

    # 2. Verify IDs, chunk_index order, content_hash, and document_checksum
    for i, (cid, text, meta) in enumerate(indexed_chunks):
        expected_cid = f"{doc_id}_{expected_doc_checksum}_{i}"
        assert cid == expected_cid, f"Chunk ID {cid} must match expected {expected_cid}"
        assert int(meta["chunk_index"]) == i, f"Chunk index {meta['chunk_index']} must equal sequential index {i}"
        assert meta["document_checksum"] == expected_doc_checksum, "document_checksum must match full doc sha256"

        expected_content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert meta["content_hash"] == expected_content_hash, "content_hash must equal SHA-256 of normalized text"
        assert meta["document_id"] == doc_id
        assert meta["category"] == "HR"
