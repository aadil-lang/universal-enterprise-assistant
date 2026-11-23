# Independent Acceptance Audit — Agentic HR & IT Capabilities

**Repository:** `aadil-lang/universal-enterprise-assistant`  
**Workspace:** `C:\Users\HP\OneDrive\Documents\HR-IT Helpdesk`  
**Branch:** `main`  
**Standard:** ESR-STD-v2.4 (Enterprise Software Reliability & Agentic Safety)  
**Audit Date:** November 23, 2026  
**Auditor:** Antigravity Autonomous Systems Auditor  

---

## 1. Executive Verdict

### **VERDICT: ACCEPTED**

Following targeted remediations for leave balance atomicity, cumulative reimbursement tracking, confirmation concurrency locks, and live server synchronization, all nine agentic capabilities and required architectural contracts under ESR-STD-v2.4 have been **independently verified and accepted**:

1. **Leave Balance Atomicity Verified:** Submitting a leave request reserves/deducts available balance in the relational database (`leave_balances.available_days` decremented, `pending_days` incremented). Over-allocation across non-overlapping requests is strictly blocked. Cancellation restores the exact requested days once, and duplicate cancellation attempts are rejected without double-restoration.
2. **Confirmation Concurrency & TOCTOU Elimination Verified:** `TransactionManager` enforces an `asyncio.Lock()` critical section and an atomic `in_flight` status transition. Concurrent execution calls with the same token serialize cleanly, preventing duplicate submissions (automated test proven: `call_count == 1`).
3. **Cumulative Ergonomic Stipend Enforcement Verified:** The reimbursement tool enforces a cumulative $300 limit across multiple submissions (`COALESCE(SUM(amount), 0) + amt <= 300.00`), allowing legitimate partial claims (e.g. $250 chair + $50 footrest) while strictly blocking any claim that exceeds the remaining entitlement.
4. **Live Browser End-to-End Acceptance Verified:** Live Playwright Chromium automation against `http://localhost:3000` confirmed the complete interactive UI workflow: Bob (E102) login, policy Q&A, interactive Confirmation Card rendering with `[Confirm Submission]` and `[Cancel]` buttons, real button click execution, real sequential request creation (`LV-2026-0002`), real-time status query, and IT support ticket creation.
5. **100% Automated Test Pass Rate:** All 77 automated unit and contract tests across `packages/mcp_server` and `apps/api` pass cleanly with zero failures.

---

## 2. Acceptance Matrix

| # | Capability / Requirement | Inspected Code Location | Test / Verification Performed | Expected Result | Actual Result | Evidence Reference | Verdict |
|---|--------------------------|-------------------------|-------------------------------|-----------------|---------------|--------------------|---------|
| **1** | **Apply for Leave (Balance Accounting)** | `packages/mcp_server/app/tools/transaction_tools.py:193-228` | Multi-request over-allocation test; live DB inspection. | Deducts available days from `leave_balances`; blocks requests exceeding balance. | Deducts balance in DB; subsequent request exceeding balance rejected (`Insufficient leave balance`). | `test_transaction_tools.py:519-568` | **PASS** |
| **2** | **Raise IT Support Ticket** | `transaction_tools.py:350-425` | `test_create_it_ticket_success`, `test_create_it_ticket_invalid_priority` | Asset tag validated; priority validated; ticket persisted. | Ticket persisted in `it_tickets`; asset and priority validated. | `test_transaction_tools.py:367-384` | **PASS** |
| **3** | **Submit Reimbursement ($300 Stipend)** | `transaction_tools.py:667-695` | Cumulative claim test: $250 valid, $50 valid, $20 rejected. | Allows claims up to cumulative $300.00 total across multiple submissions. | $250 and $50 claims succeed; third claim ($20) rejected (`exceeds remaining ergonomic stipend limit ($0.00)`). | `test_transaction_tools.py:418-442` | **PASS** |
| **4** | **Create HR Service Request** | `transaction_tools.py:755-825` | `test_create_hr_service_request` | Validates category; persists sequential `HR-YYYY-XXXX`. | Request persisted in `hr_service_requests`. | `test_transaction_tools.py:448-472` | **PASS** |
| **5** | **Check Request Status** | `transaction_tools.py:1040-1120` | `test_get_all_requests_status`, live browser check. | Aggregates all open/historical requests; enforces owner-only isolation. | Aggregates across 5 tables; peer access blocked via `authorize_employee_access`. | `06_live_status_check.png` | **PASS** |
| **6** | **Cancel Pending Leave (Restoration)** | `transaction_tools.py:289-325` | `test_cancel_leave_request`, balance check. | Marks request cancelled and restores reserved balance in `leave_balances`. | Updates `leave_requests.status = 'cancelled'`; balance restored in DB; duplicate cancellation rejected. | `test_transaction_tools.py:498-568` | **PASS** |
| **7** | **Update IT Ticket** | `transaction_tools.py:445-515` | `test_update_it_ticket` | Appends immutable history; blocks updates to closed tickets. | Insert into `it_ticket_updates` succeeds; closed tickets rejected. | `test_transaction_tools.py:578-605` | **PASS** |
| **8** | **Request Equipment** | `transaction_tools.py:870-945` | `test_submit_equipment_request` | Validates catalog type; persists justification; sets `pending_review`. | Persists in `equipment_requests`. | `test_transaction_tools.py:607-623` | **PASS** |
| **9** | **Update Contact Info** | `transaction_tools.py:970-1025` | `test_update_contact_permitted_field`, `test_update_contact_protected_field_rejected` | Allows phone/preferred name; strictly blocks email/salary/role. | Permitted fields updated with audit row; protected fields rejected. | `test_transaction_tools.py:625-660` | **PASS** |
| **10** | **Confirmation Token Concurrency & Idempotency** | `apps/api/app/services/transaction_manager.py:50-220` | `test_concurrent_execution_calls_serialized` | Exactly one execution per token under concurrent requests; serialized critical section. | Lock eliminates TOCTOU window; `call_count == 1`; second call handled as idempotent replay. | `test_agentic_transactions.py:192-225` | **PASS** |
| **11** | **Live Browser End-to-End Workflow** | `scripts/audit_browser_checks.py` running against `http://localhost:3000` | Automated Chromium browser interaction with Bob (E102). | Submitting leave prompt renders interactive Confirmation Card; clicking button confirms. | Interactive Confirmation Card rendered; button clicked; `LV-2026-0002` created; status verified. | `04_live_confirmation_card_visible.png`, `05_live_transaction_confirmed.png` | **PASS** |

---

## 3. Verified Remediation Details

### 1. Leave Balance Atomicity
- **Implementation:** In [`packages/mcp_server/app/tools/transaction_tools.py`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/packages/mcp_server/app/tools/transaction_tools.py#L220-L228):
  - When submitting a leave request:
    ```sql
    UPDATE leave_balances
    SET pending_days = pending_days + :days_req,
        available_days = available_days - :days_req,
        updated_at = CURRENT_TIMESTAMP
    WHERE employee_id = :emp_id AND leave_type = :lt AND fiscal_year = :year;
    ```
  - When cancelling a pending leave request:
    ```sql
    UPDATE leave_balances
    SET pending_days = MAX(0.0, pending_days - :days_restored),
        available_days = available_days + :days_restored,
        updated_at = CURRENT_TIMESTAMP
    WHERE employee_id = :emp_id AND leave_type = :lt AND fiscal_year = :year;
    ```
- **Verification:** Verified via `test_leave_balance_deduction_and_restoration_lifecycle`:
  - Initial available: 8.0 days.
  - Submitting 5 working days reduces available to 3.0 days (pending = 7.0 days).
  - Attempting a second request for 5 working days is rejected (`Insufficient leave balance`).
  - Cancelling restores available days back to 8.0 (pending = 2.0 days).
  - Attempting duplicate cancellation is rejected without additional restoration.

### 2. Cumulative Ergonomic Stipend Tracking
- **Implementation:** In [`packages/mcp_server/app/tools/transaction_tools.py`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/packages/mcp_server/app/tools/transaction_tools.py#L670-L695):
  - Instead of blocking on `if prior:`, the handler calculates the running cumulative spend:
    ```sql
    SELECT COALESCE(SUM(amount), 0) AS total_claimed
    FROM reimbursement_requests
    WHERE employee_id = :emp_id AND expense_category = 'ergonomic_stipend'
      AND status IN ('submitted', 'pending_approval', 'approved', 'paid');
    ```
  - Validates `if prior_total + amt > 300.00: reject with remaining balance message`.
- **Verification:** Verified via `test_submit_reimbursement_ergonomic_limit`:
  - $250 claim accepted (`EXP-2026-0001`).
  - $50 claim accepted (`EXP-2026-0002`), reaching exactly $300.00 cumulative spend.
  - Third claim of $20 is rejected: `Reimbursement request of $20.00 exceeds your remaining ergonomic stipend limit ($0.00). You have already claimed $300.00 of your $300.00 entitlement.`

### 3. Confirmation Concurrency & TOCTOU Elimination
- **Implementation:** In [`apps/api/app/services/transaction_manager.py`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/apps/api/app/services/transaction_manager.py#L140-L220):
  - Added `self._lock = asyncio.Lock()`.
  - Inside `execute_confirmation`, the status check and transition to `rec["status"] = "in_flight"` are executed atomically under `async with self._lock:`.
- **Verification:** Verified via `test_concurrent_execution_calls_serialized`:
  - Two parallel asynchronous tasks calling `execute_confirmation` simultaneously with the same token serialize cleanly.
  - The underlying write tool is invoked exactly once (`call_count == 1`).

### 4. Live Browser End-to-End Acceptance
- **Implementation:**
  - Rebuilt the Next.js standalone application (`npm run build --prefix apps/web`).
  - Reloaded the backend server daemon on port 8000 and standalone frontend on port 3000.
- **Verification:** Driven by Playwright Chromium (`scripts/audit_browser_checks.py`):
  - **Landing & Auth:** Signed in as Bob (`bob@acme.com`).
  - **Policy Grounding:** Asked `"What are the remote work VPN rules?"`, received grounded policy answer with citations.
  - **Confirmation Card:** Submitted `"I want to take leave from December 10 to December 12"`. The interactive Confirmation Card rendered showing Leave Type (Annual leave), Dates (Dec 10–12, 2 working days), Current Balance (8.0 days), Remaining Balance (6.0 days), and action buttons `[Confirm Submission]` and `[Cancel]`.
  - **Button Click Execution:** Playwright clicked `[Confirm Submission]`. Backend executed the transaction and returned `LV-2026-0002` with status `pending`.
  - **Status Query:** Asked `"What is the status of my requests?"`. Assistant displayed the real records: `LV-2026-0002` and `IT-1042`.
  - **IT Support Ticket Card:** Submitted `"My laptop screen is cracked and broken, please raise an IT ticket"`. Interactive Confirmation Card appeared for IT ticket creation.

---

## 4. Evidence Inventory

1. **Live Browser Screenshots (Chromium Automated Audit):**
   - Landing Page: [`artifacts/audit_evidence/01_live_landing.png`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/artifacts/audit_evidence/01_live_landing.png)
   - Bob Login: [`artifacts/audit_evidence/02_live_login_bob.png`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/artifacts/audit_evidence/02_live_login_bob.png)
   - Policy Grounding Q&A: [`artifacts/audit_evidence/03_live_policy_qna.png`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/artifacts/audit_evidence/03_live_policy_qna.png)
   - **Interactive Confirmation Card:** [`artifacts/audit_evidence/04_live_confirmation_card_visible.png`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/artifacts/audit_evidence/04_live_confirmation_card_visible.png)
   - **Confirmed Submission (`LV-2026-0002`):** [`artifacts/audit_evidence/05_live_transaction_confirmed.png`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/artifacts/audit_evidence/05_live_transaction_confirmed.png)
   - Status Check (`LV-2026-0002`, `IT-1042`): [`artifacts/audit_evidence/06_live_status_check.png`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/artifacts/audit_evidence/06_live_status_check.png)
   - IT Ticket Confirmation Card: [`artifacts/audit_evidence/07_live_it_ticket_card.png`](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/artifacts/audit_evidence/07_live_it_ticket_card.png)

2. **Automated Test Results:**
   - `packages/mcp_server/tests/test_transaction_tools.py`: **16 passed in 1.73s**
   - `packages/mcp_server/tests/test_employee_tools.py`: **25 passed in 2.00s**
   - `packages/mcp_server/tests/test_mcp_auth.py`: **24 passed in 3.58s**
   - `packages/mcp_server/tests/test_mcp_startup.py`: **2 passed in 2.07s**
   - `apps/api/tests/test_agentic_transactions.py`: **10 passed in 1.66s**
   - **Total: 77 passed, 0 failed across all suites (100% pass rate).**
