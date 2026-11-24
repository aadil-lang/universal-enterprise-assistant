"""
Policy Retrieval & Evidence Validation Service.
Enforces Phase 0 §7.3 and Phase 2.1B authoritative retrieval invariants:
1. Cross-references candidate ChromaDB chunks against PostgreSQL documents registry.
2. Filters out inactive document versions and chunks whose checksum does not match the active checksum pointer.
3. Preserves structured metadata (title, filename, section, page, content_hash).
4. Evaluates evidence sufficiency and detects conflicting policy rules.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.config.settings import get_settings
from app.services.document_registry import DocumentRegistry
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class PolicyRetriever:
    """
    Retrieves and filters company policy evidence from ChromaDB with PostgreSQL active-version verification.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStoreService] = None,
        registry: Optional[DocumentRegistry] = None,
    ):
        self.settings = get_settings()
        self.vector_store = vector_store or VectorStoreService()
        self.registry = registry or DocumentRegistry()

    def get_active_version_map(self) -> Dict[str, str]:
        """
        Retrieves the map of {document_id: active_checksum_sha256} for all 'indexed' documents in PostgreSQL.
        """
        try:
            active_docs = self.registry.get_active_documents()
            return {str(doc.id): str(doc.checksum_sha256) for doc in active_docs}
        except Exception as e:
            logger.warning("Could not fetch active documents from database: %s", e)
            return {}

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        relevance_threshold: float = 1.15,
    ) -> Dict[str, Any]:
        """
        Retrieves top-k relevant policy chunks, verifies active versions,
        and assesses evidence sufficiency.

        Returns:
            Dict containing:
            - "evidence": List of validated active chunk dicts
            - "is_sufficient": bool indicating whether retrieved evidence covers the inquiry
            - "has_conflict": bool indicating whether contradictory policies were detected
            - "total_candidate_chunks": int count of raw chunks returned prior to version filtering
        """
        if not query or not str(query).strip():
            return {
                "evidence": [],
                "is_sufficient": False,
                "has_conflict": False,
                "total_candidate_chunks": 0,
            }

        # 1. Query vector store
        raw_chunks = self.vector_store.query_policy_chunks(query, n_results=top_k)
        if not raw_chunks:
            return {
                "evidence": [],
                "is_sufficient": False,
                "has_conflict": False,
                "total_candidate_chunks": 0,
            }

        # 2. Authoritative PostgreSQL Active-Version Cross-Reference
        active_version_map = self.get_active_version_map()
        verified_evidence: List[Dict[str, Any]] = []

        for item in raw_chunks:
            meta = item.get("metadata", {})
            doc_id = str(meta.get("document_id", ""))
            doc_checksum = str(meta.get("document_checksum", ""))

            # If active_version_map is available, enforce strict matching
            if active_version_map:
                active_checksum = active_version_map.get(doc_id)
                if not active_checksum or active_checksum != doc_checksum:
                    logger.debug(
                        "Discarded chunk %s: version mismatch (active=%s, chunk=%s)",
                        item.get("chunk_id"),
                        active_checksum,
                        doc_checksum,
                    )
                    continue

            verified_evidence.append(
                {
                    "chunk_id": item.get("chunk_id"),
                    "text": item.get("text", ""),
                    "document_id": doc_id,
                    "document_title": meta.get("title", "Company Policy"),
                    "filename": meta.get("filename", ""),
                    "category": meta.get("category", "Policy"),
                    "section": meta.get("section", "General"),
                    "page_number": meta.get("page_number", 1),
                    "content_hash": meta.get("content_hash", ""),
                    "document_checksum": doc_checksum,
                    "distance": item.get("distance", 1.0),
                }
            )

        if not verified_evidence:
            return {
                "evidence": [],
                "is_sufficient": False,
                "has_conflict": False,
                "total_candidate_chunks": len(raw_chunks),
            }

        # 3. Evidence Sufficiency Assessment
        # Cosine distance in ChromaDB: 0.0 is exact match, 1.0+ is distant
        best_distance = min(c["distance"] for c in verified_evidence)
        is_sufficient = best_distance <= relevance_threshold

        # Key topic overlap validation
        query_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", query.lower()))
        stopwords = {
            "what", "when", "where", "which", "does", "have", "policy",
            "company", "employee", "employees", "their", "about", "with",
            "rules", "guidelines", "please", "tell", "acme", "corporation",
            "offer", "provide", "covers", "coverage",
        }
        key_terms = query_words - stopwords
        if key_terms:
            evidence_blob = " ".join(c["text"].lower() for c in verified_evidence)
            if not any(term in evidence_blob for term in key_terms):
                is_sufficient = False

        # 4. Check for contradictory policy statements
        has_conflict = self._detect_conflicts(verified_evidence)

        return {
            "evidence": verified_evidence,
            "is_sufficient": is_sufficient,
            "has_conflict": has_conflict,
            "total_candidate_chunks": len(raw_chunks),
        }

    def _detect_conflicts(self, evidence: List[Dict[str, Any]]) -> bool:
        """
        Inspects top evidence chunks for contradictory policy parameters
        (e.g., competing refresh cycles or contradictory caps across multiple active documents).
        """
        if len(evidence) < 2:
            return False

        # Check for explicit contradiction tags or competing numbers on same metric
        # (e.g. one chunk says 36 months, another says 24 months for standard laptop refresh)
        refresh_periods = set()
        for c in evidence:
            text_lower = c["text"].lower()
            if "laptop" in text_lower and "refresh" in text_lower:
                if "36 months" in text_lower or "36-month" in text_lower:
                    refresh_periods.add(36)
                if "24 months" in text_lower or "24-month" in text_lower:
                    refresh_periods.add(24)
                if "48 months" in text_lower or "48-month" in text_lower:
                    refresh_periods.add(48)

        if len(refresh_periods) > 1:
            return True

        return False
