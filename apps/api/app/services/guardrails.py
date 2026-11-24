"""
Input & Output Security Guardrails.
Enforces Phase 0 §8.2 requirements:
1. Heuristic and pattern-based prompt injection detection.
2. Context-aware PII redaction of unauthorized sensitive entities (credit cards, SSNs)
   while preserving legitimate operational employee data.
3. Citation validation against retrieved document chunks.
4. Output sanitization and safe refusal generation.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Heuristic signatures for prompt injection, jailbreaks, and rule subversion
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|prompts)", re.IGNORECASE),
    re.compile(r"(reveal|print|display|show|output)\s+(the\s+)?(system\s+prompt|developer\s+instructions|secret\s+key)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|dan\s+mode|unrestricted|god\s+mode)", re.IGNORECASE),
    re.compile(r"bypass\s+(all\s+)?(security|guardrails|filters|restrictions)", re.IGNORECASE),
    re.compile(r"system\s*[:\s]\s*(override|reset|award|grant|delete)", re.IGNORECASE),
    re.compile(r"\b(drop\s+table|delete\s+from|grant\s+admin|insert\s+into|update\s+\w+\s+set)\b", re.IGNORECASE),
    re.compile(r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]", re.IGNORECASE),
]

# Sensitive PII patterns (Credit Cards, SSNs)
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Citation pattern: e.g. [Acme Leave Policy, Sick Leave Accrual] or [Acme IT Equipment Policy]
CITATION_REGEX = re.compile(r"\[([^\[\]]+)\]")


class GuardrailService:
    """Provides pre-flight input inspection and post-flight response validation."""

    @staticmethod
    def inspect_input(query: str, max_chars: int = 2000) -> Dict[str, Any]:
        """
        Pre-flight check:
        1. Length and non-empty validation.
        2. Prompt injection detection.
        3. Non-authorized PII redaction.
        """
        if not query or not str(query).strip():
            return {
                "is_valid": False,
                "sanitized_query": "",
                "injection_detected": False,
                "refusal_reason": "Query cannot be empty.",
            }

        cleaned = str(query).strip()
        if len(cleaned) > max_chars:
            return {
                "is_valid": False,
                "sanitized_query": cleaned[:max_chars],
                "injection_detected": False,
                "refusal_reason": f"Query exceeds maximum permitted length of {max_chars} characters.",
            }

        # Check prompt injection patterns
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(cleaned):
                logger.warning("Prompt injection signature detected in user input: %s", cleaned)
                return {
                    "is_valid": False,
                    "sanitized_query": cleaned,
                    "injection_detected": True,
                    "refusal_reason": "I cannot fulfill this request as it contains unauthorized instructions or prompt injection attempts.",
                }

        # Context-aware PII masking: Mask CC and SSN
        masked_query = CREDIT_CARD_REGEX.sub("[REDACTED_CARD]", cleaned)
        masked_query = SSN_REGEX.sub("[REDACTED_SSN]", masked_query)

        return {
            "is_valid": True,
            "sanitized_query": masked_query,
            "injection_detected": False,
            "refusal_reason": None,
        }

    @staticmethod
    def validate_citations(
        response_text: str,
        retrieved_evidence: List[Dict[str, Any]],
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Post-flight check:
        Verifies that cited sources exist in the retrieved evidence chunks.
        Extracts verified citations and leaves legitimate text intact.
        """
        if not response_text:
            return "", []

        # Build known document and section index from retrieved evidence
        known_sources = set()
        evidence_by_title = {}
        for ev in retrieved_evidence:
            title = ev.get("document_title", "").strip().lower()
            section = ev.get("section", "").strip().lower()
            filename = ev.get("filename", "").strip().lower()

            if title:
                known_sources.add(title)
                evidence_by_title[title] = ev
            if filename:
                known_sources.add(filename)
                evidence_by_title[filename] = ev
            if title and section:
                known_sources.add(f"{title}, {section}")

        verified_citations: List[Dict[str, Any]] = []
        found_matches = CITATION_REGEX.findall(response_text)

        for match_str in found_matches:
            match_clean = match_str.strip()
            match_lower = match_clean.lower()

            # Ignore structural tags, markdown checkboxes, etc.
            if match_lower in ("x", " ", "todo", "redacted_card", "redacted_ssn"):
                continue

            # Check if citation corresponds to any retrieved evidence
            is_verified = any(k in match_lower for k in known_sources)

            if is_verified:
                # Find matching evidence piece
                parts = [p.strip() for p in match_clean.split(",")]
                doc_name = parts[0]
                sec_name = parts[1] if len(parts) > 1 else None

                # Locate corresponding chunk metadata
                matched_ev = None
                for ev in retrieved_evidence:
                    doc_match = doc_name.lower() in ev.get("document_title", "").lower() or doc_name.lower() in ev.get("filename", "").lower()
                    sec_match = sec_name and (sec_name.lower() in ev.get("section", "").lower() or ev.get("section", "").lower() in sec_name.lower())
                    if doc_match and sec_match:
                        matched_ev = ev
                        break
                if not matched_ev:
                    for ev in retrieved_evidence:
                        if doc_name.lower() in ev.get("document_title", "").lower() or doc_name.lower() in ev.get("filename", "").lower():
                            matched_ev = ev
                            break

                citation_meta = {
                    "document_title": matched_ev.get("document_title") if matched_ev else doc_name,
                    "filename": matched_ev.get("filename") if matched_ev else "",
                    "section": sec_name or (matched_ev.get("section") if matched_ev else "General"),
                    "page_number": matched_ev.get("page_number", 1) if matched_ev else 1,
                    "content_hash": matched_ev.get("content_hash", "") if matched_ev else "",
                }
                if citation_meta not in verified_citations:
                    verified_citations.append(citation_meta)

        # Sanitize output from any leaked non-operational PII
        sanitized_output = CREDIT_CARD_REGEX.sub("[REDACTED_CARD]", response_text)
        sanitized_output = SSN_REGEX.sub("[REDACTED_SSN]", sanitized_output)

        return sanitized_output, verified_citations
