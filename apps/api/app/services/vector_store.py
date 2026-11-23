"""
ChromaDB Vector Store Service.
Manages the company_policies collection, storing chunk texts, dense embeddings,
and structured metadata (document_id, filename, title, category, chunk_index, section, page_number, content_hash).
"""

import logging
import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api import ClientAPI
from chromadb.config import Settings as ChromaSettings

from app.config.settings import get_settings
from app.schemas.document import DocumentChunk
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Raised when ChromaDB collection operations fail."""
    pass


class VectorStoreService:
    """
    Manages collection lifecycle and vector indexing in ChromaDB.
    """

    def __init__(self, client: Optional[ClientAPI] = None, collection_name: Optional[str] = None):
        self.settings = get_settings()
        self.collection_name = collection_name or self.settings.CHROMA_COLLECTION
        self.client = client or self._init_client()
        self._collection = None

    def _init_client(self) -> ClientAPI:
        """Initializes ChromaDB client based on configuration."""
        if os.getenv("PYTEST_CURRENT_TEST") or self.settings.APP_ENV == "test":
            return chromadb.EphemeralClient()

        try:
            logger.info(
                "Connecting to ChromaDB HttpClient at %s:%s",
                self.settings.CHROMA_HOST,
                self.settings.CHROMA_PORT,
            )
            return chromadb.HttpClient(
                host=self.settings.CHROMA_HOST,
                port=self.settings.CHROMA_PORT,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        except Exception as e:
            logger.warning("Could not connect to ChromaDB HttpClient (%s). Using EphemeralClient fallback.", e)
            return chromadb.EphemeralClient()

    @property
    def collection(self):
        """Lazily creates or retrieves the target collection."""
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine", "description": "Enterprise policies vector index"},
                )
            except Exception as e:
                raise VectorStoreError(f"Failed to get_or_create ChromaDB collection '{self.collection_name}': {e}") from e
        return self._collection

    def index_document_chunks(
        self,
        document_id: str,
        filename: str,
        title: str,
        category: str,
        chunks: List[DocumentChunk],
    ) -> int:
        """
        Stages and indexes chunks into ChromaDB safely using disjoint version-specific chunk IDs.
        Preserves existing indexed chunks unchanged while staging and verifying replacement chunks.
        Cleans up staged replacement chunks on failure without impacting the active version.

        Returns:
            int: Number of chunks successfully staged and verified.
        """
        if not chunks:
            return 0

        # Step 1: Pre-calculate embeddings using the centralized embedding service
        embedder = get_embedding_service(self.settings.EMBEDDING_MODEL)
        texts = [chunk.text for chunk in chunks]
        embeddings = embedder.embed_texts(texts)

        # Step 2: Prepare IDs and metadata payloads with document_checksum
        new_ids: List[str] = [chunk.chunk_id for chunk in chunks]
        metadatas: List[Dict[str, Any]] = [
            {
                "document_id": str(document_id),
                "document_checksum": str(chunk.document_checksum),
                "filename": str(filename),
                "title": str(title),
                "category": str(category),
                "chunk_index": int(chunk.chunk_index),
                "section": str(chunk.section or "General"),
                "page_number": int(chunk.page_number or 0),
                "content_hash": str(chunk.content_hash),
            }
            for chunk in chunks
        ]

        # Step 3: Write replacement chunks to ChromaDB
        try:
            self.collection.upsert(
                ids=new_ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
        except Exception as upsert_err:
            logger.error(
                "Failed to upsert new chunks for document %s: %s. Cleaning up staged IDs.",
                document_id,
                upsert_err,
            )
            self.cleanup_staged_chunks(new_ids)
            raise VectorStoreError(f"Failed to upsert chunks into ChromaDB: {upsert_err}") from upsert_err

        # Step 4: Verify staged chunks exist and have correct content and metadata
        try:
            self.verify_staged_chunks(new_ids, chunks)
        except Exception as verify_err:
            logger.error(
                "Verification failed for staged chunks of document %s: %s. Cleaning up staged IDs.",
                document_id,
                verify_err,
            )
            self.cleanup_staged_chunks(new_ids)
            raise VectorStoreError(f"Staged chunks verification failed: {verify_err}") from verify_err

        logger.info(
            "Successfully staged and verified %d chunks for document %s (checksum: %s)",
            len(new_ids),
            document_id,
            chunks[0].document_checksum if chunks else "N/A",
        )
        return len(new_ids)

    def verify_staged_chunks(self, staged_ids: List[str], expected_chunks: List[DocumentChunk]) -> None:
        """
        Verifies that all staged IDs exist in ChromaDB and their content and metadata match expectations.
        """
        if not staged_ids:
            return

        records = self.collection.get(
            ids=staged_ids,
            include=["documents", "metadatas"],
        )
        retrieved_ids = set(records.get("ids", []))
        expected_ids = set(staged_ids)
        if expected_ids != retrieved_ids:
            missing = expected_ids - retrieved_ids
            raise VectorStoreError(f"Staged chunks missing from ChromaDB after write: {missing}")

        chunk_map = {chunk.chunk_id: chunk for chunk in expected_chunks}
        retrieved_docs = dict(zip(records["ids"], records.get("documents", [])))
        retrieved_metas = dict(zip(records["ids"], records.get("metadatas", [])))

        for cid, expected in chunk_map.items():
            actual_text = retrieved_docs.get(cid)
            actual_meta = retrieved_metas.get(cid, {})
            if actual_text != expected.text:
                raise VectorStoreError(f"Document text mismatch for staged chunk {cid}")
            if actual_meta.get("document_checksum") != expected.document_checksum:
                raise VectorStoreError(f"Document checksum mismatch for staged chunk {cid}")
            if actual_meta.get("content_hash") != expected.content_hash:
                raise VectorStoreError(f"Content hash mismatch for staged chunk {cid}")
            if int(actual_meta.get("chunk_index", -1)) != expected.chunk_index:
                raise VectorStoreError(f"Chunk index mismatch for staged chunk {cid}")

    def cleanup_staged_chunks(self, staged_ids: List[str]) -> None:
        """
        Deletes staged replacement chunks on failure.
        Because replacement chunk IDs are version-specific and disjoint,
        this never affects previous active document versions.
        """
        if not staged_ids:
            return
        try:
            self.collection.delete(ids=staged_ids)
            logger.info("Cleaned up %d staged chunks from ChromaDB", len(staged_ids))
        except Exception as e:
            logger.warning("Error cleaning up staged chunks %s: %s", staged_ids, e)

    def purge_obsolete_chunks(self, document_id: str, active_checksum: str) -> int:
        """
        Deletes chunks belonging to older versions of a document.
        Must only be invoked after PostgreSQL has successfully committed the active checksum update.
        Catches errors and logs a warning without failing the ingestion request.
        """
        try:
            res = self.collection.get(
                where={"document_id": str(document_id)},
                include=["metadatas"],
            )
            obsolete_ids = []
            if res and res.get("ids"):
                for cid, meta in zip(res["ids"], res.get("metadatas", [])):
                    if meta.get("document_checksum") != active_checksum:
                        obsolete_ids.append(cid)

            if obsolete_ids:
                self.collection.delete(ids=obsolete_ids)
                logger.info(
                    "Purged %d obsolete chunks for document %s (active checksum: %s)",
                    len(obsolete_ids),
                    document_id,
                    active_checksum,
                )
                return len(obsolete_ids)
            return 0
        except Exception as e:
            logger.warning(
                "Failed to purge obsolete chunks for document %s (active: %s): %s",
                document_id,
                active_checksum,
                e,
            )
            return 0

    def delete_document_chunks(self, document_id: str) -> None:
        """Removes all chunks associated with a document_id."""
        try:
            # Query existing chunk IDs for this document
            existing = self.collection.get(
                where={"document_id": str(document_id)},
                include=[],
            )
            existing_ids = existing.get("ids", [])
            if existing_ids:
                self.collection.delete(ids=existing_ids)
                logger.info("Deleted %d existing chunks for document %s", len(existing_ids), document_id)
        except Exception as e:
            logger.warning("Could not delete existing chunks for document %s: %s", document_id, e)

    def count_document_chunks(self, document_id: str) -> int:
        """Returns the number of indexed chunks for a document."""
        try:
            res = self.collection.get(
                where={"document_id": str(document_id)},
                include=[],
            )
            return len(res.get("ids", []))
        except Exception:
            return 0

    def query_policy_chunks(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries the vector index for chunks semantically relevant to query_text.
        Computes query embedding via EmbeddingService and queries the collection.
        Returns a list of dicts with chunk_id, text, metadata, and distance.
        """
        if not query_text or not query_text.strip():
            return []

        embedder = get_embedding_service(self.settings.EMBEDDING_MODEL)
        query_vec = embedder.embed_query(query_text)

        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_vec],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        try:
            results = self.collection.query(**kwargs)
        except Exception as e:
            logger.error("ChromaDB query failed: %s", e)
            raise VectorStoreError(f"Vector search failed: {e}") from e

        chunks: List[Dict[str, Any]] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return chunks

        ids = results["ids"][0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for cid, doc, meta, dist in zip(ids, docs, metas, dists):
            chunks.append(
                {
                    "chunk_id": cid,
                    "text": doc,
                    "metadata": meta,
                    "distance": dist,
                }
            )
        return chunks
