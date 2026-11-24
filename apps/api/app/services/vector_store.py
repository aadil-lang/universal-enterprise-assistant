"""
ChromaDB Vector Store Service.
Manages the company_policies collection, storing chunk texts, dense embeddings,
and structured metadata (document_id, filename, title, category, chunk_index, section, page_number, content_hash).
"""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api import ClientAPI
from chromadb.config import Settings as ChromaSettings

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except ImportError:
    QdrantClient = None
    qmodels = None

from app.config.settings import get_settings
from app.schemas.document import DocumentChunk
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Raised when vector store collection operations fail."""
    pass


class QdrantVectorStoreBackend:
    """
    Qdrant Cloud implementation for persistent, high-availability cloud vector search.
    Implements identical interface to ChromaDB VectorStoreService.
    """

    def __init__(self, url: str, api_key: Optional[str] = None, collection_name: str = "company_policies"):
        if QdrantClient is None:
            raise VectorStoreError(
                "qdrant-client package is required for Qdrant vector store. "
                "Install via 'pip install qdrant-client'."
            )
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.settings = get_settings()
        self.client = QdrantClient(url=self.url, api_key=self.api_key, timeout=15.0)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensures the 384-dimensional cosine similarity collection exists."""
        try:
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(size=384, distance=qmodels.Distance.COSINE),
                )
                logger.info("Created Qdrant collection '%s' with 384-dim Cosine distance.", self.collection_name)
        except Exception as e:
            logger.warning("Could not auto-create Qdrant collection '%s': %s", self.collection_name, e)

    def index_document_chunks(
        self,
        document_id: str,
        filename: str,
        title: str,
        category: str,
        chunks: List[DocumentChunk],
    ) -> int:
        if not chunks:
            return 0

        embedder = get_embedding_service(self.settings.EMBEDDING_MODEL)
        texts = [chunk.text for chunk in chunks]
        embeddings = embedder.embed_texts(texts)

        points = []
        point_ids = []
        for chunk, emb in zip(chunks, embeddings):
            # Deterministic UUID from chunk_id
            pid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))
            point_ids.append(pid)
            payload = {
                "chunk_id": chunk.chunk_id,
                "document_id": str(document_id),
                "document_checksum": str(chunk.document_checksum),
                "filename": str(filename),
                "title": str(title),
                "category": str(category),
                "chunk_index": int(chunk.chunk_index),
                "section": str(chunk.section or "General"),
                "page_number": int(chunk.page_number or 0),
                "content_hash": str(chunk.content_hash),
                "text": chunk.text,
            }
            points.append(qmodels.PointStruct(id=pid, vector=emb, payload=payload))

        try:
            self.client.upsert(collection_name=self.collection_name, points=points)
            logger.info("Successfully upserted %d points to Qdrant for doc %s", len(points), document_id)
            return len(points)
        except Exception as err:
            logger.error("Failed to upsert points to Qdrant for document %s: %s", document_id, err)
            raise VectorStoreError(f"Qdrant point upsert failed: {err}") from err

    def cleanup_staged_chunks(self, staged_ids: List[str]) -> None:
        if not staged_ids:
            return
        pids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, cid)) for cid in staged_ids]
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.PointIdsList(points=pids),
            )
        except Exception as e:
            logger.warning("Error cleaning up staged Qdrant points: %s", e)

    def purge_obsolete_chunks(self, document_id: str, active_checksum: str) -> int:
        try:
            filter_doc = qmodels.Filter(
                must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=str(document_id)))]
            )
            hits, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_doc,
                limit=1000,
                with_payload=True,
            )
            obsolete_ids = [
                hit.id for hit in hits
                if hit.payload and hit.payload.get("document_checksum") != active_checksum
            ]
            if obsolete_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=qmodels.PointIdsList(points=obsolete_ids),
                )
                logger.info("Purged %d obsolete Qdrant chunks for doc %s", len(obsolete_ids), document_id)
                return len(obsolete_ids)
            return 0
        except Exception as e:
            logger.warning("Failed to purge obsolete Qdrant chunks: %s", e)
            return 0

    def delete_document_chunks(self, document_id: str) -> None:
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.Filter(
                    must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=str(document_id)))]
                ),
            )
        except Exception as e:
            logger.warning("Error deleting Qdrant document chunks for %s: %s", document_id, e)

    def count_document_chunks(self, document_id: str) -> int:
        try:
            res = self.client.count(
                collection_name=self.collection_name,
                count_filter=qmodels.Filter(
                    must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=str(document_id)))]
                ),
            )
            return res.count
        except Exception:
            return 0

    def query_policy_chunks(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not query_text or not query_text.strip():
            return []

        embedder = get_embedding_service(self.settings.EMBEDDING_MODEL)
        query_vec = embedder.embed_query(query_text)

        qfilter = None
        if where:
            conditions = []
            for k, v in where.items():
                conditions.append(qmodels.FieldCondition(key=k, match=qmodels.MatchValue(value=v)))
            if conditions:
                qfilter = qmodels.Filter(must=conditions)

        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vec,
                limit=n_results,
                query_filter=qfilter,
                with_payload=True,
            )
        except Exception as e:
            logger.error("Qdrant search failed: %s", e)
            raise VectorStoreError(f"Qdrant vector search failed: {e}") from e

        chunks = []
        for hit in hits:
            payload = hit.payload or {}
            chunks.append(
                {
                    "chunk_id": payload.get("chunk_id", str(hit.id)),
                    "text": payload.get("text", ""),
                    "metadata": {
                        "document_id": payload.get("document_id"),
                        "document_checksum": payload.get("document_checksum"),
                        "filename": payload.get("filename"),
                        "title": payload.get("title"),
                        "category": payload.get("category"),
                        "chunk_index": payload.get("chunk_index"),
                        "section": payload.get("section"),
                        "page_number": payload.get("page_number"),
                        "content_hash": payload.get("content_hash"),
                    },
                    "distance": 1.0 - hit.score if hit.score is not None else 0.0,
                }
            )
        return chunks


class VectorStoreService:
    """
    Unified Vector Store Service.
    Seamlessly routes between ChromaDB (local/test) and Qdrant (cloud production).
    """

    def __init__(self, client: Optional[ClientAPI] = None, collection_name: Optional[str] = None):
        self.settings = get_settings()
        self.collection_name = collection_name or self.settings.CHROMA_COLLECTION
        self._backend = None

        is_test_env = os.getenv("PYTEST_CURRENT_TEST") or self.settings.APP_ENV == "test"
        if not is_test_env and self.settings.VECTOR_STORE_PROVIDER == "qdrant" and self.settings.QDRANT_URL:
            logger.info("Initializing QdrantVectorStoreBackend for cloud vector storage.")
            self._backend = QdrantVectorStoreBackend(
                url=self.settings.QDRANT_URL,
                api_key=self.settings.QDRANT_API_KEY,
                collection_name=self.settings.QDRANT_COLLECTION or self.collection_name,
            )
            self.client = None
        else:
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
            persist_dir = os.path.join(os.getcwd(), "data", "chromadb")
            os.makedirs(persist_dir, exist_ok=True)
            logger.warning("Could not connect to ChromaDB HttpClient (%s). Using PersistentClient fallback at '%s'.", e, persist_dir)
            return chromadb.PersistentClient(path=persist_dir)

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
        if self._backend is not None:
            return self._backend.index_document_chunks(
                document_id=document_id,
                filename=filename,
                title=title,
                category=category,
                chunks=chunks,
            )

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
        if self._backend is not None:
            return self._backend.cleanup_staged_chunks(staged_ids)
        if not staged_ids:
            return
        try:
            self.collection.delete(ids=staged_ids)
            logger.info("Cleaned up %d staged chunks from ChromaDB", len(staged_ids))
        except Exception as e:
            logger.warning("Error cleaning up staged chunks %s: %s", staged_ids, e)

    def purge_obsolete_chunks(self, document_id: str, active_checksum: str) -> int:
        if self._backend is not None:
            return self._backend.purge_obsolete_chunks(document_id, active_checksum)
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
        if self._backend is not None:
            return self._backend.delete_document_chunks(document_id)
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
        if self._backend is not None:
            return self._backend.count_document_chunks(document_id)
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
        if self._backend is not None:
            return self._backend.query_policy_chunks(query_text, n_results=n_results, where=where)

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
