"""
Targeted Regression Test Suite for DEF-01: Heading-Boundary-Aware Section Extraction.
Verifies correct section metadata extraction across PDF and DOCX documents:
1. PDF page with multiple headings.
2. PDF content before the first heading assigned to fallback 'General'.
3. DOCX numbered heading using 'Normal' style.
4. DOCX conventional 'Heading' / 'Title' styles.
5. Ordinary numbered paragraph not misclassified as section heading.
6. Section metadata propagation from segments into downstream DocumentChunk objects.
7. Real policy fixtures: Acme Leave Policy (PDF) and Acme IT Equipment Policy (DOCX).
"""

import io
from pathlib import Path
import docx
import pypdf
import pytest

from app.services.chunker import chunk_extracted_segments
from app.services.document_extractor import (
    ExtractedSegment,
    extract_from_docx,
    extract_from_pdf,
    is_section_heading,
)


# ===========================================================================
# 1. Heading Detection Precision Unit Tests
# ===========================================================================
def test_is_section_heading_numbered_headings():
    """Verifies that numbered headings are recognized accurately."""
    assert is_section_heading("1. Purpose and Scope")
    assert is_section_heading("2. Annual Vacation Leave Accrual and Rollover")
    assert is_section_heading("3. Sick Leave Accrual and Carryover")
    assert is_section_heading("1. Standard Hardware Provisioning")
    assert is_section_heading("2. Laptop Refresh and Replacement Cycle")
    assert is_section_heading("Section 1: Introduction")
    assert is_section_heading("Section 2 - Equipment Guidelines")
    assert is_section_heading("1. Overview.")


def test_is_section_heading_rejects_ordinary_numbered_paragraphs():
    """Verifies that ordinary numbered body sentences are not misclassified as headings."""
    long_numbered_p = "1. All employees must submit their expense reports within thirty days of purchase."
    assert not is_section_heading(long_numbered_p)

    long_numbered_rule = "2. Employees who fail to adhere to security protocols will face disciplinary action."
    assert not is_section_heading(long_numbered_rule)

    assert not is_section_heading("Acme Corporation - IT Equipment and Hardware Policy")
    assert not is_section_heading("STATUS: ACTIVE")
    assert not is_section_heading("DOCUMENT ID: POL-HR-2026-02")


# ===========================================================================
# 2. PDF Extraction: Multiple Headings and Pre-heading Content
# ===========================================================================
def test_pdf_multiple_headings_and_pre_heading_content():
    """
    Verifies that a multi-heading PDF page splits into distinct segments,
    with pre-heading content assigned to 'General' and subsequent segments
    assigned their respective section headings.
    """
    # Create an in-memory PDF with pypdf Writer
    writer = pypdf.PdfWriter()
    # We can use the real Acme Leave Policy fixture as it contains pre-heading content and 3 sections on page 1
    pdf_path = Path("data/policies/Acme_Leave_Policy.pdf")
    assert pdf_path.exists(), "Acme_Leave_Policy.pdf fixture must exist"
    content = pdf_path.read_bytes()

    segments = extract_from_pdf(content)
    assert len(segments) >= 3, f"Expected at least 3 segments on multi-heading page, got {len(segments)}"

    # Segment 1 should be pre-heading header/metadata
    assert segments[0].section == "General"
    assert "Employee Leave Policy" in segments[0].text

    # Segment 2 should be Section 1
    assert segments[1].section == "1. Purpose and Scope"
    assert "outlines vacation accrual" in segments[1].text

    # Segment 3 should be Section 2
    assert segments[2].section == "2. Annual Vacation Leave Accrual and Rollover"
    assert "18 days per calendar year" in segments[2].text
    assert "5 days" in segments[2].text

    # Segment 4 should be Section 3
    assert segments[3].section == "3. Sick Leave Accrual and Carryover"
    assert "10 days per calendar year" in segments[3].text


# ===========================================================================
# 3. DOCX Extraction: Normal Style with Numbered Heading & Heading Style
# ===========================================================================
def test_docx_numbered_headings_in_normal_style():
    """
    Verifies that DOCX numbered headings using Word's 'Normal' style
    are properly identified and split into distinct segments.
    """
    doc = docx.Document()
    # Pre-heading title in Normal style
    p_title = doc.add_paragraph("Acme Policy Header")
    p_title.style = "Normal"

    # Numbered heading in Normal style
    p_h1 = doc.add_paragraph("1. Standard Hardware Provisioning")
    p_h1.style = "Normal"
    doc.add_paragraph("Engineering personnel receive a laptop.")

    # Numbered heading in Normal style
    p_h2 = doc.add_paragraph("2. Laptop Refresh and Replacement Cycle")
    p_h2.style = "Normal"
    doc.add_paragraph("Laptops are refreshed every 36 months.")

    # Body sentence that starts with a number (should NOT become a heading)
    doc.add_paragraph("1. All employees must return loaner equipment within three business days of receiving the primary unit.")

    buf = io.BytesIO()
    doc.save(buf)
    content = buf.getvalue()

    segments = extract_from_docx(content)
    assert len(segments) == 3

    assert segments[0].section == "General"
    assert "Acme Policy Header" in segments[0].text

    assert segments[1].section == "1. Standard Hardware Provisioning"
    assert "Engineering personnel receive a laptop" in segments[1].text

    assert segments[2].section == "2. Laptop Refresh and Replacement Cycle"
    assert "36 months" in segments[2].text
    assert "All employees must return loaner equipment" in segments[2].text


def test_docx_conventional_heading_styles():
    """Verifies that standard Word 'Heading 1' and 'Title' styles continue to be detected."""
    doc = docx.Document()
    doc.add_paragraph("Title Overview", style="Title")
    doc.add_paragraph("This is general context.", style="Normal")

    doc.add_paragraph("Security Protocols", style="Heading 1")
    doc.add_paragraph("Connecting via VPN is mandatory.", style="Normal")

    buf = io.BytesIO()
    doc.save(buf)
    content = buf.getvalue()

    segments = extract_from_docx(content)
    assert len(segments) == 2
    assert segments[0].section == "Title Overview"
    assert segments[1].section == "Security Protocols"


# ===========================================================================
# 4. Propagation into Downstream Document Chunks
# ===========================================================================
def test_section_propagation_into_document_chunks():
    """Verifies that extracted section titles correctly propagate into DocumentChunk objects."""
    segments = [
        ExtractedSegment(
            text="2. Annual Vacation Leave Accrual and Rollover\nEmployees accrue 18 days.",
            section="2. Annual Vacation Leave Accrual and Rollover",
            page_number=1,
        )
    ]
    chunks = chunk_extracted_segments(
        document_id="doc-leave-001",
        document_checksum="abc123hash",
        segments=segments,
    )
    assert len(chunks) == 1
    assert chunks[0].section == "2. Annual Vacation Leave Accrual and Rollover"
    assert chunks[0].page_number == 1
    assert "18 days" in chunks[0].text


# ===========================================================================
# 5. Real Policy Fixtures Acceptance Evidence
# ===========================================================================
def test_real_acme_fixtures_section_accuracy():
    """
    Acceptance check on real Acme Corporation policy fixtures:
    - Annual vacation accrual must map to '2. Annual Vacation Leave Accrual and Rollover'.
    - IT laptop refresh must map to '2. Laptop Refresh and Replacement Cycle'.
    """
    # 1. Leave Policy (PDF)
    leave_pdf = Path("data/policies/Acme_Leave_Policy.pdf").read_bytes()
    leave_segments = extract_from_pdf(leave_pdf)
    vacation_seg = [s for s in leave_segments if "18 days per calendar year" in s.text]
    assert len(vacation_seg) == 1
    assert vacation_seg[0].section == "2. Annual Vacation Leave Accrual and Rollover"

    # 2. IT Equipment Policy (DOCX)
    it_docx = Path("data/policies/Acme_IT_Equipment_Policy.docx").read_bytes()
    it_segments = extract_from_docx(it_docx)
    refresh_seg = [s for s in it_segments if "36-month" in s.text]
    assert len(refresh_seg) == 1
    assert refresh_seg[0].section == "2. Laptop Refresh and Replacement Cycle"

    repair_seg = [s for s in it_segments if "broken screens" in s.text]
    assert len(repair_seg) == 1
    assert repair_seg[0].section == "3. Hardware Damage and Screen Repair Policy"
