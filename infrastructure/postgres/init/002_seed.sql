-- =============================================================================
-- Universal Enterprise HR & IT Assistant - Deterministic Synthetic Seed Data
-- Scope: Acme Corporation (Demonstration Fiscal Year 2026)
-- Authoritative Demonstration Baseline (Idempotent Execution)
-- =============================================================================

-- 1. Employees Fixtures
INSERT INTO employees (
    id, employee_number, first_name, last_name, corporate_email, job_title, department, hire_date, employment_status
) VALUES 
(
    'a0000000-0000-0000-0000-000000000101', 'E101', 'Alice', 'Smith',
    'alice@acme.com', 'HR Director', 'Human Resources', '2021-03-15', 'active'
),
(
    'a0000000-0000-0000-0000-000000000102', 'E102', 'Bob', 'Jones',
    'bob@acme.com', 'Senior Software Engineer', 'Engineering', '2022-06-01', 'active'
),
(
    'a0000000-0000-0000-0000-000000000103', 'E103', 'Carol', 'Davis',
    'carol@acme.com', 'Marketing Specialist', 'Marketing', '2023-01-10', 'active'
),
(
    'a0000000-0000-0000-0000-000000000104', 'E104', 'David', 'Miller',
    'david@acme.com', 'Operations Associate', 'Operations', '2023-04-01', 'terminated'
)
ON CONFLICT (id) DO UPDATE SET
    employee_number = EXCLUDED.employee_number,
    first_name = EXCLUDED.first_name,
    last_name = EXCLUDED.last_name,
    corporate_email = EXCLUDED.corporate_email,
    job_title = EXCLUDED.job_title,
    department = EXCLUDED.department,
    hire_date = EXCLUDED.hire_date,
    employment_status = EXCLUDED.employment_status,
    updated_at = NOW();

-- 2. Application Users (Authentication Principals)
-- Password for all demonstration accounts: Password123!
-- Verified BCrypt hash: $2b$12$cWUuhQr0YEKbHoHu0qm5B.QL9wkX6mqy3SjOwU0HtLKvVoQBHI1Z2 (Cost factor 12)
INSERT INTO app_users (
    id, email, password_hash, role, employee_id, is_active
) VALUES 
(
    'b0000000-0000-0000-0000-000000000101', 'alice@acme.com',
    '$2b$12$cWUuhQr0YEKbHoHu0qm5B.QL9wkX6mqy3SjOwU0HtLKvVoQBHI1Z2',
    'hr_admin', 'a0000000-0000-0000-0000-000000000101', TRUE
),
(
    'b0000000-0000-0000-0000-000000000102', 'bob@acme.com',
    '$2b$12$cWUuhQr0YEKbHoHu0qm5B.QL9wkX6mqy3SjOwU0HtLKvVoQBHI1Z2',
    'employee', 'a0000000-0000-0000-0000-000000000102', TRUE
),
(
    'b0000000-0000-0000-0000-000000000103', 'carol@acme.com',
    '$2b$12$cWUuhQr0YEKbHoHu0qm5B.QL9wkX6mqy3SjOwU0HtLKvVoQBHI1Z2',
    'employee', 'a0000000-0000-0000-0000-000000000103', TRUE
),
(
    'b0000000-0000-0000-0000-000000000104', 'david@acme.com',
    '$2b$12$cWUuhQr0YEKbHoHu0qm5B.QL9wkX6mqy3SjOwU0HtLKvVoQBHI1Z2',
    'employee', 'a0000000-0000-0000-0000-000000000104', FALSE
)
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    employee_id = EXCLUDED.employee_id,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- 3. Leave Balances (Fiscal Year 2026 Baseline)
-- Bob Jones (E102):
--   Annual Leave: 20 accrued, 10 used, 2 pending -> 8 available
--   Sick Leave: 10 accrued, 2 used, 0 pending -> 8 available
INSERT INTO leave_balances (
    id, employee_id, leave_type, accrued_days, used_days, pending_days, fiscal_year
) VALUES 
-- Alice Smith (E101)
(
    'c0000000-0000-0000-0000-000000000101', 'a0000000-0000-0000-0000-000000000101',
    'annual', 25.00, 5.00, 0.00, 2026
),
(
    'c0000000-0000-0000-0000-000000000102', 'a0000000-0000-0000-0000-000000000101',
    'sick', 10.00, 1.00, 0.00, 2026
),
-- Bob Jones (E102) - Target Baseline
(
    'c0000000-0000-0000-0000-000000000103', 'a0000000-0000-0000-0000-000000000102',
    'annual', 20.00, 10.00, 2.00, 2026
),
(
    'c0000000-0000-0000-0000-000000000104', 'a0000000-0000-0000-0000-000000000102',
    'sick', 10.00, 2.00, 0.00, 2026
),
-- Carol Davis (E103)
(
    'c0000000-0000-0000-0000-000000000105', 'a0000000-0000-0000-0000-000000000103',
    'annual', 18.00, 4.00, 0.00, 2026
),
(
    'c0000000-0000-0000-0000-000000000106', 'a0000000-0000-0000-0000-000000000103',
    'sick', 10.00, 0.00, 0.00, 2026
)
ON CONFLICT (employee_id, leave_type, fiscal_year) DO UPDATE SET
    accrued_days = EXCLUDED.accrued_days,
    used_days = EXCLUDED.used_days,
    pending_days = EXCLUDED.pending_days,
    updated_at = NOW();

-- 4. IT Assets
-- Bob Jones (E102): Lenovo ThinkPad T14 (Tag: LT-8821, Serial: SN-994821)
INSERT INTO it_assets (
    id, employee_id, asset_tag, device_type, make_model, serial_number, assigned_date, condition_status
) VALUES 
(
    'd0000000-0000-0000-0000-000000000101', 'a0000000-0000-0000-0000-000000000101',
    'LT-5510', 'laptop', 'Dell Latitude 7420', 'SN-551098', '2021-03-20', 'active'
),
(
    'd0000000-0000-0000-0000-000000000102', 'a0000000-0000-0000-0000-000000000102',
    'LT-8821', 'laptop', 'Lenovo ThinkPad T14', 'SN-994821', '2022-06-05', 'active'
),
(
    'd0000000-0000-0000-0000-000000000103', 'a0000000-0000-0000-0000-000000000103',
    'LT-7740', 'laptop', 'Dell Latitude 5420', 'SN-774012', '2023-01-15', 'active'
)
ON CONFLICT (asset_tag) DO UPDATE SET
    employee_id = EXCLUDED.employee_id,
    device_type = EXCLUDED.device_type,
    make_model = EXCLUDED.make_model,
    serial_number = EXCLUDED.serial_number,
    assigned_date = EXCLUDED.assigned_date,
    condition_status = EXCLUDED.condition_status;

-- 5. IT Support Tickets
-- Bob Jones (E102): Ticket IT-1042 ("VPN connection timeout", Status: open, Priority: medium)
INSERT INTO it_tickets (
    id, employee_id, ticket_number, title, description, category, priority, status
) VALUES 
(
    'e0000000-0000-0000-0000-000000000101', 'a0000000-0000-0000-0000-000000000102',
    'IT-1042', 'VPN connection timeout',
    'VPN timeout on home Wi-Fi after 30 minutes of continuous connection.',
    'VPN', 'medium', 'open'
),
(
    'e0000000-0000-0000-0000-000000000102', 'a0000000-0000-0000-0000-000000000103',
    'IT-1011', 'Second monitor request',
    'Requesting an external 27-inch 4K monitor for marketing graphic layout design.',
    'Hardware', 'low', 'closed'
)
ON CONFLICT (ticket_number) DO UPDATE SET
    employee_id = EXCLUDED.employee_id,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    priority = EXCLUDED.priority,
    status = EXCLUDED.status,
    updated_at = NOW();

-- 6. Document Registry (Calculated Actual SHA-256 Checksums)
-- Preserves existing status, checksum, and chunk_count if document is already indexed
INSERT INTO documents (
    id, title, filename, file_path, category, status, checksum_sha256, chunk_count
) VALUES 
(
    'f0000000-0000-0000-0000-000000000101',
    'Acme Corporation Leave Policy',
    'Acme_Leave_Policy.pdf',
    'data/policies/Acme_Leave_Policy.pdf',
    'HR', 'pending',
    '0a6699566aa259c2262b4adff58b124f756f5c42f49f4559ee40ebfdf59ab771',
    0
),
(
    'f0000000-0000-0000-0000-000000000102',
    'Acme Corporation IT Equipment and Hardware Policy',
    'Acme_IT_Equipment_Policy.docx',
    'data/policies/Acme_IT_Equipment_Policy.docx',
    'IT', 'pending',
    'b7a2c16da4dc2457772499688bc1143ce43f20272c88a650d8b7ffc9d2ef6b14',
    0
),
(
    'f0000000-0000-0000-0000-000000000103',
    'Acme Corporation Remote Work and Ergonomic Policy',
    'Acme_Remote_Work_Policy.md',
    'data/policies/Acme_Remote_Work_Policy.md',
    'HR', 'pending',
    'a25e470d067d14520c0b63300f99637cc4bdd43da88fb784b2031f6d25b7cff4',
    0
)
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    filename = EXCLUDED.filename,
    file_path = EXCLUDED.file_path,
    category = EXCLUDED.category,
    status = CASE WHEN documents.status = 'indexed' THEN documents.status ELSE EXCLUDED.status END,
    checksum_sha256 = CASE WHEN documents.status = 'indexed' THEN documents.checksum_sha256 ELSE EXCLUDED.checksum_sha256 END,
    chunk_count = CASE WHEN documents.status = 'indexed' THEN documents.chunk_count ELSE EXCLUDED.chunk_count END,
    updated_at = NOW();
