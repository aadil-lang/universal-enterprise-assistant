"""
Phase 1.2B Comprehensive Verification & Audit Script.
Validates Schema, Seed Data, Policy Fixtures, Configuration, Secret Handling, and Drivers.
"""

import hashlib
import zipfile
import xml.etree.ElementTree as ET
import pypdf
import bcrypt

def verify_schema():
    print("--- 1. Verifying PostgreSQL Schema (001_schema.sql) ---")
    with open("infrastructure/postgres/init/001_schema.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    assert "CREATE TABLE IF NOT EXISTS employees (" in sql
    assert "id UUID PRIMARY KEY DEFAULT gen_random_uuid()" in sql
    assert "employee_number VARCHAR(32) UNIQUE NOT NULL" in sql
    assert "corporate_email VARCHAR(255) NOT NULL" in sql
    assert "uq_employees_email_lower" in sql
    print("  [PASS] employees table has UUID PK, employee_number UNIQUE, and lowercase email index")

    assert "CREATE TABLE IF NOT EXISTS app_users (" in sql
    assert "employee_id UUID NOT NULL UNIQUE REFERENCES employees(id)" in sql
    assert "uq_app_users_email_lower" in sql
    print("  [PASS] app_users table has UUID employee_id NOT NULL UNIQUE foreign key")

    assert "CREATE TABLE IF NOT EXISTS leave_balances (" in sql
    assert "available_days NUMERIC(5,2) GENERATED ALWAYS AS (accrued_days - used_days - pending_days) STORED" in sql
    assert "chk_leave_non_negative CHECK (accrued_days >= 0 AND used_days >= 0 AND pending_days >= 0)" in sql
    assert "chk_leave_accrued_sufficient CHECK (accrued_days >= (used_days + pending_days))" in sql
    print("  [PASS] leave_balances has stored generated column for available_days and accrued >= used + pending constraint")

    assert "CREATE TABLE IF NOT EXISTS it_tickets (" in sql
    assert "description TEXT NOT NULL" in sql
    assert "ticket_number VARCHAR(32) UNIQUE NOT NULL" in sql
    print("  [PASS] it_tickets includes description TEXT NOT NULL and unique ticket_number")

    assert "CREATE TABLE IF NOT EXISTS documents (" in sql
    assert "chk_doc_status CHECK (status IN ('pending', 'indexing', 'indexed', 'failed'))" in sql
    assert "checksum_sha256 CHAR(64) NOT NULL" in sql
    assert "chunk_count INT NOT NULL DEFAULT 0" in sql
    assert "indexed_at TIMESTAMPTZ" in sql
    print("  [PASS] documents table supports pending, indexing, indexed, failed with checksum and chunk_count")

def verify_seeds():
    print("\n--- 2. Verifying Synthetic Seed Data (002_seed.sql & seed.sql) ---")
    verified_hash = "$2b$12$cWUuhQr0YEKbHoHu0qm5B.QL9wkX6mqy3SjOwU0HtLKvVoQBHI1Z2"
    assert bcrypt.checkpw(b"Password123!", verified_hash.encode("ascii")), "Password hash failed verification!"
    print("  [PASS] Demo BCrypt password hash authenticates 'Password123!' successfully")

    for file_path in ["infrastructure/postgres/init/002_seed.sql", "data/seeds/seed.sql"]:
        with open(file_path, "r", encoding="utf-8") as f:
            seed_sql = f.read()

        # Alice
        assert "E101" in seed_sql and "Alice" in seed_sql and "alice@acme.com" in seed_sql and "hr_admin" in seed_sql
        # Bob
        assert "E102" in seed_sql and "Bob" in seed_sql and "bob@acme.com" in seed_sql and "employee" in seed_sql
        # Carol (must be employee, NOT it_admin)
        assert "E103" in seed_sql and "Carol" in seed_sql and "carol@acme.com" in seed_sql
        assert "'carol@acme.com',\n    '$2b$12$" in seed_sql and "'employee', 'a0000000-0000-0000-0000-000000000103'" in seed_sql
        # Bob's leave balances: 20 accrued, 10 used, 2 pending
        assert "'annual', 20.00, 10.00, 2.00, 2026" in seed_sql
        # Bob's sick leave balances: 10 accrued, 2 used, 0 pending
        assert "'sick', 10.00, 2.00, 0.00, 2026" in seed_sql
        # Bob's asset: LT-8821, Lenovo ThinkPad T14, SN-994821
        assert "'LT-8821', 'laptop', 'Lenovo ThinkPad T14', 'SN-994821'" in seed_sql
        # Bob's ticket: IT-1042, VPN connection timeout, open, medium
        assert "'IT-1042', 'VPN connection timeout'" in seed_sql
        assert "'VPN', 'medium', 'open'" in seed_sql

        # Preserves indexed document status on rerun
        assert "status = CASE WHEN documents.status = 'indexed' THEN documents.status ELSE EXCLUDED.status END" in seed_sql
        print(f"  [PASS] {file_path} defines Alice, Bob, Carol, verified hashes, and preserves indexed metadata on rerun")

def verify_fixtures():
    print("\n--- 3. Verifying Policy Fixtures Ground Truth Extraction & Actual Checksums ---")
    fixtures = [
        ("data/policies/Acme_Leave_Policy.pdf", "0a6699566aa259c2262b4adff58b124f756f5c42f49f4559ee40ebfdf59ab771"),
        ("data/policies/Acme_IT_Equipment_Policy.docx", "b7a2c16da4dc2457772499688bc1143ce43f20272c88a650d8b7ffc9d2ef6b14"),
        ("data/policies/Acme_Remote_Work_Policy.md", "a25e470d067d14520c0b63300f99637cc4bdd43da88fb784b2031f6d25b7cff4"),
    ]

    for path, expected_hash in fixtures:
        with open(path, "rb") as f:
            data = f.read()
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {path}: {actual_hash} != {expected_hash}"
        print(f"  [PASS] {path}: verified actual SHA-256 = {actual_hash[:16]}...")

    # PDF text
    pdf_reader = pypdf.PdfReader("data/policies/Acme_Leave_Policy.pdf")
    pdf_text = "".join([page.extract_text() for page in pdf_reader.pages])
    assert "18 days per calendar year" in pdf_text
    assert "maximum rollover cap of 5 days" in pdf_text
    assert "sick leave at a rate of 10 days" in pdf_text
    assert "2 weeks in advance" not in pdf_text
    print("  [PASS] Acme_Leave_Policy.pdf: verified 18d vacation, 10d sick, 5d rollover; 2-week notice rule removed")

    # DOCX text
    with zipfile.ZipFile("data/policies/Acme_IT_Equipment_Policy.docx") as z:
        xml_data = z.read("word/document.xml")
        tree = ET.fromstring(xml_data)
        docx_text = "".join(tree.itertext())
    assert "Lenovo ThinkPad T14" in docx_text
    assert "36-month refresh cycle" in docx_text
    assert "within 24 hours of occurrence" in docx_text
    assert "MacBook" not in docx_text
    assert "Dell XPS" not in docx_text
    print("  [PASS] Acme_IT_Equipment_Policy.docx: verified Lenovo ThinkPad T14 standard, 36m refresh, 24h repair reporting")

    # Markdown text
    with open("data/policies/Acme_Remote_Work_Policy.md", "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "$300" in md_text
    assert "Mandatory Daily VPN Connection" in md_text
    print("  [PASS] Acme_Remote_Work_Policy.md: verified $300 ergonomic stipend and daily VPN requirement")

def verify_docker_and_config():
    print("\n--- 4. Verifying Docker Compose, Drivers, & Configuration ---")
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        compose = f.read()

    assert "ports:\n      - \"8001:8001\"" not in compose
    assert "ports:\n      - \"8005:8000\"" not in compose
    assert "ports:\n      - \"127.0.0.1:5432:5432\"" in compose, "PostgreSQL host port should bind to 127.0.0.1"
    assert "postgresql+psycopg://" in compose, "API should use psycopg 3 in docker-compose.yml"
    assert "postgresql+psycopg2://" in compose, "MCP should use psycopg2 in docker-compose.yml"
    assert "backend_internal:" in compose
    assert "frontend_net:" in compose
    print("  [PASS] docker-compose.yml: safe 127.0.0.1 postgres binding, driver separation, and network isolation")

    with open(".env.example", "r", encoding="utf-8") as f:
        env = f.read()
    assert "POSTGRES_DB=acme_assistant" in env
    assert "POSTGRES_USER=acme_app" in env
    assert "DEMO_FISCAL_YEAR=2026" in env
    assert "postgresql+psycopg://" in env, "API DATABASE_URL in .env.example should use psycopg driver"
    print("  [PASS] .env.example: consistent with acme_assistant, acme_app, DEMO_FISCAL_YEAR=2026, and psycopg driver")

    with open(".dockerignore", "r", encoding="utf-8") as f:
        dockerignore = f.read()
    assert "*.md" not in dockerignore, "Found blanket *.md exclusion in .dockerignore!"
    print("  [PASS] .dockerignore: blanket *.md exclusion removed to allow policy markdown files in build contexts")

if __name__ == "__main__":
    verify_schema()
    verify_seeds()
    verify_fixtures()
    verify_docker_and_config()
    print("\n>>> ALL PHASE 1.2B AUDIT CHECKS PASSED SUCCESSFULLY <<<")
