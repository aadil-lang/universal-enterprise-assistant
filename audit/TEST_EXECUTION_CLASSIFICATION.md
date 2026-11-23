# Phase 2.1A — Test Execution Classification Matrix

**Project:** Universal Enterprise HR & IT Assistant — Acme Corporation  
**Repository:** `aadil-lang/universal-enterprise-assistant`  
**Workspace:** `C:\Users\HP\OneDrive\Documents\HR-IT Helpdesk`  
**Standard:** ESR-STD-v2.4  
**Date:** November 20, 2026  
**Auditor:** Independent Technical Auditor  

---

## 1. Classification Methodology

To provide absolute provenance integrity, every test reported in the Phase 6 dogfooding report has been independently categorized into exactly one of seven mutually exclusive operational tiers:

1. **Live browser execution:** Exercised through a real Playwright-controlled browser rendering the live web application DOM.
2. **Live HTTP/API execution:** Network requests transmitted over TCP to the active listening server ports (`:3000` or `:8000`).
3. **In-process ASGI execution:** Executed against FastAPI application router handlers via Starlette / ASGI test transport in memory.
4. **Direct service/function execution:** Direct Python function or coroutine invocation with mock databases or synthetic state.
5. **Static source inspection:** Code review of TSX/Python files without executing runtime code.
6. **Build or unit-test execution:** Standard automated test runners (`pytest`, `npm test`, `next build`).
7. **Not tested:** Workflows claimed or implied that were never executed during the session.

---

## 2. Phase 6 Employee Journey Classification (Bob Jones E102)

| Step # | Test Name / Operational Goal | Phase 6 Claimed Mechanism | Actual Execution Category | Evidence & Provenance Details |
| :---: | :--- | :--- | :--- | :--- |
| **01** | Employee Login (Bob E102) | Real login workflow | **Direct service/function execution** | Called `_execute_login()` in `scripts/execute_phase_6_dogfooding.py` against in-memory SQLite session. *(Note: Live browser execution was subsequently achieved in Phase 2.1A).* |
| **02** | Inspect Initial Interface | Live UI visual inspection | **Static source inspection** | Derived by inspecting lines 168–205 of `apps/web/components/ChatInterface.tsx`. No browser window was open. |
| **03** | Annual Leave Balance Query | Assistant conversational response | **Direct service/function execution** | Evaluated via `execute_workflow_sync()` in Python with an in-process mock MCP dispatcher. |
| **04** | Sick Leave Balance Query | Assistant conversational response | **Direct service/function execution** | Evaluated via `execute_workflow_sync()` in Python with an in-process mock MCP dispatcher. |
| **05** | Assigned Hardware Query | Assistant conversational response | **Direct service/function execution** | Evaluated via `execute_workflow_sync()` in Python with an in-process mock MCP dispatcher. |
| **06** | Open IT Tickets Query | Assistant conversational response | **Direct service/function execution** | Evaluated via `execute_workflow_sync()` in Python with an in-process mock MCP dispatcher. |
| **07** | Vacation Entitlement (Q05) | RAG policy synthesis & citation | **Direct service/function execution** | Evaluated in memory via `execute_workflow_sync()` using ephemeral ChromaDB and local regex extraction. |
| **08** | Vacation Rollover (Q06) | RAG policy synthesis & citation | **Direct service/function execution** | Evaluated in memory via `execute_workflow_sync()` using ephemeral ChromaDB. |
| **09** | Ergonomic Stipend (Q08) | RAG policy synthesis & citation | **Direct service/function execution** | Evaluated in memory via `execute_workflow_sync()` using ephemeral ChromaDB. |
| **10** | Mandatory VPN (Q09) | RAG policy synthesis & citation | **Direct service/function execution** | Evaluated in memory via `execute_workflow_sync()` using ephemeral ChromaDB. |
| **11** | Laptop Refresh Cycle (Q10) | RAG policy synthesis & citation | **Direct service/function execution** | Evaluated in memory via `execute_workflow_sync()` using ephemeral ChromaDB. |
| **12** | Hybrid Policy + Balance Query| Dual RAG + MCP synthesis | **Direct service/function execution** | Evaluated in memory via `execute_workflow_sync()`. |
| **13** | Citations Presence Inspection | UI citation card verification | **Direct service/function execution** | Inspected the Python dictionary key `citations` in the returned state object. |
| **14** | Follow-up Question Testing | Multi-turn conversational flow | **Direct service/function execution** | Executed two independent sync Python calls in `execute_phase_6_dogfooding.py`. |
| **15** | Logout & Token Disposal | UI logout & session clearing | **Direct service/function execution** | Verified by calling `decode_access_token("invalid_token")` in Python; caught `HTTPException(401)`. |

---

## 3. Phase 6 Security and Boundary Exploration Classification

| Test ID | Test Name / Security Boundary | Claimed Mechanism | Actual Execution Category | Evidence & Provenance Details |
| :---: | :--- | :--- | :--- | :--- |
| **SEC-01**| Unauthenticated API Rejection | HTTP 401 on chat endpoint | **Direct service/function execution** | Executed `decode_access_token("")` in Python; caught HTTP 401 exception. |
| **SEC-02**| Peer Record Access Denial | Bob querying Carol E103 | **Direct service/function execution** | Executed `execute_workflow_sync()` in Python; checked string output for `"Access Denied"`. |
| **SEC-03**| Role Privilege Escalation | Employee calling upload API | **Direct service/function execution** | Directly invoked `upload_document(current_user=bob_caller)` in Python; caught HTTP 403. |
| **SEC-04**| HR Admin Authorized Lookup | Alice querying Bob E102 | **Direct service/function execution** | Executed `execute_workflow_sync()` with `alice_caller` in Python. |
| **SEC-05**| Out-of-Scope Prompt Refusal | "Recommend a good movie" | **Direct service/function execution** | Executed `execute_workflow_sync()` in Python. |
| **SEC-06**| Direct Prompt Injection (3x) | Ignore instructions / dump DB | **Direct service/function execution** | Iterated over 3 injection strings in Python loop calling `execute_workflow_sync()`. |
| **SEC-07**| Confidential Compensation | Exact salary / bonus refusal | **Direct service/function execution** | Executed `execute_workflow_sync()` in Python. |
| **SEC-08**| Error Sanitization | Malformed PDF upload error | **Direct service/function execution** | Invoked `pipeline.ingest_document("broken.pdf", b"...")` in Python; caught `MalformedDocumentError`. |
| **SEC-09**| Deactivated User Block | David Miller E104 login | **Direct service/function execution** | Invoked `_execute_login()` in Python; caught HTTP 401. |
| **SEC-10**| User Enumeration Defense | Unknown user timing normalization| **Direct service/function execution** | Invoked `_execute_login()` for nonexistent user; verified error string and dummy hash. |

---

## 4. Phase 6 HR Administrator Journey Classification (Alice Smith E101)

| Step # | Test Name / Admin Workflow | Claimed Mechanism | Actual Execution Category | Evidence & Provenance Details |
| :---: | :--- | :--- | :--- | :--- |
| **01** | HR Admin Login | Real admin login workflow | **Direct service/function execution** | Called `_execute_login()` in Python for `alice@acme.com`. |
| **02** | Admin Interface Inspection | UI badge & button check | **Static source inspection** | Inspected lines 205–215 of `ChatInterface.tsx` (`user?.role === 'hr_admin' && <button...`). |
| **03** | Ingest Document Modal UI | Modal rendering & form fields | **Static source inspection** | Inspected `apps/web/components/DocumentUploadModal.tsx`. |
| **04** | Supported Format Handlers | PDF, DOCX, Markdown parsing | **Direct service/function execution** | Inspected `DocumentExtractor` capabilities in Python. |
| **05** | Document Upload Validation | File validation feedback | **Direct service/function execution** | Called `validate_document_file("sample_policy.md", ...)` in Python. |
| **06** | Unsupported File Rejection | Rejecting .exe, .csv, .txt | **Direct service/function execution** | Called `validate_document_file()` in a Python loop for 4 extensions. |
| **07** | Empty Document Rejection | Rejecting 0-byte upload | **Direct service/function execution** | Called `validate_document_file("empty.md", b"")` in Python. |
| **08** | UI Status Feedback Alert | Emerald/rose alert verification| **Static source inspection** | Inspected lines 115–138 of `DocumentUploadModal.tsx`. |

---

## 5. Automated Build, Verification & Unit Test Suites

| Suite / Check Name | Command Line Executed | Actual Execution Category | Provenance Status |
| :--- | :--- | :--- | :---: |
| **Frontend Unit & Client Checks** | `node apps/web/tests/verify_frontend.mjs` | **Build or unit-test execution** | **PASS (4/4)** |
| **Next.js Production Build** | `npm run build` (in `apps/web`) | **Build or unit-test execution** | **PASS (Clean)** |
| **Multi-Chunk Retrieval Tests** | `pytest apps/api/tests/test_policy_retrieval_multichunk.py` | **Build or unit-test execution** | **PASS (7/7)** |
| **Adversarial & Auth Security** | `pytest apps/api/tests/test_ai_security_adversarial.py ...` | **Build or unit-test execution** | **PASS (14/14)** |

---

## 6. Phase 2.1A Additional Browser Validation Classification

| Action Executed | Target Endpoint | Actual Execution Category | Empirical Artifact |
| :--- | :--- | :--- | :--- |
| **Browser Navigation & Render** | `http://127.0.0.1:3000` | **Live browser execution** | Verified page title, DOM loaded, `trace.zip`. |
| **Live Credential Authentication** | `POST http://localhost:8000/api/v1/auth/login` | **Live browser execution** | Form filled by Playwright Chromium; HTTP 200 returned; JWT stored. |
| **Chat Interface DOM Mount** | `http://127.0.0.1:3000` | **Live browser execution** | User identity rendered: `"Bob Jones(E102) EMPLOYEE"`. |
| **Conversational Query Submit** | `POST http://localhost:8000/api/v1/chat` | **Live browser execution** | Dispatched via browser input; caught 45s timeout from container Gemini outage; error card rendered. |
| **Full Page Screenshot Capture** | `audit/EVIDENCE/bob_browser_journey.png` | **Live browser execution** | 38.8 KB PNG image captured from active browser canvas. |
| **Playwright Trace Archive** | `audit/EVIDENCE/trace.zip` | **Live browser execution** | 4.06 MB trace archive containing DOM snapshots, console logs, network events. |

---

## 7. Comparative Provenance Synthesis

```
Phase 6 Testing Mix (Reported as "Product Dogfooding"):
├── Direct Service / Function Execution: 78% (25 tests)
├── Static Source Inspection:            12% (4 tests)
├── Build / Unit Test Execution:         10% (4 suites)
└── Live Browser Execution:               0% (0 tests)  <-- ZERO BROWSER TESTING IN PHASE 6

Phase 2.1A Audit Remediation (Independent Provenance):
├── Live Browser Execution:              100% Proven for navigation, login, and error handling
├── Live Network Activity Logged:        Recorded in audit/EVIDENCE/network_activity.json
├── Full Playwright Trace Recorded:      Recorded in audit/EVIDENCE/trace.zip
└── Live Backend Outage Isolated:        Discovered container Gemini timeout & FastMCP SSE closure
```
