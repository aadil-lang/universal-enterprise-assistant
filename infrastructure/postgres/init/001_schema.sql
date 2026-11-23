-- =============================================================================
-- Universal Enterprise HR & IT Assistant - PostgreSQL 16 Schema Foundation
-- Scope: Acme Corporation (Single-Company Assignment MVP)
-- =============================================================================

-- Enable pgcrypto / uuid-ossp for gen_random_uuid() if required
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Employees (Operational HR Demographic Profile)
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_number VARCHAR(32) UNIQUE NOT NULL, -- e.g., 'E101', 'E102', 'E103'
    first_name VARCHAR(128) NOT NULL,
    last_name VARCHAR(128) NOT NULL,
    corporate_email VARCHAR(255) NOT NULL,
    job_title VARCHAR(128) NOT NULL,
    department VARCHAR(64) NOT NULL,
    hire_date DATE NOT NULL,
    employment_status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_emp_status CHECK (employment_status IN ('active', 'on_leave', 'terminated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_employees_email_lower 
ON employees (LOWER(corporate_email));

-- 2. Application Users (Authentication Principals)
-- 1:1 relationship with employees; all demonstration accounts represent Acme employees
CREATE TABLE IF NOT EXISTS app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'employee',
    employee_id UUID NOT NULL UNIQUE REFERENCES employees(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_user_role CHECK (role IN ('employee', 'hr_admin'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_app_users_email_lower 
ON app_users (LOWER(email));

-- 3. Leave Balances (MCP Target)
-- Available leave is derived via STORED generated column: (accrued_days - used_days - pending_days)
-- fiscal_year is explicitly provided from central DEMO_FISCAL_YEAR (no database default)
CREATE TABLE IF NOT EXISTS leave_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type VARCHAR(32) NOT NULL,
    accrued_days NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    used_days NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    pending_days NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    available_days NUMERIC(5,2) GENERATED ALWAYS AS (accrued_days - used_days - pending_days) STORED,
    fiscal_year INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_emp_leave UNIQUE (employee_id, leave_type, fiscal_year),
    CONSTRAINT chk_leave_type CHECK (leave_type IN ('annual', 'sick')),
    CONSTRAINT chk_leave_non_negative CHECK (accrued_days >= 0 AND used_days >= 0 AND pending_days >= 0),
    CONSTRAINT chk_leave_accrued_sufficient CHECK (accrued_days >= (used_days + pending_days))
);

-- 4. IT Assets (Hardware Assigned to Employees)
CREATE TABLE IF NOT EXISTS it_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID REFERENCES employees(id) ON DELETE SET NULL,
    asset_tag VARCHAR(64) UNIQUE NOT NULL, -- e.g., 'LT-8821'
    device_type VARCHAR(64) NOT NULL,      -- e.g., 'laptop', 'monitor'
    make_model VARCHAR(128) NOT NULL,      -- e.g., 'Lenovo ThinkPad T14'
    serial_number VARCHAR(128) NOT NULL,
    assigned_date DATE,
    condition_status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_asset_type CHECK (device_type IN ('laptop', 'monitor', 'phone', 'yubikey')),
    CONSTRAINT chk_asset_status CHECK (condition_status IN ('active', 'in_repair', 'retired', 'lost'))
);

-- 5. IT Support Tickets
CREATE TABLE IF NOT EXISTS it_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    ticket_number VARCHAR(32) UNIQUE NOT NULL, -- e.g., 'IT-1042'
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(64) NOT NULL,             -- e.g., 'VPN', 'Hardware', 'Software'
    priority VARCHAR(16) NOT NULL DEFAULT 'medium',
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_ticket_priority CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    CONSTRAINT chk_ticket_status CHECK (status IN ('open', 'in_progress', 'resolved', 'closed'))
);

-- 6. Document Registry (RAG Lifecycle Registry)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    category VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    checksum_sha256 CHAR(64) NOT NULL,
    chunk_count INT NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    indexed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_doc_category CHECK (category IN ('HR', 'IT')),
    CONSTRAINT chk_doc_status CHECK (status IN ('pending', 'indexing', 'indexed', 'failed'))
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_leave_emp ON leave_balances(employee_id);
CREATE INDEX IF NOT EXISTS idx_asset_emp ON it_assets(employee_id);
CREATE INDEX IF NOT EXISTS idx_ticket_emp ON it_tickets(employee_id);
CREATE INDEX IF NOT EXISTS idx_doc_status ON documents(status);
