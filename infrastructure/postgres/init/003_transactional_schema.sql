-- =============================================================================
-- Universal Enterprise HR & IT Assistant - PostgreSQL 16 Transactional Schema
-- Scope: Transactional Workflows for Acme Corporation (FY 2026)
-- Migration: 003_transactional_schema.sql (Reversible)
-- =============================================================================

-- 1. Contact Information Extensions to Employees Table
ALTER TABLE employees 
ADD COLUMN IF NOT EXISTS phone_number VARCHAR(32),
ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR(128),
ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR(32),
ADD COLUMN IF NOT EXISTS personal_email VARCHAR(255);

-- 2. Leave Requests (Capability 1 & 6)
CREATE TABLE IF NOT EXISTS leave_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_number VARCHAR(32) UNIQUE NOT NULL, -- e.g. LV-2026-0001
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type VARCHAR(32) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_requested NUMERIC(5,2) NOT NULL,
    reason TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    cancellation_reason TEXT,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_leave_req_type CHECK (leave_type IN ('annual', 'sick')),
    CONSTRAINT chk_leave_req_status CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    CONSTRAINT chk_leave_req_dates CHECK (start_date <= end_date),
    CONSTRAINT chk_leave_req_days CHECK (days_requested > 0)
);

CREATE INDEX IF NOT EXISTS idx_leave_requests_emp ON leave_requests(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_requests_status ON leave_requests(status);
CREATE INDEX IF NOT EXISTS idx_leave_requests_dates ON leave_requests(employee_id, start_date, end_date);

-- 3. IT Ticket Updates History (Capability 7)
CREATE TABLE IF NOT EXISTS it_ticket_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES it_tickets(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    update_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ticket_updates_ticket ON it_ticket_updates(ticket_id);

-- Optional asset link on it_tickets if not already present
ALTER TABLE it_tickets 
ADD COLUMN IF NOT EXISTS asset_tag VARCHAR(64);

-- 4. Reimbursement Requests (Capability 3)
CREATE TABLE IF NOT EXISTS reimbursement_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_number VARCHAR(32) UNIQUE NOT NULL, -- e.g. EXP-2026-0001
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    expense_category VARCHAR(64) NOT NULL,      -- e.g. ergonomic_stipend, travel, equipment, general
    amount NUMERIC(10,2) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    purchase_date DATE NOT NULL,
    description TEXT NOT NULL,
    vendor VARCHAR(128),
    receipt_filename VARCHAR(255),
    receipt_path VARCHAR(512),
    status VARCHAR(32) NOT NULL DEFAULT 'submitted',
    review_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_reimbursement_status CHECK (status IN ('submitted', 'pending_approval', 'approved', 'rejected', 'paid')),
    CONSTRAINT chk_reimbursement_amount CHECK (amount > 0)
);

CREATE INDEX IF NOT EXISTS idx_reimbursements_emp ON reimbursement_requests(employee_id);
CREATE INDEX IF NOT EXISTS idx_reimbursements_cat ON reimbursement_requests(expense_category);

-- 5. HR Service Requests (Capability 4)
CREATE TABLE IF NOT EXISTS hr_service_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_number VARCHAR(32) UNIQUE NOT NULL, -- e.g. HR-2026-0001
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    service_category VARCHAR(64) NOT NULL,      -- e.g. employment_verification_letter, employment_certificate, payroll_clarification, general_hr
    purpose TEXT NOT NULL,
    recipient_details TEXT,
    additional_details TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'submitted',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_hr_service_status CHECK (status IN ('submitted', 'in_progress', 'completed', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_hr_service_emp ON hr_service_requests(employee_id);

-- 6. Equipment Requests (Capability 8)
CREATE TABLE IF NOT EXISTS equipment_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_number VARCHAR(32) UNIQUE NOT NULL, -- e.g. EQ-2026-0001
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    equipment_type VARCHAR(64) NOT NULL,        -- e.g. monitor, keyboard, headset, docking_station, ergonomic_chair
    specifications TEXT,
    business_justification TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'submitted',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_equipment_status CHECK (status IN ('submitted', 'pending_review', 'approved', 'fulfilled', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_equipment_emp ON equipment_requests(employee_id);

-- 7. Employee Contact Audit History (Capability 9)
CREATE TABLE IF NOT EXISTS employee_contact_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    field_name VARCHAR(64) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by UUID NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contact_audit_emp ON employee_contact_audit(employee_id);

-- 8. Transaction Confirmations & Idempotency Store (Section 7)
CREATE TABLE IF NOT EXISTS transaction_confirmations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    confirmation_token VARCHAR(64) UNIQUE NOT NULL,
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    transaction_type VARCHAR(64) NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash CHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'awaiting_confirmation',
    idempotency_key VARCHAR(128) UNIQUE,
    executed_request_id VARCHAR(64),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    executed_at TIMESTAMPTZ,
    CONSTRAINT chk_confirm_status CHECK (status IN ('awaiting_confirmation', 'confirmed', 'executed', 'rejected', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_confirm_token ON transaction_confirmations(confirmation_token);
CREATE INDEX IF NOT EXISTS idx_confirm_emp ON transaction_confirmations(employee_id);
CREATE INDEX IF NOT EXISTS idx_confirm_idem ON transaction_confirmations(idempotency_key);

-- 9. Transaction Audit Log
CREATE TABLE IF NOT EXISTS transaction_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    action VARCHAR(64) NOT NULL,
    request_number VARCHAR(32),
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_emp ON transaction_audit_events(employee_id);
