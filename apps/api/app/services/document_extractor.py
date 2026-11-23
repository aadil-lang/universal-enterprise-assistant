"""
Document text extraction service.
Extracts readable text, page numbers, and section hierarchy across PDF, DOCX, TXT, and Markdown.
"""

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from typing import List, Optional

import pypdf

from app.services.document_validation import EmptyDocumentError, MalformedDocumentError


@dataclass
class ExtractedSegment:
    """Represents a coherent segment of text extracted with structural provenance."""
    text: str
    section: str = "General"
    page_number: int = 0  # 1-indexed for PDF, 0 for flow documents (DOCX, TXT, MD)


def is_section_heading(text: str) -> bool:
    """
    Conservatively detects whether a line or paragraph represents a structural section heading.
    Prevents ordinary numbered list items or body sentences from being misclassified as headings.
    """
    stripped = text.strip()
    if not stripped or len(stripped) > 80:
        return False

    numbered_match = re.match(
        r"^(?:Section\s+\d+|[0-9]+(?:\.[0-9]+)*)(?:\s*[:\-\.]|\.)?\s+(.*)$",
        stripped,
        re.I,
    )
    if numbered_match:
        title_body = numbered_match.group(1).strip()
        words = title_body.split()
        if len(words) <= 10 and bool(re.match(r"^[A-Z]", title_body)):
            if stripped.endswith((".", ";", ",")):
                return len(words) <= 4
            return True
        return False

    if len(stripped) < 60 and stripped.isupper() and len(stripped.split()) <= 8:
        if not re.match(r"^(?:STATUS|DOCUMENT ID|DATE|VERSION|AUTHOR|CATEGORY):", stripped):
            return True

    return False


def extract_from_pdf(content: bytes) -> List[ExtractedSegment]:
    """
    Extracts text from PDF bytes page by page using pypdf.
    Preserves 1-indexed page numbers and detects heading boundaries throughout each page.
    Splits page content into ordered segments introduced by their respective section headings.
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
    except Exception as e:
        raise MalformedDocumentError(f"Failed to parse PDF document: {e}") from e

    segments: List[ExtractedSegment] = []
    current_section = "General"

    for page_idx, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception as e:
            raise MalformedDocumentError(f"Failed to extract text from PDF page {page_idx}: {e}") from e

        cleaned_page = page_text.strip()
        if not cleaned_page:
            continue

        lines = cleaned_page.splitlines()
        page_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if is_section_heading(stripped):
                # Flush previous segment if accumulated on this page
                if page_lines:
                    text_block = "\n".join(page_lines).strip()
                    if text_block:
                        segments.append(
                            ExtractedSegment(
                                text=text_block,
                                section=current_section,
                                page_number=page_idx,
                            )
                        )
                    page_lines = []
                current_section = stripped[:80]
                page_lines.append(stripped)
            else:
                page_lines.append(stripped)

        if page_lines:
            text_block = "\n".join(page_lines).strip()
            if text_block:
                segments.append(
                    ExtractedSegment(
                        text=text_block,
                        section=current_section,
                        page_number=page_idx,
                    )
                )

    if not segments:
        raise EmptyDocumentError("PDF document contains no extractable text.")

    return segments


def extract_from_docx(content: bytes) -> List[ExtractedSegment]:
    """
    Extracts paragraphs and tables from DOCX bytes with section heading detection.
    Supports Word Heading/Title styles as well as numbered section headings in Normal style.
    Supports python-docx with transparent fallback to zipfile/ElementTree.
    """
    segments: List[ExtractedSegment] = []
    current_section = "General"
    current_chunk_lines: List[str] = []

    try:
        import docx
        doc = docx.Document(io.BytesIO(content))

        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue

            style_name = getattr(paragraph.style, "name", "")
            is_heading = ("Heading" in style_name or "Title" in style_name) or is_section_heading(text)

            if is_heading:
                # Flush previous segment if accumulated
                if current_chunk_lines:
                    text_block = "\n".join(current_chunk_lines).strip()
                    if text_block:
                        segments.append(
                            ExtractedSegment(
                                text=text_block,
                                section=current_section,
                                page_number=0,
                            )
                        )
                    current_chunk_lines = []
                current_section = text[:80]
                current_chunk_lines.append(text)
            else:
                current_chunk_lines.append(text)

        # Also extract table text
        for table in doc.tables:
            table_rows: List[str] = []
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    table_rows.append(" | ".join(row_cells))
            if table_rows:
                current_chunk_lines.append("\n".join(table_rows))

    except Exception:
        # Fallback to pure zipfile XML extraction
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                xml_data = z.read("word/document.xml")
                root = ET.fromstring(xml_data)
                # Word XML namespace
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                for p in root.findall(".//w:p", ns):
                    p_text = "".join(node.text for node in p.findall(".//w:t", ns) if node.text).strip()
                    if p_text:
                        if is_section_heading(p_text):
                            if current_chunk_lines:
                                text_block = "\n".join(current_chunk_lines).strip()
                                if text_block:
                                    segments.append(
                                        ExtractedSegment(
                                            text=text_block,
                                            section=current_section,
                                            page_number=0,
                                        )
                                    )
                                current_chunk_lines = []
                            current_section = p_text[:80]
                        current_chunk_lines.append(p_text)
        except Exception as e:
            raise MalformedDocumentError(f"Failed to parse DOCX document: {e}") from e

    if current_chunk_lines:
        text_block = "\n".join(current_chunk_lines).strip()
        if text_block:
            segments.append(
                ExtractedSegment(
                    text=text_block,
                    section=current_section,
                    page_number=0,
                )
            )

    if not segments:
        raise EmptyDocumentError("DOCX document contains no extractable text.")

    return segments


def extract_from_markdown(content: bytes) -> List[ExtractedSegment]:
    """
    Extracts text from Markdown bytes, partitioning by headings (#, ##, ###) for section context.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as e:
            raise MalformedDocumentError(f"Failed to decode Markdown file: {e}") from e

    if not text.strip():
        raise EmptyDocumentError("Markdown document is empty.")

    segments: List[ExtractedSegment] = []
    lines = text.splitlines()
    current_section = "General"
    current_lines: List[str] = []

    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")

    for line in lines:
        match = heading_pattern.match(line.strip())
        if match:
            # Flush existing section text
            if current_lines:
                combined = "\n".join(current_lines).strip()
                if combined:
                    segments.append(
                        ExtractedSegment(
                            text=combined,
                            section=current_section,
                            page_number=0,
                        )
                    )
                current_lines = []
            current_section = match.group(2).strip()[:80]
            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_lines:
        combined = "\n".join(current_lines).strip()
        if combined:
            segments.append(
                ExtractedSegment(
                    text=combined,
                    section=current_section,
                    page_number=0,
                )
            )

    if not segments:
        raise EmptyDocumentError("Markdown document contains no extractable text.")

    return segments


def extract_from_txt(content: bytes) -> List[ExtractedSegment]:
    """
    Extracts text from plain text bytes, identifying paragraph blocks and inferred section headers.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as e:
            raise MalformedDocumentError(f"Failed to decode text file: {e}") from e

    if not text.strip():
        raise EmptyDocumentError("Text document is empty.")

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        raise EmptyDocumentError("Text document contains no readable paragraphs.")

    segments: List[ExtractedSegment] = []
    current_section = "General"

    for para in paragraphs:
        first_line = para.splitlines()[0].strip()
        if len(first_line) < 60 and (first_line.isupper() or re.match(r"^(?:Section|\d+\.)", first_line)):
            current_section = first_line[:80]

        segments.append(
            ExtractedSegment(
                text=para,
                section=current_section,
                page_number=0,
            )
        )

    return segments


def extract_text_from_document(filename: str, content: bytes) -> List[ExtractedSegment]:
    """
    Universal extractor dispatching to format-specific extractors based on filename extension.
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == ".pdf":
        return extract_from_pdf(content)
    elif ext == ".docx":
        return extract_from_docx(content)
    elif ext == ".md":
        return extract_from_markdown(content)
    elif ext == ".txt":
        return extract_from_txt(content)
    else:
        raise MalformedDocumentError(f"Unsupported document format: {ext}")
