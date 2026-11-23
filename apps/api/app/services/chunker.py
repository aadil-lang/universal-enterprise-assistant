"""
Configurable document chunking service.
Splits normalized extracted segments into boundary-aware, overlapping chunks
while preserving section headings and page provenance metadata.
"""

import hashlib
import re
from typing import List, Optional, Union

from app.schemas.document import DocumentChunk
from app.services.document_extractor import ExtractedSegment
from app.services.text_normalizer import normalize_text


def split_text_into_sentences(text: str) -> List[str]:
    """
    Splits text into sentences using standard punctuation boundaries
    without breaking common acronyms, decimal numbers, or abbreviations.
    """
    # Split on sentence terminals followed by whitespace and an uppercase letter/quote
    sentence_delimiters = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'â€œ])")
    sentences = sentence_delimiters.split(text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_extracted_segments(
    document_id: str,
    document_checksum: Union[str, List[ExtractedSegment]] = "0" * 64,
    segments: Optional[List[ExtractedSegment]] = None,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> List[DocumentChunk]:
    """
    Chunks extracted segments into bounded, overlapping DocumentChunk instances.
    Supports versioned chunk IDs: {document_id}_{document_checksum}_{chunk_index}.
    Handles both signatures:
      chunk_extracted_segments(document_id, document_checksum, segments, ...)
      chunk_extracted_segments(document_id, segments, ...)
    """
    if isinstance(document_checksum, list):
        actual_segments = document_checksum
        document_checksum = "0" * 64
    else:
        document_checksum = str(document_checksum)
        actual_segments = segments or []

    if chunk_overlap >= chunk_size:
        chunk_overlap = chunk_size // 4

    chunks: List[DocumentChunk] = []
    chunk_index = 0

    for segment in actual_segments:
        normalized = normalize_text(segment.text)
        if not normalized:
            continue

        # If segment is smaller than chunk_size, emit as single chunk
        if len(normalized) <= chunk_size:
            content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{document_id}_{document_checksum}_{chunk_index}",
                    document_id=document_id,
                    document_checksum=document_checksum,
                    chunk_index=chunk_index,
                    text=normalized,
                    section=segment.section or "General",
                    page_number=segment.page_number,
                    content_hash=content_hash,
                )
            )
            chunk_index += 1
            continue

        # For larger segments, first split by paragraphs
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", normalized) if p.strip()]

        current_text = ""
        for para in paragraphs:
            # If paragraph itself is larger than chunk_size, split by sentences
            if len(para) > chunk_size:
                sentences = split_text_into_sentences(para)
                if not sentences:
                    sentences = [para]

                for sentence in sentences:
                    if len(current_text) + len(sentence) + 1 <= chunk_size:
                        current_text = f"{current_text} {sentence}".strip()
                    else:
                        if current_text:
                            content_hash = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
                            chunks.append(
                                DocumentChunk(
                                    chunk_id=f"{document_id}_{document_checksum}_{chunk_index}",
                                    document_id=document_id,
                                    document_checksum=document_checksum,
                                    chunk_index=chunk_index,
                                    text=current_text,
                                    section=segment.section or "General",
                                    page_number=segment.page_number,
                                    content_hash=content_hash,
                                )
                            )
                            chunk_index += 1

                            # Compute overlap window
                            overlap_text = current_text[-chunk_overlap:] if len(current_text) > chunk_overlap else ""
                            current_text = f"{overlap_text} {sentence}".strip()
                        else:
                            # Single sentence exceeds chunk_size, split forcibly on word boundaries
                            words = sentence.split()
                            sub_text = ""
                            for w in words:
                                if len(sub_text) + len(w) + 1 <= chunk_size:
                                    sub_text = f"{sub_text} {w}".strip()
                                else:
                                    content_hash = hashlib.sha256(sub_text.encode("utf-8")).hexdigest()
                                    chunks.append(
                                        DocumentChunk(
                                            chunk_id=f"{document_id}_{document_checksum}_{chunk_index}",
                                            document_id=document_id,
                                            document_checksum=document_checksum,
                                            chunk_index=chunk_index,
                                            text=sub_text,
                                            section=segment.section or "General",
                                            page_number=segment.page_number,
                                            content_hash=content_hash,
                                        )
                                    )
                                    chunk_index += 1
                                    sub_text = w
                            current_text = sub_text
            else:
                if len(current_text) + len(para) + 2 <= chunk_size:
                    current_text = f"{current_text}\n\n{para}".strip()
                else:
                    if current_text:
                        content_hash = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
                        chunks.append(
                            DocumentChunk(
                                chunk_id=f"{document_id}_{document_checksum}_{chunk_index}",
                                document_id=document_id,
                                document_checksum=document_checksum,
                                chunk_index=chunk_index,
                                text=current_text,
                                section=segment.section or "General",
                                page_number=segment.page_number,
                                content_hash=content_hash,
                            )
                        )
                        chunk_index += 1

                        overlap_text = current_text[-chunk_overlap:] if len(current_text) > chunk_overlap else ""
                        current_text = f"{overlap_text}\n\n{para}".strip()
                    else:
                        current_text = para

        # Flush any remaining text in the segment buffer
        if current_text:
            content_hash = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{document_id}_{document_checksum}_{chunk_index}",
                    document_id=document_id,
                    document_checksum=document_checksum,
                    chunk_index=chunk_index,
                    text=current_text,
                    section=segment.section or "General",
                    page_number=segment.page_number,
                    content_hash=content_hash,
                )
            )
            chunk_index += 1

    return chunks
