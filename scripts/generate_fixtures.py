"""
Script to generate genuine, readable PDF and DOCX policy fixtures for Acme Corporation.
Strictly adheres to approved Phase 0 v1.7.0 ground truth policy facts.
"""
import os
import zipfile

def generate_pdf(file_path: str):
    """
    Generates a syntactically valid, readable PDF 1.4 document containing
    authoritative Acme Corporation Leave Policy facts.
    """
    # Stream text strictly containing approved leave policy rules:
    # - Annual vacation accrual: 18 days/year; maximum 5 days rollover per calendar year.
    # - Sick leave: 10 days/year; maximum 5 days rollover per calendar year.
    stream_content = """BT
/F1 18 Tf
50 720 Td
(Acme Corporation - Employee Leave Policy) Tj
0 -30 Td
/F2 10 Tf
(Document ID: POL-HR-2026-02  |  Effective Date: January 1, 2026  |  Status: Active) Tj
0 -40 Td
/F1 14 Tf
(1. Purpose and Scope) Tj
0 -20 Td
/F2 11 Tf
(This policy outlines vacation accrual, sick leave, and rollover rules for all Acme Corporation employees.) Tj
0 -30 Td
/F1 14 Tf
(2. Annual Vacation Leave Accrual and Rollover) Tj
0 -20 Td
/F2 11 Tf
(Acme employees accrue annual vacation leave at a rate of 18 days per calendar year.) Tj
0 -18 Td
(Unused vacation days may be rolled over into the next fiscal year, up to a maximum rollover cap of 5 days.) Tj
0 -18 Td
(Any accrued vacation beyond the 5-day rollover cap is forfeited at the end of the calendar year.) Tj
0 -30 Td
/F1 14 Tf
(3. Sick Leave Accrual and Carryover) Tj
0 -20 Td
/F2 11 Tf
(Employees accrue sick leave at a rate of 10 days per calendar year.) Tj
0 -18 Td
(Unused sick leave can be carried over into subsequent years up to a maximum rollover cap of 5 days.) Tj
ET"""

    stream_bytes = stream_content.encode("latin1")
    stream_len = len(stream_bytes)

    header = "%PDF-1.4\n"
    obj1 = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        "3 0 obj\n"
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R\n"
        "   /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >>\n"
        ">>\nendobj\n"
    )
    obj4_header = f"4 0 obj\n<< /Length {stream_len} >>\nstream\n"
    obj4_footer = "\nendstream\nendobj\n"
    obj5 = "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n"
    obj6 = "6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    # Compute exact byte offsets for xref
    pos = len(header.encode("latin1"))
    offset1 = pos
    pos += len(obj1.encode("latin1"))
    offset2 = pos
    pos += len(obj2.encode("latin1"))
    offset3 = pos
    pos += len(obj3.encode("latin1"))
    offset4 = pos
    pos += len(obj4_header.encode("latin1")) + stream_len + len(obj4_footer.encode("latin1"))
    offset5 = pos
    pos += len(obj5.encode("latin1"))
    offset6 = pos
    pos += len(obj6.encode("latin1"))
    xref_offset = pos

    xref = (
        "xref\n"
        "0 7\n"
        "0000000000 65535 f \n"
        f"{offset1:010d} 00000 n \n"
        f"{offset2:010d} 00000 n \n"
        f"{offset3:010d} 00000 n \n"
        f"{offset4:010d} 00000 n \n"
        f"{offset5:010d} 00000 n \n"
        f"{offset6:010d} 00000 n \n"
        "trailer\n"
        "<< /Size 7 /Root 1 0 R >>\n"
        "startxref\n"
        f"{xref_offset}\n"
        "%%EOF\n"
    )

    pdf_bytes = (
        header.encode("latin1")
        + obj1.encode("latin1")
        + obj2.encode("latin1")
        + obj3.encode("latin1")
        + obj4_header.encode("latin1")
        + stream_bytes
        + obj4_footer.encode("latin1")
        + obj5.encode("latin1")
        + obj6.encode("latin1")
        + xref.encode("latin1")
    )

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"Generated PDF at: {file_path} ({len(pdf_bytes)} bytes)")


def generate_docx(file_path: str):
    """
    Generates a genuine Microsoft Word OpenXML (.docx) file containing
    authoritative Acme Corporation IT Equipment Policy facts.
    """
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr><w:t>Acme Corporation - IT Equipment and Hardware Policy</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:rPr><w:i/><w:sz w:val="22"/></w:rPr><w:t>Document ID: POL-IT-2026-01 | Effective Date: January 1, 2026 | Status: Active</w:t></w:r>
    </w:p>
    <w:p><w:r><w:t></w:t></w:r></w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading2"/></w:pPr>
      <w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:t>1. Standard Hardware Provisioning</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:sz w:val="24"/><w:t>All engineering personnel are assigned standard company-managed laptops upon hire. The standard engineering laptop model is the Lenovo ThinkPad T14 equipped with 32GB RAM and 512GB SSD storage.</w:t></w:r>
    </w:p>
    <w:p><w:r><w:t></w:t></w:r></w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading2"/></w:pPr>
      <w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:t>2. Laptop Refresh and Replacement Cycle</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:sz w:val="24"/><w:t>Standard company laptops are subject to a mandatory 36-month refresh cycle from their initial assignment date. Employees eligible for replacement will receive instructions from IT Support to transition to a refreshed unit.</w:t></w:r>
    </w:p>
    <w:p><w:r><w:t></w:t></w:r></w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading2"/></w:pPr>
      <w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:t>3. Hardware Damage and Screen Repair Policy</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:sz w:val="24"/><w:t>In the event of hardware damage or malfunctioning components, broken screens must be reported through an IT ticket within 24 hours of occurrence. Loaner equipment will be provided while repairs are conducted.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"""

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document_xml)
    print(f"Generated DOCX at: {file_path}")


if __name__ == "__main__":
    generate_pdf("data/policies/Acme_Leave_Policy.pdf")
    generate_docx("data/policies/Acme_IT_Equipment_Policy.docx")
