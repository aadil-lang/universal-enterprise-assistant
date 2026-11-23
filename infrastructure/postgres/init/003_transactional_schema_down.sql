-- =============================================================================
-- Universal Enterprise HR & IT Assistant - Reversible Migration Rollback
-- Migration: 003_transactional_schema_down.sql
-- =============================================================================

DROP TABLE IF EXISTS transaction_audit_events CASCADE;
DROP TABLE IF EXISTS transaction_confirmations CASCADE;
DROP TABLE IF EXISTS employee_contact_audit CASCADE;
DROP TABLE IF EXISTS equipment_requests CASCADE;
DROP TABLE IF EXISTS hr_service_requests CASCADE;
DROP TABLE IF EXISTS reimbursement_requests CASCADE;
DROP TABLE IF EXISTS it_ticket_updates CASCADE;
DROP TABLE IF EXISTS leave_requests CASCADE;

ALTER TABLE it_tickets DROP COLUMN IF EXISTS asset_tag;

ALTER TABLE employees 
DROP COLUMN IF EXISTS phone_number,
DROP COLUMN IF EXISTS emergency_contact_name,
DROP COLUMN IF EXISTS emergency_contact_phone,
DROP COLUMN IF EXISTS personal_email;
