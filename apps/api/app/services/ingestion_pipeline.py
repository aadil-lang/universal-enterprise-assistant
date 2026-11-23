"""
Document Ingestion Pipeline Orchestrator.
Coordinates the end-to-end processing stages:
Upload -> Validation -> Text Extraction -> Normalization -> Chunking -> Embedding -> ChromaDB Indexing -> PostgreSQL Status Update.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from app.config.settings import get_settings
from app.schemas.document import DocumentStatus, DocumentUploadResponse
from app.services.chunker import chunk_extracted_segments
from app.services.document_extractor import extract_text_from_document
from app.services.document_registry import DocumentRegistry
from app.services.document_validation import validate_document_file
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Enterprise Document Ingestion and Vector Indexing Pipeline.
    Strictly generic: operates over document content without hardcoded company facts.
    """

    def __init__(
        self,
        registry: Optional[DocumentRegistry] = None,
        vector_store: Optional[VectorStoreService] = None,
    ):
        self.settings = get_settings()
        self.registry = registry or DocumentRegistry()
        self.vector_store = vector_store or VectorStoreService()

    def ingest_document(
        self,
        filename: str,
        content: bytes,
        title: Optional[str] = None,
        category: str = "HR",
    ) -> DocumentUploadResponse:
        """
        Executes the end-to-end document ingestion pipeline.

        Args:
            filename: Name of the uploaded file.
            content: Raw bytes of the document.
            title: Human-readable title (defaults to filename if omitted).
            category: Enterprise category ('HR' or 'IT').

        Returns:
            DocumentUploadResponse: Status, chunk count, and document details.
        """
        # Stage 1: Validation
        norm_category = category.strip().upper()
        ext, checksum = validate_document_file(filename, content, category=norm_category)

        derived_title = title.strip() if title and title.strip() else Path(filename).stem.replace("_", " ")

        # Stage 2: Deduplication Check
        existing_doc = self.registry.get_document_by_filename(filename)
        if (
            existing_doc is not None
            and existing_doc.checksum_sha256 == checksum
            and existing_doc.status == DocumentStatus.INDEXED.value
        ):
            logger.info("Document '%s' already indexed with identical checksum. Skipping reprocessing.", filename)
            return DocumentUploadResponse(
                document_id=str(existing_doc.id),
                filename=existing_doc.filename,
                title=existing_doc.title,
                category=existing_doc.category,
                status=DocumentStatus.INDEXED,
                checksum_sha256=existing_doc.checksum_sha256,
                chunk_count=existing_doc.chunk_count,
                message="Document already indexed with identical checksum. Unchanged.",
            )

        # Stage 3: Save file to configured application data directory safely
        storage_dir = Path(self.settings.DOCUMENTS_DIR)
        storage_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = Path(filename).name
        target_path = storage_dir / safe_filename
        with open(target_path, "wb") as f:
            f.write(content)

        # Stage 4: Register / Update in PostgreSQL (status='indexing')
        doc_record = self.registry.register_or_update_document(
            filename=safe_filename,
            title=derived_title,
            category=norm_category,
            file_path=str(target_path).replace("\\", "/"),
            checksum_sha256=checksum,
        )
        document_id = str(doc_record.id)
        staged_ids = []

        try:
            # Stage 5: Text Extraction
            segments = extract_text_from_document(filename=safe_filename, content=content)

            # Stage 6: Chunking & Normalization with full-document checksum
            chunks = chunk_extracted_segments(
                document_id=document_id,
                document_checksum=checksum,
                segments=segments,
                chunk_size=self.settings.CHUNK_SIZE,
                chunk_overlap=self.settings.CHUNK_OVERLAP,
            )
            staged_ids = [chunk.chunk_id for chunk in chunks]

            # Stage 7: Embedding, ChromaDB Staging & Verification
            indexed_count = self.vector_store.index_document_chunks(
                document_id=document_id,
                filename=safe_filename,
                title=derived_title,
                category=norm_category,
                chunks=chunks,
            )

            # Stage 8: Update PostgreSQL active pointer and status to 'indexed'
            updated_doc = self.registry.mark_indexed(
                document_id=document_id,
                chunk_count=indexed_count,
                checksum_sha256=checksum,
            )

            # Stage 9: Purge obsolete chunks only after PostgreSQL commits
            self.vector_store.purge_obsolete_chunks(
                document_id=document_id,
                active_checksum=checksum,
            )

            return DocumentUploadResponse(
                document_id=str(updated_doc.id),
                filename=updated_doc.filename,
                title=updated_doc.title,
                category=updated_doc.category,
                status=DocumentStatus.INDEXED,
                checksum_sha256=updated_doc.checksum_sha256,
                chunk_count=updated_doc.chunk_count,
                message=f"Successfully indexed {indexed_count} chunks into collection '{self.settings.CHROMA_COLLECTION}'.",
            )

        except Exception as e:
            logger.error("Ingestion failed for document '%s' (%s): %s", filename, document_id, e)
            if staged_ids:
                try:
                    self.vector_store.cleanup_staged_chunks(staged_ids)
                except Exception as clean_err:
                    logger.warning("Error during staged chunks cleanup: %s", clean_err)
            self.registry.mark_failed(document_id=document_id)
            raise
